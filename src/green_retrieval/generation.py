"""LLM-based response generation using Groq."""

from typing import Any, Dict

from groq import Groq

from .config import Config

SYSTEM_PROMPT = """You are an expert plant pathologist and agricultural advisor. Your expertise includes disease diagnosis, treatment protocols, and integrated pest management.

Your communication style:
- Clear, concise, and action-oriented
- Use simple language accessible to farmers and gardeners
- Provide specific, practical advice (not vague generalities)
- Include dosages, timing, and application methods when relevant
- Acknowledge limitations or uncertainties honestly

Your response structure:
1. Confirmation: State clearly if prediction matches EPPO data (Yes/No + reasoning)
2. Disease Overview: Explain cause, symptoms, and impact in 2-3 sentences
3. Treatment: Provide 3-5 concrete actions with implementation details
4. Prevention: List 3-5 preventive measures in priority order

Avoid:
- Generic advice like "maintain good hygiene" without specifics
- Overly technical jargon without explanation
- Unverified information not supported by EPPO data
- Recommending products without active ingredients"""


class ResponseGenerator:
    """Generator for LLM-based disease diagnosis responses."""

    def __init__(self, api_key: str = None, model: str = None):
        """Initialize generator.

        Args:
            api_key: Groq API key (defaults to Config.GROQ_API_KEY)
            model: Model name (defaults to Config.GROQ_MODEL)
        """
        self.api_key = api_key or Config.GROQ_API_KEY
        self.model = model or Config.GROQ_MODEL
        self.client = Groq(api_key=self.api_key) if self.api_key else None
        self.call_count = 0

    def _format_facts(self, facts: Dict[str, Any]) -> str:
        """Format EPPO facts for prompt.

        Args:
            facts: Dictionary with overview, names, and hosts data

        Returns:
            Formatted text for LLM prompt
        """
        parts = []
        overview = facts.get("overview") or {}

        if isinstance(overview, dict):
            prefname = overview.get("prefname")
            eppocode = overview.get("eppocode")
            if prefname:
                parts.append(f"Disease/Pest: {prefname}")
            if eppocode:
                code = (
                    eppocode.get("eppocode")
                    if isinstance(eppocode, dict)
                    else eppocode
                )
                if code:
                    parts.append(f"EPPO Code: {code}")

        # Add common names
        common_names = []
        for name_entry in facts.get("names") or []:
            if isinstance(name_entry, dict) and name_entry.get("fullname"):
                common_names.append(name_entry["fullname"])
        if common_names:
            parts.append(f"Also known as: {', '.join(common_names[:5])}")

        # Add affected plants
        hosts = []
        for host_entry in facts.get("hosts") or []:
            if isinstance(host_entry, dict) and host_entry.get("prefname"):
                host_name = host_entry["prefname"]
                classification = host_entry.get("class_label", "")
                if classification:
                    hosts.append(f"{host_name} ({classification})")
                else:
                    hosts.append(host_name)
        if hosts:
            parts.append(f"Commonly affects: {', '.join(hosts[:10])}")

        return "\n".join(parts) if parts else ""

    def generate(self, cv_label: str, facts: Dict[str, Any]) -> str:
        """Generate diagnosis response from EPPO facts.

        Args:
            cv_label: Original CV model prediction label
            facts: EPPO facts dictionary

        Returns:
            Generated response text
        """
        formatted = self._format_facts(facts)
        if not formatted.strip():
            return "I cannot provide a diagnosis: no EPPO-backed facts are available for this label."

        if not self.client:
            return "I cannot generate a response: Groq API key is not set."

        user_content = f'''Vision Model Prediction: "{cv_label}"

=== EPPO DATABASE INFORMATION ===
{formatted}

=== YOUR TASK ===
Analyze the prediction against EPPO data and provide a structured response:

**1. CONFIRMATION**
   - Does the prediction match the EPPO disease? (YES/NO)
   - Explain your reasoning (2-3 sentences)
   - If NO, specify what the prediction likely refers to

**2. DISEASE OVERVIEW**
   - Causative agent (pathogen type and scientific name)
   - Primary symptoms (visible signs on plant)
   - Economic/agricultural impact

**3. TREATMENT OPTIONS** (in order of effectiveness)
   - Option 1: [Method] - [Active ingredient/approach] - [Application timing]
   - Option 2: [Method] - [Active ingredient/approach] - [Application timing]
   - Option 3: [Method] - [Active ingredient/approach] - [Application timing]
   
**4. PREVENTION STRATEGIES** (proactive measures)
   - Priority 1: [Most critical preventive action]
   - Priority 2: [Second most important]
   - Priority 3: [Additional preventive measure]

Keep each section concise (3-5 bullet points max). Focus on what farmers can DO, not just what to know.'''

        try:
            self.call_count += 1
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                model=self.model,
                max_completion_tokens=Config.GROQ_MAX_TOKENS,
                temperature=Config.GROQ_TEMPERATURE,
            )
            content = response.choices[0].message.content if response.choices else None
            return (
                (content or "").strip()
                or "I could not generate a response from the provided facts."
            )
        except Exception as e:
            return f"I cannot generate a response: {str(e)}"

    def get_stats(self) -> Dict[str, int]:
        """Get generator statistics.

        Returns:
            Dictionary with call_count
        """
        return {"call_count": self.call_count}