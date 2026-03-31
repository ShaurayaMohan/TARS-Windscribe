"""
Sentiment analysis for TARS.

Runs as a separate GPT-4o call after classification.  For each ticket it
returns sentiment, urgency, churn risk, and a one-line summary.

Tickets are processed in batches of BATCH_SIZE to stay within context limits
when full customer conversation threads are included (~8k chars per ticket).

The results are merged into the per-ticket MongoDB documents and aggregated
into a weekly sentiment report every Tuesday.
"""
import json
import logging
from typing import List, Dict

from openai import OpenAI

logger = logging.getLogger(__name__)

BATCH_SIZE = 20
MAX_CONVO_CHARS = 8000

VALID_SENTIMENTS = {"positive", "neutral_confused", "frustrated", "angry"}
VALID_URGENCIES = {"low", "medium", "high", "critical"}
VALID_CHURN = {"low", "medium", "high"}

SYSTEM_MSG = (
    "You are TARS, an expert Customer Experience Analyst "
    "for Windscribe VPN. You assess support ticket sentiment "
    "with precision. You always return valid JSON exactly as "
    "specified."
)


class SentimentAnalyzer:
    """Scores support tickets for sentiment, urgency, and churn risk."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def analyze(self, tickets: List[Dict]) -> Dict[str, Dict]:
        """
        Analyze tickets for sentiment signals in batches.

        Args:
            tickets: list of ticket dicts with 'number', 'subject', and
                     either 'full_conversation' (preferred) or 'first_message'.

        Returns:
            Dict keyed by ticket number (str) -> {sentiment, urgency,
            churn_risk, summary}.  Returns partial results if some batches fail.
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
            f"Sentiment: processing {len(tickets)} tickets in {total_batches} "
            f"batch(es) of up to {BATCH_SIZE}"
        )

        for idx, batch in enumerate(batches, 1):
            try:
                batch_results = self._analyze_batch(batch, idx, total_batches)
                all_results.update(batch_results)
            except Exception as e:
                logger.warning(
                    f"Sentiment batch {idx}/{total_batches} failed: {e} "
                    f"— continuing with remaining batches"
                )

        logger.info(f"Sentiment scored {len(all_results)}/{len(tickets)} tickets total")
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
            f"Sentiment batch {batch_num}/{total_batches}: "
            f"finish_reason={finish_reason}, "
            f"tokens={usage.prompt_tokens}+{usage.completion_tokens}"
            f"={usage.total_tokens}"
        )
        if finish_reason == "length":
            logger.warning(
                f"Sentiment batch {batch_num} cut off by max_tokens"
            )

        raw = json.loads(response.choices[0].message.content)
        results = raw.get("tickets", {})

        cleaned: Dict[str, Dict] = {}
        for num, data in results.items():
            cleaned[str(num)] = {
                "sentiment": data.get("sentiment", "neutral_confused")
                    if data.get("sentiment") in VALID_SENTIMENTS else "neutral_confused",
                "urgency": data.get("urgency", "medium")
                    if data.get("urgency") in VALID_URGENCIES else "medium",
                "churn_risk": data.get("churn_risk", "low")
                    if data.get("churn_risk") in VALID_CHURN else "low",
                "summary": (data.get("summary") or "")[:200],
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

        return f"""You are TARS, an expert Customer Experience Analyst for Windscribe VPN.
Analyze the following batch of {ticket_count} support tickets.

For each ticket, determine the Sentiment, Urgency, Churn Risk, and a One-Line Summary based strictly on the provided text (subject + full customer conversation thread).

=== SCORING DIMENSIONS ===

1. SENTIMENT (Strictly one of: positive, neutral_confused, frustrated, angry)
   - positive: Satisfied, expressing gratitude, complimentary.
   - neutral_confused: Factual bug reports, standard questions, "matter-of-fact" tone, or simple confusion ("how do I do X?", "I don't understand this feature"). Default for basic technical issues and users who are confused but not yet annoyed.
   - frustrated: Clearly annoyed, repeated issues, losing patience, expressing exasperation — "why isn't this working", "I've tried everything". Must show genuine irritation, not just confusion.
   - angry: Hostile, threatening, ALL CAPS, demanding, aggressive ultimatums.

2. URGENCY (Strictly one of: low, medium, high, critical)
   - low: General questions, feature requests, account management, no service impact.
   - medium: Partial degradation, slow speeds, specific server down (but others work), workaround exists.
   - high: Complete connection failure on all protocols, blocked by censorship (e.g., China/Iran), billing failures.
   - critical: Privacy/data breach, account takeover, payment fraud, legal threats.

3. CHURN RISK (Strictly one of: low, medium, high)
   - low: Standard inquiries, user is engaged to fix the issue, asking "how-to" questions, or reporting minor bugs.
   - medium: The user is expressing doubt about the product's value (e.g., "Why am I paying for this?"). Includes persistent technical issues (frequent disconnects) or discovering a feature they need is missing.
   - high: Explicitly requesting cancellation or a full refund. Mentions switching to a competitor by name (e.g., Nord, Express, Proton, Mullvad). Total failure of their primary use case (e.g., "I bought this for streaming and it's blocked," or "Windscribe no longer connects in my restricted network").

4. ONE-LINE SUMMARY (Max 30 words)
   - Write from the customer's perspective but strip out all greetings and emotional fluff. Focus entirely on the core technical or account issue.
   - Be highly specific. Include OS, protocol, server location, or error codes if the user mentions them.
   - EXAMPLES of Bad vs. Good:
     - BAD: "User is angry because the app doesn't work."
     - GOOD: "WireGuard protocol failing to connect on all US East servers from a school WiFi network."
     - BAD: "Customer wants a refund because of crashing."
     - GOOD: "App crashes constantly on Android 14 after the latest update; requesting refund due to unusable service."
     - BAD: "Billing problem."
     - GOOD: "Charged twice for the yearly Pro plan after attempting to upgrade from the free tier."

=== CALIBRATION RULES ===
- Do not hallucinate context. Base your assessment ONLY on the ticket content provided below.
- The conversation may contain multiple customer messages separated by "---". Consider the ENTIRE conversation arc when scoring — a customer who starts calm but becomes frustrated later should be scored as frustrated.
- "Refund" nuance: A request for a *full* refund is HIGH churn risk. A request for a *partial* refund (e.g., "I forgot to use my promo code") is usually LOW or MEDIUM, as they intend to stay.
- Competitor namedrop: If a user compares Windscribe negatively to a competitor, instantly score as HIGH churn risk.
- Profanity alone does not equal 'angry'. Look at intent. "This cool feature is f***ing awesome" is positive.
- Do not overuse 'critical' urgency. A user being unable to connect is 'high' urgency to them, but 'critical' is strictly reserved for security/fraud/legal issues.
- "Frustrated" requires clear signs of annoyance or exasperation — not just confusion. A user who is simply lost or asking questions without irritation should be scored as "neutral_confused".
- Don't over-index on "angry" unless there's clear hostility.

=== OUTPUT FORMAT ===
Return ONLY raw, valid JSON.
Do NOT wrap the output in markdown code blocks (no ```json).
Do NOT include any conversational text, preamble, or commentary.

{{
  "tickets": {{
    "<ticket_number>": {{
      "sentiment": "<value>",
      "urgency": "<value>",
      "churn_risk": "<value>",
      "summary": "<value>"
    }}
  }}
}}

=== TICKETS ===
{tickets_formatted}"""
