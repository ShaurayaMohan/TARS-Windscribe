"""
AI-powered ticket analysis for TARS.

Two-phase approach:
  Phase 1 — Classify every ticket into one of 16 known daily categories.
  Phase 2 — Flag any ticket that genuinely doesn't fit as a new/emerging trend.
"""
import json
import logging
from typing import List, Dict, Optional

from openai import OpenAI

logger = logging.getLogger(__name__)

# ── Known categories ───────────────────────────────────────────────────────────
# Each entry: (category_id, title, description)
# These are baked into the prompt so the AI always uses stable, consistent labels.

KNOWN_CATEGORIES: List[Dict[str, str]] = [
    # Connection & Protocol Failures
    {
        "category_id": "amnezia_config",
        "title": "Amnezia / Third-Party Client Configurations",
        "description": (
            "User is trying to use Windscribe servers via the AmneziaVPN or AmneziaWG client "
            "(usually to bypass strict DPI like RKN in Russia). Tickets contain requests for raw "
            "WireGuard config files, questions on how to format configs for Amnezia, or error logs "
            "showing handshake timeouts or protocol failures in the Amnezia client."
        ),
    },
    {
        "category_id": "standard_protocol_failures",
        "title": "Standard Protocol Connection Failures",
        "description": (
            "User cannot connect using the native Windscribe app on standard networks. App is stuck "
            "on 'Connecting...' or immediately drops back to disconnected. Tickets often include debug "
            "logs, mention a specific ISP/mobile carrier, or note that the VPN works on mobile data "
            "but fails on home Wi-Fi."
        ),
    },
    {
        "category_id": "restricted_network_censorship",
        "title": "Restricted Network / Native App Censorship",
        "description": (
            "User is in a known restricted country (Russia, China, Iran) and the native app is "
            "completely blocked. Stealth, WStunnel, or all protocols are failing. Tickets often mention "
            "recent government block waves or include screenshots of the app endlessly spinning."
        ),
    },
    {
        "category_id": "intermittent_disconnections",
        "title": "Intermittent Disconnections",
        "description": (
            "VPN connects successfully but drops repeatedly. Connection dies when the phone screen "
            "locks, disconnects every few hours, or fails silently in the background while the UI "
            "still shows 'Connected'."
        ),
    },
    {
        "category_id": "slow_speeds_latency",
        "title": "Slow Speeds / High Latency",
        "description": (
            "User is connected but experiencing terrible performance. Tickets usually name the specific "
            "server, list base internet speed vs VPN speed, and often include Speedtest screenshots or "
            "Linux MTR/traceroute logs complaining about high ping in games."
        ),
    },
    # Access & Routing
    {
        "category_id": "streaming_blocks",
        "title": "Streaming Service Blocks",
        "description": (
            "User cannot access geo-restricted streaming content. Tickets name the specific platform "
            "(Netflix, BBC iPlayer, Amazon Prime), the specific Windscribe server, and usually include "
            "screenshots or text of the streaming service's proxy error code."
        ),
    },
    {
        "category_id": "website_geofencing_ip_bans",
        "title": "Website / App Geofencing & IP Bans",
        "description": (
            "User is blocked from a non-streaming service (banks, crypto exchanges, betting apps, "
            "ChatGPT, or local government portals). Tickets contain screenshots of Cloudflare 'Access "
            "Denied' pages or complaints that the website has detected VPN usage or flagged the IP "
            "as high-risk."
        ),
    },
    {
        "category_id": "split_tunneling_lan",
        "title": "Split Tunneling / LAN Failures",
        "description": (
            "User is trying to route specific traffic inside or outside the VPN, and it isn't working. "
            "Tickets list the exact app or IP they are trying to exclude, or complain about inability "
            "to cast to their TV, print to a wireless printer, or access a local NAS while Windscribe "
            "is on."
        ),
    },
    {
        "category_id": "robert_false_positives",
        "title": "R.O.B.E.R.T. Blocking (False Positives)",
        "description": (
            "A normal website or app is broken or failing to load assets. Tickets include the specific "
            "URL that is failing and explicitly mention that turning Windscribe off immediately fixes "
            "the website."
        ),
    },
    # Billing & Subscriptions
    {
        "category_id": "refund_requests",
        "title": "Refund Requests",
        "description": (
            "User explicitly demands money back. Reason is typically: it didn't bypass a block, they "
            "forgot to cancel a trial, or they bought the wrong plan. Tickets usually include order "
            "numbers, transaction IDs, or the email address tied to the payment."
        ),
    },
    {
        "category_id": "payment_failures",
        "title": "Payment Failures / Declines",
        "description": (
            "User is trying to purchase a plan but the payment gateway rejects them. Tickets include "
            "error codes from Paymentwall, Apple App Store, or Google Play, or state that their credit "
            "card was declined despite having funds."
        ),
    },
    {
        "category_id": "crypto_uncredited",
        "title": "Crypto Payment Uncredited",
        "description": (
            "User paid with cryptocurrency but their account is still on the Free tier. Tickets almost "
            "always include a blockchain transaction hash/ID, the specific coin used (BTC, ETH, XMR), "
            "and complaints that the funds left their wallet hours or days ago."
        ),
    },
    {
        "category_id": "plan_feature_confusion",
        "title": "Plan & Feature Confusion",
        "description": (
            "User bought a plan but is confused about what they see in the app. Tickets ask why they "
            "still see 'Free' servers with stars, why their custom plan doesn't have unlimited data, "
            "or complain that a specific server they were looking for isn't listed."
        ),
    },
    {
        "category_id": "cancellation_autorenewal",
        "title": "Cancellation / Auto-Renew Disputes",
        "description": (
            "User is angry about an automated charge or wants to stop future billing. Tickets ask how "
            "to find the cancel button on the website, or demand a reversal of a renewal charge they "
            "didn't authorize."
        ),
    },
    # Account & Authentication
    {
        "category_id": "lost_access_password_reset",
        "title": "Lost Access / Password Resets",
        "description": (
            "User cannot log into their account. They forgot their password, no longer have access to "
            "the email used to sign up, or never linked an email to their account in the first place "
            "and are now locked out."
        ),
    },
    {
        "category_id": "2fa_security_lockout",
        "title": "2FA / Security Lockouts",
        "description": (
            "User is blocked from logging in due to account security features. Lost their phone or "
            "authenticator app, don't have backup codes, or are stuck in an endless loop of CAPTCHAs "
            "on the login screen."
        ),
    },
    {
        "category_id": "tv_lazy_login",
        "title": "TV / Lazy Login Failures",
        "description": (
            "User is trying to log into a Smart TV app using the 6-digit code. App says 'Invalid Code' "
            "or 'Code Expired'. Multiple codes generated on phone/computer with none of them working."
        ),
    },
    # Advanced Features & Setup
    {
        "category_id": "manual_config_generation",
        "title": "Manual Config Generation Issues",
        "description": (
            "User is trying to download config files from the Windscribe website and it is failing. "
            "The 'Generate Key' button is missing, or they get an error saying 'You have no WireGuard "
            "keypairs'."
        ),
    },
    {
        "category_id": "static_ip_port_forwarding",
        "title": "Static IP / Port Forwarding Difficulties",
        "description": (
            "User bought a Static IP but cannot get their ports to open. Tickets mention the specific "
            "port number, the application (qBittorrent, Plex), and often include screenshots from "
            "port-checker websites showing the port is 'Closed'."
        ),
    },
]


class AIAnalyzer:
    """Analyzes support tickets using OpenAI — two-phase classification."""

    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o"

    # ── Prompt building ────────────────────────────────────────────────────────

    def build_analysis_prompt(
        self, tickets: List[Dict], template: Optional[str] = None
    ) -> str:
        """
        Build the full two-phase analysis prompt.

        Args:
            tickets: Enriched ticket dicts from SupportPalClient.
                     Must have 'number', 'subject', 'first_message'.
            template: Optional custom prompt stored in MongoDB.
                      Must use {{TICKET_COUNT}}, {{ALL_TICKET_NUMBERS}},
                      {{TICKETS_FORMATTED}} as substitution placeholders.

        Returns:
            Prompt string ready for OpenAI.
        """
        # Format ticket block — use NUMBER only (no internal id exposed to AI)
        tickets_text = []
        for t in tickets:
            tickets_text.append(
                f"Ticket #{t['number']}\n"
                f"Subject: {t['subject']}\n"
                f"Message: {t['first_message'][:600]}\n"
                f"---"
            )
        tickets_formatted = "\n".join(tickets_text)

        all_ticket_numbers = [t["number"] for t in tickets]
        ticket_count = len(tickets)

        # ── Custom template from MongoDB ───────────────────────────────────────
        if template:
            try:
                return (
                    template
                    .replace("{{TICKET_COUNT}}", str(ticket_count))
                    .replace("{{ALL_TICKET_NUMBERS}}", str(all_ticket_numbers))
                    .replace("{{TICKETS_FORMATTED}}", tickets_formatted)
                )
            except Exception as e:
                logger.warning(
                    f"Failed to apply custom template, falling back to built-in: {e}"
                )

        # ── Build the known-categories section ─────────────────────────────────
        categories_block = "\n".join(
            f'{i}. category_id="{c["category_id"]}"\n'
            f'   title="{c["title"]}"\n'
            f'   description: {c["description"]}'
            for i, c in enumerate(KNOWN_CATEGORIES, 1)
        )

        prompt = f"""You are TARS, an AI assistant for the Windscribe VPN support operations team.

=== YOUR TASK ===

You will receive {ticket_count} support tickets. For each ticket you must:

PHASE 1 — KNOWN CATEGORIES
Classify the ticket into exactly one of the {len(KNOWN_CATEGORIES)} known categories below.
These categories represent the normal daily mix. Use the category that best matches the ROOT CAUSE,
not just surface wording. Every ticket must be assigned to a known category unless Phase 2 applies.

PHASE 2 — NEW / EMERGING TRENDS
If a ticket genuinely does not fit ANY of the known categories, place it in a new trend cluster.
A new trend must meet ALL of these criteria:
  - It describes a SPECIFIC, CONCRETE technical issue or pattern (e.g. "iOS 19.2 crash on launch",
    "Turkey ISP blocking WireGuard handshake on port 443")
  - Multiple tickets report the SAME specific problem (at least 2 tickets with a shared root cause)
  - It is NOT just a ticket that is hard to classify — force-fit ambiguous tickets into the closest
    known category instead
  - It is NOT a catch-all or miscellaneous bucket

EXPLICITLY FORBIDDEN in new_trends:
  - Categories named "Miscellaneous", "Other", "General", "Various", "Feedback", or any synonym
  - Catch-all buckets for tickets that don't cleanly fit elsewhere
  - Feature requests, spam, or unrelated vendor emails — assign these to the closest known category

When in doubt, assign to the closest known category. It is perfectly fine (and expected) to have
ZERO new trends on most days. Only flag something as a new trend when it is genuinely novel.

=== KNOWN CATEGORIES ({len(KNOWN_CATEGORIES)} total) ===

{categories_block}

=== STRICT RULES ===

1. EVERY ticket number must appear in EXACTLY ONE place: either in ONE known_category's
   ticket_numbers list OR in ONE new_trend's ticket_numbers list.
   *** CRITICAL: A ticket number MUST NEVER be repeated. Each number appears ONCE in ONE array. ***
   *** If you find yourself writing the same number twice — STOP and move on. ***
2. Sum of all volumes across known_categories + new_trends MUST equal {ticket_count}.
3. All ticket numbers that must be accounted for: {all_ticket_numbers}
4. For known_categories: include ALL {len(KNOWN_CATEGORIES)} category entries in your output,
   even if a category has 0 tickets (set volume=0 and ticket_numbers=[]).
5. For new_trends: only include trends that have volume >= 2 AND describe a specific novel issue.
   An empty new_trends array is the EXPECTED outcome on a normal day.
6. ticket_details: for EVERY ticket number in the input, provide a one-line plain-English summary
   (15–25 words) of what the user is reporting.
7. Keep ticket_numbers arrays COMPACT — just the raw numbers, no extras, no repetitions.

=== OUTPUT FORMAT ===

Return ONLY valid JSON. No markdown, no commentary, no code fences.

IMPORTANT: Output ticket_details FIRST. This forces you to read and summarize every ticket
before you assign them to categories. This ensures no ticket is forgotten.

{{
  "analysis_date": "YYYY-MM-DD",
  "total_tickets_analyzed": {ticket_count},
  "ticket_details": {{
    "TICKET_NUMBER_AS_STRING": "One-line summary of what this user is reporting (15-25 words)"
  }},
  "known_categories": [
    {{
      "category_id": "string (must match one of the category_id values above)",
      "title": "string",
      "ticket_numbers": [list of integer ticket numbers — NO DUPLICATES],
      "volume": integer,
      "summary": "REQUIRED — 1-2 sentence summary of what is happening in THIS batch. Be specific about patterns, protocols, regions, or errors. If volume is 0, write 'No tickets today'."
    }}
  ],
  "new_trends": [
    {{
      "title": "Short specific name (e.g. 'iOS 19.2 Crash on Launch', 'Turkey Block Wave')",
      "ticket_numbers": [list of integer ticket numbers — NO DUPLICATES],
      "volume": integer,
      "description": "2-3 sentences: what is happening, probable root cause, why it doesn't fit known categories",
      "geographic_pattern": "Countries/regions affected, or null"
    }}
  ]
}}

=== TICKETS TO CLASSIFY ({ticket_count} total) ===

{tickets_formatted}

=== FINAL VERIFICATION ===
Before outputting, confirm:
- known_categories array has exactly {len(KNOWN_CATEGORIES)} entries
- sum of all ticket_numbers lengths across known_categories + new_trends == {ticket_count}
- ticket_details has exactly {ticket_count} entries
- every number in {all_ticket_numbers} appears exactly once across all ticket_numbers arrays"""

        return prompt

    # ── API call ───────────────────────────────────────────────────────────────

    def analyze_tickets(
        self, tickets: List[Dict], template: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Run the two-phase analysis and return structured results.

        Args:
            tickets: Enriched ticket dicts from SupportPalClient.
            template: Optional custom prompt template from MongoDB.

        Returns:
            Parsed analysis dict, or None on failure.
        """
        if not tickets:
            logger.warning("No tickets provided for analysis")
            return None

        logger.info(f"Starting AI analysis of {len(tickets)} tickets")
        if template:
            logger.info("Using custom prompt template from MongoDB")

        result_text = ""
        try:
            prompt = self.build_analysis_prompt(tickets, template=template)

            logger.info("Sending tickets to OpenAI for two-phase analysis...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are TARS, a technical support operations analyst for Windscribe VPN. "
                            "You classify support tickets with high precision and flag genuinely new "
                            "issues. You always return valid JSON exactly as specified."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=16384,
                frequency_penalty=0.05,
                response_format={"type": "json_object"},
            )

            result_text = response.choices[0].message.content
            analysis = json.loads(result_text)

            # ── Deduplicate ticket_numbers (AI sometimes repeats them) ─────
            for cat in analysis.get("known_categories", []):
                if "ticket_numbers" in cat:
                    cat["ticket_numbers"] = list(dict.fromkeys(cat["ticket_numbers"]))
                    cat["volume"] = len(cat["ticket_numbers"])
            for trend in analysis.get("new_trends", []):
                if "ticket_numbers" in trend:
                    trend["ticket_numbers"] = list(dict.fromkeys(trend["ticket_numbers"]))
                    trend["volume"] = len(trend["ticket_numbers"])

            known = analysis.get("known_categories", [])
            trends = analysis.get("new_trends", [])

            # ── Validation: check all tickets were assigned ───────────────
            assigned_numbers = set()
            for cat in known:
                for num in cat.get("ticket_numbers", []):
                    assigned_numbers.add(int(num))
            for trend in trends:
                for num in trend.get("ticket_numbers", []):
                    assigned_numbers.add(int(num))

            input_numbers = set(int(t["number"]) for t in tickets)
            missing = input_numbers - assigned_numbers
            total_assigned = sum(c.get("volume", 0) for c in known) + sum(
                t.get("volume", 0) for t in trends
            )

            logger.info(
                f"Analysis complete: {len([c for c in known if c.get('volume', 0) > 0])} "
                f"active known categories, {len(trends)} new trends"
            )
            logger.info(
                f"Ticket assignment: {total_assigned}/{len(tickets)} assigned, "
                f"{len(missing)} missing"
            )
            if missing:
                logger.warning(
                    f"Unassigned ticket numbers ({len(missing)}): "
                    f"{sorted(list(missing))[:20]}{'...' if len(missing) > 20 else ''}"
                )

            for c in known:
                if c.get("volume", 0) > 0:
                    logger.info(
                        f"  [known] {c.get('title')} — {c.get('volume')} tickets"
                    )
            for t in trends:
                logger.info(
                    f"  [trend] {t.get('title')} — {t.get('volume')} tickets"
                )

            return analysis

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.error(f"Response was: {result_text[:500]}")
            return None
        except Exception as e:
            logger.error(f"Error during AI analysis: {e}")
            return None
