"""
QA analysis for TARS.

Runs as a separate GPT-4o call after sentiment analysis.  For each ticket it
determines whether the ticket reports a bug, which product feature area is
affected, on which platform, and a short error pattern description.

Tickets are processed in batches of BATCH_SIZE to stay within context limits.
Results are stored per-ticket in MongoDB and aggregated into weekly QA
cluster reports.
"""
import json
import logging
from typing import List, Dict

from openai import OpenAI

logger = logging.getLogger(__name__)

BATCH_SIZE = 20
MAX_CONVO_CHARS = 8000

VALID_FEATURE_AREAS = {
    "connection_engine",
    "protocol_wireguard",
    "protocol_ikev2",
    "protocol_openvpn",
    "protocol_stealth",
    "protocol_amnezia",
    "app_crash",
    "app_ui",
    "localization",
    "look_and_feel",
    "dns_robert",
    "split_tunneling",
    "allow_lan_traffic",
    "authentication",
    "billing_app_bugs",
    "static_ip_app_issues",
    "config_generation",
    "other",
}

VALID_PLATFORMS = {
    "windows",
    "macos",
    "linux",
    "android",
    "ios",
    "router",
    "browser_extension",
    "tv",
    "unknown",
}

SYSTEM_MSG = (
    "You are TARS, a QA analysis engine for Windscribe VPN. "
    "You identify bugs, broken functionality, and product defects "
    "from support tickets with precision. You always return valid JSON "
    "exactly as specified."
)


class QAAnalyzer:
    """Extracts structured QA signals from support tickets."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def analyze(self, tickets: List[Dict]) -> Dict[str, Dict]:
        """
        Analyze tickets for QA signals in batches.

        Returns:
            Dict keyed by ticket number (str) -> {is_bug, feature_area,
            platform, error_pattern}.
        """
        if not tickets:
            return {}

        all_results: Dict[str, Dict] = {}
        batches = [
            tickets[i : i + BATCH_SIZE]
            for i in range(0, len(tickets), BATCH_SIZE)
        ]
        total_batches = len(batches)
        logger.info(
            f"QA: processing {len(tickets)} tickets in {total_batches} "
            f"batch(es) of up to {BATCH_SIZE}"
        )

        for idx, batch in enumerate(batches, 1):
            try:
                batch_results = self._analyze_batch(batch, idx, total_batches)
                all_results.update(batch_results)
            except Exception as e:
                logger.warning(
                    f"QA batch {idx}/{total_batches} failed: {e} "
                    f"— continuing with remaining batches"
                )

        logger.info(f"QA scored {len(all_results)}/{len(tickets)} tickets total")
        return all_results

    def _analyze_batch(
        self, batch: List[Dict], batch_num: int, total_batches: int
    ) -> Dict[str, Dict]:
        """Run a single GPT-4o call for one batch of tickets."""
        prompt = self._build_prompt(batch)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_MSG},
                {"role": "user", "content": prompt},
            ],
            temperature=0.15,
            max_tokens=8192,
            response_format={"type": "json_object"},
        )

        finish_reason = response.choices[0].finish_reason
        usage = response.usage
        logger.info(
            f"QA batch {batch_num}/{total_batches}: "
            f"finish_reason={finish_reason}, "
            f"tokens={usage.prompt_tokens}+{usage.completion_tokens}"
            f"={usage.total_tokens}"
        )
        if finish_reason == "length":
            logger.warning(f"QA batch {batch_num} cut off by max_tokens")

        raw = json.loads(response.choices[0].message.content)
        results = raw.get("tickets", {})

        cleaned: Dict[str, Dict] = {}
        for num, data in results.items():
            is_bug = data.get("is_bug")
            if not isinstance(is_bug, bool):
                is_bug = str(is_bug).lower() in ("true", "1", "yes")

            feature_area = data.get("feature_area", "other")
            if feature_area not in VALID_FEATURE_AREAS:
                feature_area = "other"

            platform = data.get("platform", "unknown")
            if platform not in VALID_PLATFORMS:
                platform = "unknown"

            cleaned[str(num)] = {
                "is_bug": is_bug,
                "feature_area": feature_area,
                "platform": platform,
                "error_pattern": (data.get("error_pattern") or "")[:300],
            }

        return cleaned

    def _build_prompt(self, tickets: List[Dict]) -> str:
        ticket_count = len(tickets)

        tickets_text = []
        for t in tickets:
            convo = t.get("full_conversation") or t.get("first_message", "")
            convo = convo[:MAX_CONVO_CHARS]
            tickets_text.append(
                f"Ticket #{t['number']}\n"
                f"Subject: {t['subject']}\n"
                f"Conversation:\n{convo}\n"
                f"---"
            )
        tickets_formatted = "\n".join(tickets_text)

        feature_areas_block = "\n".join(
            f"  - {fa}" for fa in sorted(VALID_FEATURE_AREAS - {"other"})
        ) + "\n  - other"

        platforms_block = "\n".join(
            f"  - {p}" for p in sorted(VALID_PLATFORMS - {"unknown"})
        ) + "\n  - unknown"

        return f"""You are TARS, a QA analysis engine for Windscribe VPN.
Analyze the following batch of {ticket_count} support tickets and extract structured QA signals.

For each ticket, determine:

1. **is_bug** (true or false)
   Is this ticket reporting broken functionality, a software defect, or a product bug that a QA engineer could reproduce and fix in the app's code?
   - true: App crashes, features not working as designed, UI glitches, broken translations, protocol connection drops/failures with app-level errors, incorrect data displayed in the app, config upload failures
   - false: How-to questions, account requests, refund requests, general inquiries, feature requests, user misconfiguration, speed/performance complaints (even if a specific protocol is mentioned), streaming service blocks, server outages, censorship/geo-blocking/network restrictions, forgotten passwords, email delivery failures (confirmation or reset emails not arriving), bank-side payment rejections, app store subscription activation issues (Google Play / Apple / Amazon purchase not activating)

   When in doubt, default to is_bug=false. Ask yourself: "Could a QA engineer reproduce and fix this in the app's code?" If the answer is no — because it's a bank, email server, app store, network, or infrastructure issue — mark is_bug=false.

2. **feature_area** (strictly one of the values below)
   Which part of the Windscribe product is affected?

{feature_areas_block}

   Definitions:
   - connection_engine: Core VPN tunnel establishment failures, handshake timeouts, protocol negotiation errors (use this when no specific protocol is identified)
   - protocol_wireguard: WireGuard-specific connection or performance failures
   - protocol_ikev2: IKEv2-specific failures
   - protocol_openvpn: OpenVPN-specific failures, including both UDP and TCP modes
   - protocol_stealth: Stealth, WStunnel, and censorship bypass protocol failures
   - protocol_amnezia: AmneziaWG-specific failures
   - app_crash: Application crashes, force closes, fails to open or launch
   - app_ui: UI/UX bugs — broken buttons, layout issues, visual glitches, missing elements
   - localization: Wrong or missing translations in non-English UI, untranslated text appearing in localized interfaces (e.g., English text in Spanish UI). Often occurs when new features ship without full translation coverage
   - look_and_feel: Issues with app personalization features — sound notifications, app background/theme, rename location, and other appearance/customization settings
   - dns_robert: DNS resolution failures, encrypted DNS issues, R.O.B.E.R.T. false positives or negatives
   - split_tunneling: Split tunnel not performing as configured — inclusive mode not including specified apps/IPs, exclusive mode not excluding them
   - allow_lan_traffic: LAN access broken while VPN is active — can't reach printers, NAS, Chromecast, or other local network devices with "Allow LAN Traffic" enabled
   - authentication: Login failures where the app itself malfunctions (login loops, app shows wrong account data, 2FA flow broken in the app), lazy login (TV) not working. NOT email delivery issues — if a confirmation email, reset email, or verification email doesn't arrive, that is a backend/email infrastructure problem, NOT an app bug
   - billing_app_bugs: App-side payment issues only — payment attempt crashes the app, promo code UI broken, wrong currency displayed in the app. NOT bank-side rejections (bank declined, payment blocked by processor), NOT app store activation failures (Google Play / Apple / Amazon subscription purchased but not showing on account), NOT failed renewals, NOT subscription management disputes
   - static_ip_app_issues: App-side static IP bugs — crashes when connecting to static IP, failures switching between static IP and regular locations, visual issues with static IP in the apps. NOT port forwarding misconfiguration
   - config_generation: Manual config file download or generation failures from the website, or issues uploading/adding configs to apps
   - other: Doesn't clearly fit any of the above

3. **platform** (strictly one of the values below)
   What OS or device is the user on?

{platforms_block}

   If the user doesn't mention their platform, use "unknown".

4. **error_pattern** (max 50 words)
   A short, specific technical description of the bug or failure. Include version numbers, error messages, or specific behavior if mentioned.
   If is_bug is false, write "N/A".

=== RULES ===
- Base your assessment ONLY on the ticket content. Do not hallucinate.
- When in doubt, default to is_bug=false. Ask: "Could a QA engineer reproduce and fix this in the app's code?" If no, it's not a bug.
- If a ticket mentions a specific protocol by name (WireGuard, IKEv2, OpenVPN, Stealth, Amnezia), use the matching protocol_* category rather than connection_engine.
- "Can't connect" alone is NOT a bug — the user could be on a censored network, behind a restrictive firewall, or have ISP issues. Only flag as a bug if the ticket describes specific app-level failure behavior (crash, error message, repeated protocol handshake failure visible in the app).
- If "network restrictions", "restrictive network", or "censorship" appears anywhere in the ticket, default to is_bug=false UNLESS the ticket describes a clear app-level crash or UI defect completely unrelated to the network restriction.
- "VPN doesn't work in my country" is censorship, NOT a bug.
- Server outages and capacity issues are infrastructure problems, NOT bugs.
- Speed and performance complaints are NEVER bugs, even when a specific protocol is mentioned. "Slow speed on WireGuard" = NOT a bug. "App crashes on WireGuard" = bug. The distinction is broken functionality vs. poor performance.
- Port forwarding issues are almost always user misconfiguration, NOT a bug.
- Streaming service blocks are NOT bugs — expected behavior changes by the streaming service.
- Email delivery failures are NOT bugs. If a confirmation email, password reset email, or verification email doesn't arrive, that is a backend/email infrastructure issue. Do NOT flag these under authentication.
- Bank-side payment issues are NOT bugs. If a payment is blocked by the bank, declined by the processor, or flagged for fraud, that is outside the app. Do NOT flag these under billing_app_bugs.
- App store subscription activation failures are NOT bugs. If a Google Play, Apple, or Amazon purchase doesn't activate the subscription on the user's account, that is a store-side issue. Do NOT flag these under billing_app_bugs.
- Forgotten passwords and standard account recovery are NOT bugs.
- Refund or cancellation requests that mention a bad experience are NOT bugs unless they also describe a specific product defect.

=== OUTPUT FORMAT ===
Return ONLY raw, valid JSON.
Do NOT wrap the output in markdown code blocks.
Do NOT include any conversational text.

{{
  "tickets": {{
    "<ticket_number>": {{
      "is_bug": true,
      "feature_area": "<value>",
      "platform": "<value>",
      "error_pattern": "<value>"
    }}
  }}
}}

=== TICKETS ===
{tickets_formatted}"""
