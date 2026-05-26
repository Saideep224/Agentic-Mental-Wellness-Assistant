"""
Behavior Agent - parses and analyzes user's behavioral and routine patterns.
"""

from typing import Dict, Any

class BehaviorAgent:
    """
    Logical agent responsible for analyzing:
    - Productivity patterns
    - Sleep issues
    - Procrastination
    - Routine consistency
    """

    def analyze(self, raw_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract behavioral insights from the single structured Gemini analysis.
        """
        data = raw_analysis.get("behavior_agent", {})

        # Fallback values if missing
        return {
            "productivity_patterns": data.get("productivity_patterns", "none detected"),
            "sleep_issues": data.get("sleep_issues", "none detected"),
            "procrastination": data.get("procrastination", "low"),
            "routine_consistency": data.get("routine_consistency", "stable")
        }

behavior_agent = BehaviorAgent()
