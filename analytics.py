"""
Agent performance analytics - detailed profiling and insights.
"""

from typing import Any
from collections import defaultdict
import json


class AgentAnalytics:
    """Analyze agent performance across scenarios."""

    def __init__(self, agent_name: str, results: list[dict]):
        """
        Args:
            agent_name: Name of the agent (e.g., "gpt-4", "claude-3")
            results: List of scenario results with structure:
                {
                    "task_id": "easy-1",
                    "reward": {
                        "score": 0.75,
                        "severity_score": 0.35,
                        "routing_score": 0.30,
                        ...
                    }
                }
        """
        self.agent_name = agent_name
        self.results = results

    def analyze(self) -> dict:
        """Run full analysis and return insights."""
        return {
            "agent_name": self.agent_name,
            "overall": self._analyze_overall(),
            "by_dimension": self._analyze_dimensions(),
            "by_difficulty": self._analyze_difficulty(),
            "strengths": self._identify_strengths(),
            "weaknesses": self._identify_weaknesses(),
            "patterns": self._identify_patterns(),
        }

    def _analyze_overall(self) -> dict:
        """Overall performance metrics."""
        if not self.results:
            return {}

        scores = [r["reward"]["score"] for r in self.results if "reward" in r]
        if not scores:
            return {}

        return {
            "average_score": round(sum(scores) / len(scores), 4),
            "min_score": round(min(scores), 4),
            "max_score": round(max(scores), 4),
            "total_scenarios": len(scores),
        }

    def _analyze_dimensions(self) -> dict:
        """Performance by decision dimension."""
        dimensions = {
            "severity": [],
            "routing": [],
            "escalation": [],
            "reasoning": [],
            "calibration": [],
            "cascade_handling": [],
            "false_positive_detection": [],
            "trend_analysis": [],
        }

        for result in self.results:
            if "reward" not in result:
                continue
            r = result["reward"]
            dimensions["severity"].append(r.get("severity_score", 0))
            dimensions["routing"].append(r.get("routing_score", 0))
            dimensions["escalation"].append(r.get("escalation_score", 0))
            dimensions["reasoning"].append(r.get("reasoning_score", 0))
            dimensions["calibration"].append(r.get("calibration_score", 0))
            dimensions["cascade_handling"].append(max(0, -r.get("cascade_penalty", 0)))  # How well avoided cascades
            dimensions["false_positive_detection"].append(r.get("false_positive_bonus", 0))
            dimensions["trend_analysis"].append(r.get("trend_bonus", 0))

        return {
            dim: {
                "avg": round(sum(scores) / len(scores), 4) if scores else 0,
                "max": round(max(scores), 4) if scores else 0,
                "accuracy": round(
                    sum(1 for s in scores if s > 0) / len(scores) * 100, 1
                )
                if scores
                else 0,
            }
            for dim, scores in dimensions.items()
        }

    def _analyze_difficulty(self) -> dict:
        """Performance breakdown by difficulty level."""
        by_difficulty = defaultdict(list)

        for result in self.results:
            if "task_id" not in result or "reward" not in result:
                continue
            task_id = result["task_id"]
            score = result["reward"]["score"]

            # Extract difficulty from task_id
            if task_id.startswith("easy"):
                difficulty = "easy"
            elif task_id.startswith("medium"):
                difficulty = "medium"
            elif task_id.startswith("hard"):
                difficulty = "hard"
            elif task_id.startswith("false-positive"):
                difficulty = "false-positive"
            else:
                continue

            by_difficulty[difficulty].append(score)

        return {
            diff: {
                "avg_score": round(sum(scores) / len(scores), 4),
                "scenarios_completed": len(scores),
            }
            for diff, scores in by_difficulty.items()
        }

    def _identify_strengths(self) -> list[str]:
        """Identify what the agent does well."""
        strengths = []
        dims = self._analyze_dimensions()

        # High accuracy dimensions
        high_accuracy = [dim for dim, metrics in dims.items() if metrics.get("accuracy", 0) >= 90]
        if high_accuracy:
            strengths.append(f"Excellent accuracy on {', '.join(high_accuracy)}")

        # Bonus scores
        has_fp_bonus = any(r.get("reward", {}).get("false_positive_bonus", 0) > 0 for r in self.results)
        if has_fp_bonus:
            strengths.append("Strong false positive detection (+0.10 bonus earned)")

        has_trend_bonus = any(r.get("reward", {}).get("trend_bonus", 0) > 0 for r in self.results)
        if has_trend_bonus:
            strengths.append("Excellent trend analysis skills (+0.05 bonus earned)")

        # Cascade avoidance
        cascade_penalties = [r.get("reward", {}).get("cascade_penalty", 0) for r in self.results]
        if sum(1 for p in cascade_penalties if p == 0) >= len(cascade_penalties) * 0.8:
            strengths.append("Strong cascade avoidance (avoided 80%+ of failures)")

        return strengths if strengths else ["Consistent performance across most dimensions"]

    def _identify_weaknesses(self) -> list[str]:
        """Identify improvement areas."""
        weaknesses = []
        dims = self._analyze_dimensions()

        # Low accuracy dimensions
        low_accuracy = [dim for dim, metrics in dims.items() if metrics.get("accuracy", 0) < 70]
        if low_accuracy:
            weaknesses.append(f"Inconsistent on {', '.join(low_accuracy[:2])}")

        # Over/under escalation
        escalation_scores = [r.get("reward", {}).get("escalation_score", 0) for r in self.results]
        escalation_acc = (sum(1 for s in escalation_scores if s > 0) / len(escalation_scores) * 100) if escalation_scores else 100
        if escalation_acc < 70:
            weaknesses.append("Conservative escalation decisions (under-escalates 30%+)")

        # Cascade failures
        cascade_penalties = [r.get("reward", {}).get("cascade_penalty", 0) for r in self.results]
        if any(p < 0 for p in cascade_penalties):
            count = sum(1 for p in cascade_penalties if p < 0)
            weaknesses.append(f"Triggered cascading failures {count} times (avoid with better severity/routing)")

        return weaknesses if weaknesses else []

    def _identify_patterns(self) -> dict:
        """Identify decision patterns."""
        patterns = {
            "over_escalates": False,
            "under_escalates": False,
            "severity_inflation": False,
            "confuses_teams": False,
            "reasoning_quality": "moderate",
        }

        # Check escalation pattern
        escalation_scores = [r.get("reward", {}).get("escalation_score", 0) for r in self.results]
        if escalation_scores and sum(escalation_scores) == 0:
            patterns["under_escalates"] = True

        # Check severity pattern
        severity_scores = [r.get("reward", {}).get("severity_score", 0) for r in self.results]
        if severity_scores and sum(1 for s in severity_scores if s == 0) / len(severity_scores) > 0.5:
            patterns["severity_inflation"] = True

        # Check reasoning
        reasoning_scores = [r.get("reward", {}).get("reasoning_score", 0) for r in self.results]
        if reasoning_scores:
            avg_reasoning = sum(reasoning_scores) / len(reasoning_scores)
            if avg_reasoning > 0.07:
                patterns["reasoning_quality"] = "excellent"
            elif avg_reasoning < 0.03:
                patterns["reasoning_quality"] = "poor"

        return patterns

    def comparison_with(self, other_analytics: "AgentAnalytics") -> dict:
        """Compare this agent with another."""
        self_overall = self._analyze_overall().get("average_score", 0)
        other_overall = other_analytics._analyze_overall().get("average_score", 0)

        return {
            "self_agent": self.agent_name,
            "other_agent": other_analytics.agent_name,
            "self_score": round(self_overall, 4),
            "other_score": round(other_overall, 4),
            "difference": round(self_overall - other_overall, 4),
            "winner": self.agent_name if self_overall > other_overall else other_analytics.agent_name,
            "self_strengths": self._identify_strengths(),
            "other_strengths": other_analytics._identify_strengths(),
        }
