"""
AI-powered ticket clustering using OpenAI
Analyzes support tickets and identifies critical issue patterns
"""
import json
import logging
from typing import List, Dict, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


class AIAnalyzer:
    """Analyzes support tickets using OpenAI to identify critical clusters"""
    
    def __init__(self, api_key: str):
        """
        Initialize AI Analyzer
        
        Args:
            api_key: OpenAI API key
        """
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o"  # Using GPT-4o for better analysis
        
    def build_analysis_prompt(self, tickets: List[Dict]) -> str:
        """
        Build the prompt with ticket data for AI analysis
        
        Args:
            tickets: List of ticket dictionaries with id, subject, first_message
            
        Returns:
            Formatted prompt string
        """
        # Format tickets into readable text
        tickets_text = []
        for ticket in tickets:
            ticket_text = f"""
Ticket #{ticket['number']} (ID: {ticket['id']})
Subject: {ticket['subject']}
Message: {ticket['first_message'][:500]}...
Status: {ticket.get('status', 'Unknown')}
Priority: {ticket.get('priority', 'Unknown')}
---"""
            tickets_text.append(ticket_text)
        
        tickets_formatted = "\n".join(tickets_text)
        
        prompt = f"""You are analyzing support tickets for Windscribe, a VPN service. Your job is to identify the top 3 most critical issue clusters from today's tickets.

ANALYSIS PROCESS:
1. Read each ticket carefully - understand what's ACTUALLY broken, not just surface symptoms
2. Extract user location/country if mentioned (this is critical for VPN issues)
3. Identify the root cause - is it a protocol failure? Geographic censorship? Server outage? Payment issue?
4. Group tickets with the SAME root cause together, even if they describe it differently
5. Rank clusters by criticality (volume + severity + user impact)

FOR EACH CLUSTER, PROVIDE:
- **Title**: Short, punchy name for the issue (e.g. "WireGuard Dead in Russia")
- **Volume**: Total number of affected tickets
- **Probable Root Cause**: 2-3 sentence technical explanation. Be specific about WHAT broke, WHY it broke, and HOW it's affecting users. Include protocols, error types, or geographic factors if relevant. Make it detailed but concise.
- **Geographic Pattern**: Which countries/regions are affected (if relevant)
- **User Impact**: What can't users do? (can't connect, can't stream, can't login, etc.)
- **All Ticket IDs**: List every single ticket ID in this cluster

TONE & STYLE:
- Keep it chill but technical - you're talking to the support ops team, not executives
- Use actual technical terms (protocols, server names, error types)
- Be direct - "Netflix Japan is cooked" not "users are experiencing difficulties"
- No corporate fluff

OUTPUT FORMAT:
Return ONLY valid JSON with no additional text:
{{
  "analysis_date": "YYYY-MM-DD",
  "total_tickets_analyzed": {len(tickets)},
  "clusters": [
    {{
      "title": "string",
      "volume": number,
      "probable_root_cause": "string (2-3 detailed sentences)",
      "geographic_pattern": "string or null",
      "user_impact": "string",
      "ticket_ids": [all ticket IDs as integers]
    }}
  ]
}}

Focus on actionable intelligence. What does the team need to know RIGHT NOW?

TICKETS TO ANALYZE:
{tickets_formatted}

Remember: Return ONLY the JSON output, no markdown code blocks or extra text."""

        return prompt
    
    def analyze_tickets(self, tickets: List[Dict]) -> Optional[Dict]:
        """
        Analyze tickets and return clustered results
        
        Args:
            tickets: List of enriched ticket dictionaries
            
        Returns:
            Analysis results as dictionary or None if failed
        """
        if not tickets:
            logger.warning("No tickets provided for analysis")
            return None
        
        logger.info(f"Starting AI analysis of {len(tickets)} tickets")
        
        try:
            # Build the prompt
            prompt = self.build_analysis_prompt(tickets)
            
            # Call OpenAI API
            logger.info("Sending tickets to OpenAI for clustering analysis...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a technical support analyst specializing in VPN service issues. You identify patterns and critical problems from support tickets."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent analysis
                response_format={"type": "json_object"}  # Force JSON output
            )
            
            # Parse response
            result_text = response.choices[0].message.content
            logger.debug(f"Raw AI response: {result_text}")
            
            # Parse JSON
            analysis = json.loads(result_text)
            
            logger.info(f"Analysis complete: {len(analysis.get('clusters', []))} clusters identified")
            
            # Log clusters found
            for i, cluster in enumerate(analysis.get('clusters', []), 1):
                logger.info(
                    f"Cluster {i}: {cluster.get('title')} "
                    f"({cluster.get('volume')} tickets)"
                )
            
            return analysis
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.error(f"Response was: {result_text}")
            return None
            
        except Exception as e:
            logger.error(f"Error during AI analysis: {e}")
            return None
    
    def format_analysis_summary(self, analysis: Dict) -> str:
        """
        Format analysis results into a readable text summary
        
        Args:
            analysis: Analysis dictionary from analyze_tickets
            
        Returns:
            Formatted text summary
        """
        if not analysis:
            return "No analysis available"
        
        lines = []
        lines.append(f"📊 Analysis Date: {analysis.get('analysis_date', 'Unknown')}")
        lines.append(f"🎫 Total Tickets Analyzed: {analysis.get('total_tickets_analyzed', 0)}")
        lines.append(f"🔥 Critical Clusters Found: {len(analysis.get('clusters', []))}")
        lines.append("")
        
        for i, cluster in enumerate(analysis.get('clusters', []), 1):
            lines.append(f"{'='*60}")
            lines.append(f"Cluster #{i}: {cluster.get('title')}")
            lines.append(f"{'='*60}")
            lines.append(f"Volume: {cluster.get('volume')} tickets")
            lines.append(f"Probable Root Cause: {cluster.get('probable_root_cause')}")
            
            if cluster.get('geographic_pattern'):
                lines.append(f"Geographic Pattern: {cluster.get('geographic_pattern')}")
            
            lines.append(f"User Impact: {cluster.get('user_impact')}")
            lines.append(f"Ticket IDs: {', '.join(map(str, cluster.get('ticket_ids', [])))}")
            lines.append("")
        
        return "\n".join(lines)
