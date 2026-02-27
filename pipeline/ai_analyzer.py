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
            "as high-risk. "
            "NOT for cases where the Windscribe app or browser extension itself is causing technical "
            "side-effects (audio failures, video black screens, WebRTC issues, crashes) — those are "
            "new_trend candidates."
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
        # Compact format: just id and title, one line each — saves input tokens
        categories_block = "\n".join(
            f'  "{c["category_id"]}": "{c["title"]}"'
            for c in KNOWN_CATEGORIES
        )
        # Full descriptions for context (separate block)
        categories_detail = "\n".join(
            f'{i}. category_id="{c["category_id"]}"\n'
            f'   title="{c["title"]}"\n'
            f'   description: {c["description"]}'
            for i, c in enumerate(KNOWN_CATEGORIES, 1)
        )

        prompt = f"""You are TARS, an AI assistant for the Windscribe VPN support operations team.

=== YOUR TASK (two passes) ===

You will receive {ticket_count} support tickets. Work in this order:

PASS 1 — NEW TREND SCAN:
  Scan ALL tickets first. Look for groups of 2+ tickets that share the same
  specific root cause which is NOT described by any of the known categories below.
  If you find such a group, mark those tickets as a new trend.

PASS 2 — CLASSIFY THE REST:
  Assign every remaining ticket to exactly one known category.
  Write a 1-2 sentence summary for each category that has tickets.

=== NEW TREND RULES ===
A new trend is any recurring issue where >= 2 tickets share the same specific
root cause AND that root cause is not already described by a known category.
The PROBLEM TYPE itself matters — if no known category covers this KIND of
problem, it is a new trend regardless of surface-level keyword similarity.

Most days will have 0-2 new trends. Zero is fine. So is two or three if the data supports it.

Constraints:
  - Minimum 2 tickets to form a trend
  - NOT a catch-all (forbidden titles: "Miscellaneous", "Other", "General", "Various", "Feedback", "Unrelated", "Unknown")
  - SPAM, vendor emails, off-topic emails are NOT trends — classify them into the closest known category

A ticket only fits a known category if its core problem type genuinely matches
that category's scope. When in doubt, prefer new_trend over forcing a bad fit.

=== KNOWN CATEGORIES ===
{categories_detail}

=== HOW TO WRITE category_summaries ===

Summaries must describe THIS SPECIFIC BATCH of tickets — what you actually saw in the data.
Do NOT just rephrase the category definition.

BAD (generic, just echoes the definition):
  "refund_requests": "Refund requests are from users who want their money back."
  "lost_access_password_reset": "Users cannot log into their account."

GOOD (specific to this batch):
  "refund_requests": "9 refund requests, mostly from users in Iran and Russia blocked after the Jan wave. 3 cite expired Paymentwall transactions."
  "lost_access_password_reset": "14 lockouts — majority forgot their password; 3 signed up via Apple and lost the linked email."

Write 1-2 sentences. Mention specific numbers, regions, protocols, platforms, or error patterns you saw.

=== OUTPUT FORMAT ===

Return ONLY valid JSON. No markdown, no commentary, no code fences.

The "classifications" object is the most important part. It MUST contain one entry for every
ticket number. The key is the ticket number as a string, the value is the category_id.

{{
  "analysis_date": "YYYY-MM-DD",
  "category_summaries": {{
    "category_id": "specific 1-2 sentence summary describing THIS batch (not the category definition)",
    ... only for categories that have at least 1 ticket ...
  }},
  "new_trends": [
    {{
      "title": "Short specific name (e.g. 'iOS 18.3 Crash on Launch', 'Turkey WireGuard Block Wave')",
      "ticket_numbers": [integer ticket numbers — minimum 2],
      "volume": integer,
      "description": "2-3 sentences: what is happening, probable root cause, why it is genuinely new",
      "geographic_pattern": "Countries/regions affected, or null"
    }}
  ],
  "classifications": {{
    "TICKET_NUMBER": "category_id",
    ... one entry for EVERY ticket in the input ...
  }},
  "ticket_summaries": {{
    "TICKET_NUMBER": "one-liner max 12 words — what is the user's actual problem",
    ... one entry for EVERY ticket in the input ...
  }}
}}

HOW TO WRITE ticket_summaries — describe what the USER actually needs, not the category name:
  BAD: "User has a connection problem" / "Payment issue" / "Refund request"
  GOOD: "Can't connect via WireGuard on Rostelecom ISP, Russia" / "Crypto payment sent 3 days ago, account still free" / "Forgot password, no longer has access to signup email"

CRITICAL — classifications AND ticket_summaries must each have EXACTLY {ticket_count} entries:
{all_ticket_numbers}

=== TICKETS TO CLASSIFY ({ticket_count} total) ===

{tickets_formatted}"""

        return prompt

    # ── API call ───────────────────────────────────────────────────────────────

    def analyze_tickets(
        self, tickets: List[Dict], template: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Run the two-phase analysis and return structured results.

        The AI outputs a flat classifications dict {ticket_number: category_id}.
        Python then groups tickets into the known_categories structure.
        This eliminates the AI's tendency to drop tickets when building nested arrays.

        Args:
            tickets: Enriched ticket dicts from SupportPalClient.
            template: Optional custom prompt template from MongoDB.

        Returns:
            Parsed analysis dict with known_categories / new_trends, or None on failure.
        """
        if not tickets:
            logger.warning("No tickets provided for analysis")
            return None

        logger.info(f"Starting AI analysis of {len(tickets)} tickets")
        if template:
            logger.info("Using custom prompt template from MongoDB")

        # Build a lookup of valid category IDs for validation
        valid_category_ids = {c["category_id"] for c in KNOWN_CATEGORIES}
        # Fallback category for any ticket with an unrecognised / missing classification
        FALLBACK_CATEGORY = "plan_feature_confusion"

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
                max_tokens=8192,
                frequency_penalty=0.05,
                response_format={"type": "json_object"},
            )

            # ── Log token usage and finish reason ─────────────────────────
            finish_reason = response.choices[0].finish_reason
            usage = response.usage
            logger.info(
                f"OpenAI response: finish_reason={finish_reason}, "
                f"input_tokens={usage.prompt_tokens}, "
                f"output_tokens={usage.completion_tokens}, "
                f"total_tokens={usage.total_tokens}"
            )
            if finish_reason == "length":
                logger.warning(
                    "Response was CUT OFF by max_tokens limit — increase max_tokens!"
                )

            result_text = response.choices[0].message.content
            raw = json.loads(result_text)

            # ── Build known_categories from flat classifications dict ──────
            classifications: Dict[str, str] = raw.get("classifications", {})
            ticket_summaries: Dict[str, str] = raw.get("ticket_summaries", {})
            category_summaries: Dict[str, str] = raw.get("category_summaries", {})
            trends_raw: list = raw.get("new_trends", [])

            # Collect ticket numbers that go to new trends so we don't double-count
            trend_ticket_numbers: set = set()
            for trend in trends_raw:
                for num in trend.get("ticket_numbers", []):
                    trend_ticket_numbers.add(str(num))

            # Group by category_id
            category_tickets: Dict[str, List[int]] = {
                c["category_id"]: [] for c in KNOWN_CATEGORIES
            }

            input_numbers = {str(t["number"]) for t in tickets}
            classified = set()
            unrecognised = []

            for num_str, cat_id in classifications.items():
                if num_str not in input_numbers:
                    continue  # AI hallucinated a ticket number — ignore
                if num_str in trend_ticket_numbers:
                    classified.add(num_str)
                    continue  # Ticket is in a new trend, handled below
                if cat_id in valid_category_ids:
                    category_tickets[cat_id].append(int(num_str))
                    classified.add(num_str)
                else:
                    unrecognised.append(num_str)

            # Force-assign unrecognised category IDs to fallback
            if unrecognised:
                logger.warning(
                    f"{len(unrecognised)} tickets had unrecognised category IDs "
                    f"→ reassigned to '{FALLBACK_CATEGORY}': {unrecognised[:10]}"
                )
                for num_str in unrecognised:
                    category_tickets[FALLBACK_CATEGORY].append(int(num_str))
                    classified.add(num_str)

            # Force-assign tickets missing from classifications entirely
            missing = input_numbers - classified - trend_ticket_numbers
            if missing:
                logger.warning(
                    f"{len(missing)} tickets were omitted from AI classifications "
                    f"→ force-assigned to '{FALLBACK_CATEGORY}': "
                    f"{sorted(list(missing))[:20]}{'...' if len(missing) > 20 else ''}"
                )
                for num_str in missing:
                    category_tickets[FALLBACK_CATEGORY].append(int(num_str))

            # ── Validate and clean new_trends ─────────────────────────────
            # Discard any trend that doesn't meet minimum bar (volume < 2 OR
            # generic/empty title). Rescued tickets get reclassified from the
            # flat classifications dict, or fall back to the fallback category.
            GENERIC_TITLES = {"unknown", "unknown trend", "misc", "miscellaneous",
                               "other", "general", "various", "feedback", "n/a"}

            new_trends = []
            for trend in trends_raw:
                nums = list(dict.fromkeys(trend.get("ticket_numbers", [])))
                title = (trend.get("title") or "").strip()
                volume = len(nums)

                title_is_generic = title.lower() in GENERIC_TITLES or not title

                if volume < 2 or title_is_generic:
                    # Rescue these tickets back into known categories
                    rescued_count = 0
                    for num in nums:
                        num_str = str(num)
                        cat_id = classifications.get(num_str)
                        if cat_id and cat_id in valid_category_ids:
                            category_tickets[cat_id].append(int(num_str))
                        else:
                            category_tickets[FALLBACK_CATEGORY].append(int(num_str))
                        rescued_count += 1
                    if rescued_count:
                        reason = (
                            f"volume={volume} < 2" if volume < 2
                            else f"generic title '{title}'"
                        )
                        logger.info(
                            f"Discarded trend '{title}' ({reason}) — "
                            f"{rescued_count} tickets rescued to known categories"
                        )
                    continue  # skip — don't add to new_trends

                new_trends.append({**trend, "ticket_numbers": nums, "volume": volume})

            # Rebuild known_categories now that rescued tickets may have changed volumes
            known_categories = []
            for cat in KNOWN_CATEGORIES:
                cid = cat["category_id"]
                nums = list(dict.fromkeys(category_tickets[cid]))
                known_categories.append({
                    "category_id": cid,
                    "title": cat["title"],
                    "ticket_numbers": nums,
                    "volume": len(nums),
                    "summary": category_summaries.get(cid, None),
                })

            # Build final analysis object in the same shape the rest of the pipeline expects
            analysis = {
                "analysis_date": raw.get("analysis_date", ""),
                "total_tickets_analyzed": len(tickets),
                "known_categories": known_categories,
                "new_trends": new_trends,
                # Raw per-ticket summaries — keyed by ticket number as string
                # Used by pipeline/analyzer.py to build ticket_details
                "ticket_summaries": {str(k): v for k, v in ticket_summaries.items()},
            }

            # ── Summary logging ───────────────────────────────────────────
            total_assigned = sum(c["volume"] for c in known_categories) + sum(
                t["volume"] for t in new_trends
            )
            active = [c for c in known_categories if c["volume"] > 0]
            logger.info(
                f"Analysis complete: {len(active)} active known categories, "
                f"{len(new_trends)} new trends, "
                f"{total_assigned}/{len(tickets)} tickets assigned"
            )
            for c in active:
                logger.info(f"  [known] {c['title']} — {c['volume']} tickets")
            for t in new_trends:
                logger.info(f"  [trend] {t.get('title')} — {t.get('volume')} tickets")

            return analysis

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.error(f"Response was: {result_text[:500]}")
            return None
        except Exception as e:
            logger.error(f"Error during AI analysis: {e}")
            return None
