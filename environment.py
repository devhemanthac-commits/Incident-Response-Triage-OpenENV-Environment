"""
IncidentTriageEnv — core environment with:
  - Cascading failure penalties (-0.20 per cascade on mis-triage)
  - Time-series trend detection bonus (+0.05 for mentioning trends)
  - False positive detection bonus (+0.10 for correct low-priority triage)
  - Expert team routing with partial credit for alt teams
  - Multi-step episodes (max 2 attempts) with consequence observations
  - Adaptation bonus (+0.05 if agent improves toward correct answer on step 2)
"""

import random
from copy import deepcopy
from models import TriageObservation, TriageAction, TriageReward, LearningSignal
from data import SCENARIOS

_SEVERITY_ORDER = ["P0", "P1", "P2", "P3", "P4"]

# Keywords that indicate the agent is analyzing metric trends
_TREND_KEYWORDS = [
    "trend", "trending", "rate of change", "increasing", "growing",
    "decreasing", "trajectory", "spike pattern", "gradual", "climbing",
    "ramping", "accelerating", "steady rise", "creeping",
]


def _severity_distance(a: str, b: str) -> int:
    return abs(_SEVERITY_ORDER.index(a) - _SEVERITY_ORDER.index(b))


class IncidentTriageEnv:
    MAX_ATTEMPTS = 2  # Multi-step: max 2 attempts per episode
    DONE_THRESHOLD = 0.95

    def __init__(self) -> None:
        self._scenario: dict | None = None
        self._attempt: int = 0
        self._cascade_triggered: bool = False
        self._cascade_penalty_total: float = 0.0
        self._prev_action: TriageAction | None = None  # for adaptation tracking

    # ──────────────────────────────────────────────────────────────────────────
    def reset(self, task_id: str | None = None, seed: int = 42) -> TriageObservation:
        if task_id is not None:
            matches = [s for s in SCENARIOS if s["task_id"] == task_id]
            if not matches:
                raise ValueError(f"Unknown task_id: {task_id!r}")
            self._scenario = deepcopy(matches[0])
        else:
            rng = random.Random(seed)
            self._scenario = deepcopy(rng.choice(SCENARIOS))

        self._attempt = 0
        self._cascade_triggered = False
        self._cascade_penalty_total = 0.0
        self._prev_action = None
        return self._build_observation(step_number=0, feedback="", new_alert="")

    # ──────────────────────────────────────────────────────────────────────────
    def step(self, action: TriageAction) -> tuple[TriageObservation, TriageReward, bool, dict]:
        if self._scenario is None:
            raise RuntimeError("Call reset() before step()")

        self._attempt += 1

        # ── Check for cascading failure BEFORE grading ───────────────────────
        cascade = self._scenario.get("cascade_trigger")
        new_alert = ""
        cascade_feedback = ""

        if cascade and not self._cascade_triggered:
            should_trigger = self._check_cascade_condition(action, cascade)
            if should_trigger:
                self._cascade_triggered = True
                self._cascade_penalty_total += cascade["penalty"]
                cascade_feedback = cascade["feedback"]
                new_alert = cascade["new_alert"]

        # ── Grade action (includes cascade penalty from _cascade_penalty_total)
        reward = self._grade(action)
        done = reward.score >= self.DONE_THRESHOLD or self._attempt >= self.MAX_ATTEMPTS

        # ── Build consequence-aware feedback ─────────────────────────────────
        feedback_parts = [reward.feedback]
        if cascade_feedback:
            feedback_parts.append(cascade_feedback)

        # Inject consequence observation on step 1 if not done
        if self._attempt == 1 and not done:
            consequence = self._scenario.get("consequence_observation", "")
            if consequence:
                feedback_parts.append(f"OBSERVATION: {consequence}")

        combined_feedback = " | ".join(feedback_parts)

        # Track previous action for adaptation bonus
        self._prev_action = action

        obs = self._build_observation(
            step_number=self._attempt,
            feedback=combined_feedback,
            new_alert=new_alert,
        )
        info = {
            "attempt": self._attempt,
            "expected_severity": self._scenario["expected_severity"],
            "expected_team": self._scenario["expected_team"],
            "expected_escalate": self._scenario["expected_escalate"],
            "cascade_triggered": self._cascade_triggered,
            "cascade_penalty_total": self._cascade_penalty_total,
        }
        return obs, reward, done, info

    # ──────────────────────────────────────────────────────────────────────────
    def state(self) -> dict:
        if self._scenario is None:
            return {"status": "not_started"}
        return {
            "task_id": self._scenario["task_id"],
            "incident_id": self._scenario["incident_id"],
            "attempt": self._attempt,
            "max_attempts": self.MAX_ATTEMPTS,
            "cascade_triggered": self._cascade_triggered,
        }

    # ──────────────────────────────────────────────────────────────────────────
    def grade(self, action: TriageAction) -> TriageReward:
        """Public grading without advancing state (for testing)."""
        if self._scenario is None:
            raise RuntimeError("Call reset() before grade()")
        return self._grade(action)

    # ──────────────────────────────────────────────────────────────────────────
    def _check_cascade_condition(self, action: TriageAction, cascade: dict) -> bool:
        """Determine if action triggers a cascading failure."""
        s = self._scenario
        condition = cascade.get("condition", "wrong_severity_or_team")

        if condition == "wrong_severity_or_team":
            sev_wrong = action.severity != s["expected_severity"]
            team_wrong = action.team != s["expected_team"]
            return sev_wrong or team_wrong
        return False

    # ──────────────────────────────────────────────────────────────────────────
    def _grade(self, action: TriageAction) -> TriageReward:
        s = self._scenario
        exp_sev = s["expected_severity"]
        exp_team = s["expected_team"]
        exp_esc = s["expected_escalate"]
        key_indicators: list[str] = s.get("key_indicators", [])
        reasoning_lower = action.reasoning.lower()

        # ── Severity (0.35) ──────────────────────────────────────────────────
        dist = _severity_distance(action.severity, exp_sev)
        if dist == 0:
            sev_score = 0.35
        elif dist == 1:
            sev_score = 0.15
        else:
            sev_score = 0.0

        # ── Routing with expert team matrix (0.30) ───────────────────────────
        team_routing = s.get("team_routing", {})
        if action.team == exp_team:
            route_score = 0.30
        elif action.team in team_routing.get("alt_teams", []):
            alt_penalty = team_routing.get("alt_penalty", 0.15)
            route_score = 0.30 - alt_penalty
        else:
            route_score = 0.0

        # ── Escalation (0.15) ────────────────────────────────────────────────
        esc_score = 0.15 if action.escalate == exp_esc else 0.0

        # ── Reasoning (0.10) ─────────────────────────────────────────────────
        reason_score = 0.0
        if len(action.reasoning) > 30:
            reason_score += 0.05
            matched = sum(1 for kw in key_indicators if kw.lower() in reasoning_lower)
            if matched > 0:
                reason_score += min(0.05, 0.05 * matched / max(len(key_indicators), 1))

        # ── Confidence calibration (0.10) ────────────────────────────────────
        fully_correct = dist == 0 and action.team == exp_team and action.escalate == exp_esc
        if fully_correct:
            calib_score = 0.10 if action.confidence >= 0.75 else 0.05
        else:
            calib_score = 0.10 if action.confidence <= 0.50 else 0.0

        # ── Trend detection bonus (up to +0.05) ─────────────────────────────
        trend_bonus = 0.0
        if any(kw in reasoning_lower for kw in _TREND_KEYWORDS):
            trend_bonus = 0.05

        # ── False positive bonus (up to +0.10) ──────────────────────────────
        fp_bonus = 0.0
        if s.get("is_false_positive", False):
            if action.severity in ("P3", "P4"):
                fp_bonus = s.get("false_positive_bonus", 0.10)

        # ── Adaptation bonus (+0.05 on step 2 if agent improved) ────────────
        adapt_bonus = 0.0
        if self._prev_action is not None and self._attempt >= 2:
            prev_dist = _severity_distance(self._prev_action.severity, exp_sev)
            if dist < prev_dist:
                adapt_bonus += 0.02
            if self._prev_action.team != exp_team and action.team == exp_team:
                adapt_bonus += 0.02
            if self._prev_action.escalate != exp_esc and action.escalate == exp_esc:
                adapt_bonus += 0.01

        # ── Cascade penalty (only for the step that triggered it) ────────────
        cascade_penalty = 0.0
        if self._cascade_triggered and self._attempt == 1:
            cascade_penalty = self._cascade_penalty_total

        # ── Total (capped at 0.0 – 1.0) ────────────────────────────────────
        raw_total = (sev_score + route_score + esc_score + reason_score
                     + calib_score + trend_bonus + fp_bonus + adapt_bonus
                     + cascade_penalty)
        total = round(min(max(raw_total, 0.0), 1.0), 4)

        # ── Feedback ─────────────────────────────────────────────────────────
        parts = []
        if sev_score < 0.35:
            parts.append(f"Severity: got {action.severity}, expected {exp_sev} (off by {dist})")
        if route_score < 0.30:
            if route_score > 0:
                parts.append(f"Routing: got {action.team} (alt team — partial credit), optimal is {exp_team}")
            else:
                parts.append(f"Routing: got {action.team}, expected {exp_team}")
        if esc_score == 0:
            parts.append(f"Escalation: got {action.escalate}, expected {exp_esc}")
        if reason_score < 0.10:
            parts.append(f"Reasoning: include key indicators — {key_indicators[:3]}")
        if calib_score < 0.10:
            parts.append(f"Calibration: confidence {action.confidence:.2f} {'too high' if not fully_correct else 'too low'}")
        if trend_bonus > 0:
            parts.append("Trend analysis: +0.05 bonus for identifying metric trends")
        if fp_bonus > 0:
            parts.append("False positive detection: +0.10 bonus for correct low-priority triage")
        if adapt_bonus > 0:
            parts.append(f"Adaptation: +{adapt_bonus:.3f} bonus for improving from previous attempt")
        if cascade_penalty < 0:
            parts.append(f"CASCADE PENALTY: {cascade_penalty:.2f} — mis-triage caused downstream failures")
        feedback = "; ".join(parts) if parts else "Perfect triage!"

        # Generate learning signals for agent improvement
        learning_signals = []
        key_insights = []

        # Signal 1: Severity assessment
        if dist == 0:
            learning_signals.append(LearningSignal(
                dimension="severity",
                correct=True,
                reason=f"Correctly identified {exp_sev}. Analyzed metrics appropriately.",
                improvement_hint=""
            ))
        else:
            signal_text = f"Got {action.severity}, expected {exp_sev} (off by {dist})"
            hint = f"Look at metric trends: {s.get('key_indicators', [])[0] if s.get('key_indicators') else 'key metrics'}"
            learning_signals.append(LearningSignal(
                dimension="severity",
                correct=False,
                reason=signal_text,
                improvement_hint=hint
            ))
            key_insights.append(f"Severity: {dist} level{'s' if dist > 1 else ''} off")

        # Signal 2: Team routing
        if action.team == exp_team:
            learning_signals.append(LearningSignal(
                dimension="team_routing",
                correct=True,
                reason=f"Correctly routed to {exp_team}. Identified the domain expertise needed.",
                improvement_hint=""
            ))
        elif action.team in team_routing.get("alt_teams", []):
            learning_signals.append(LearningSignal(
                dimension="team_routing",
                correct=False,
                reason=f"Chose {action.team} (alt team). Optimal is {exp_team}.",
                improvement_hint=f"The optimal team {exp_team} has deeper domain knowledge for this issue."
            ))
            key_insights.append(f"Team routing: {action.team} is suboptimal")
        else:
            learning_signals.append(LearningSignal(
                dimension="team_routing",
                correct=False,
                reason=f"Chose wrong team {action.team}. Expected {exp_team}.",
                improvement_hint=f"Analyze symptoms more carefully to identify the root domain."
            ))
            key_insights.append(f"Team routing: {action.team} has no relevant expertise")

        # Signal 3: Escalation decision
        if action.escalate == exp_esc:
            learning_signals.append(LearningSignal(
                dimension="escalation",
                correct=True,
                reason=f"Escalation decision correct: {action.escalate}",
                improvement_hint=""
            ))
        else:
            esc_text = "escalated" if action.escalate else "didn't escalate"
            expected_text = "should escalate" if exp_esc else "should NOT escalate"
            learning_signals.append(LearningSignal(
                dimension="escalation",
                correct=False,
                reason=f"You {esc_text}, but {expected_text}",
                improvement_hint=f"Consider incident scope and team capacity when deciding escalation."
            ))
            key_insights.append(f"Escalation: {expected_text}")

        # Signal 4: Reasoning quality
        if reason_score > 0:
            learning_signals.append(LearningSignal(
                dimension="reasoning_quality",
                correct=True,
                reason=f"Good reasoning: mentioned key indicators and analyzed evidence",
                improvement_hint=""
            ))
        else:
            learning_signals.append(LearningSignal(
                dimension="reasoning_quality",
                correct=False,
                reason=f"Reasoning too vague or missing key indicators",
                improvement_hint=f"Reference specific metrics: {s.get('key_indicators', [])[0:3]}"
            ))

        # Cascade insight
        if cascade_penalty < 0:
            key_insights.append(f"[ALERT] Cascading failure triggered: Wrong triage caused downstream damage")

        # Pattern-based insight
        if s.get("is_false_positive", False) and action.severity in ("P3", "P4"):
            key_insights.append("[INSIGHT] Correctly identified false positive (high metrics but expected behavior)")

        # Trend insight
        if trend_bonus > 0:
            key_insights.append("[INSIGHT] Excellent trend analysis - you recognized metric trajectory patterns")

        return TriageReward(
            score=total,
            severity_score=sev_score,
            routing_score=route_score,
            escalation_score=esc_score,
            reasoning_score=round(reason_score, 4),
            calibration_score=calib_score,
            cascade_penalty=cascade_penalty,
            false_positive_bonus=fp_bonus,
            trend_bonus=trend_bonus,
            adaptation_bonus=round(adapt_bonus, 4),
            feedback=feedback,
            learning_signals=learning_signals,
            key_insights=key_insights,
        )

    # ──────────────────────────────────────────────────────────────────────────
    def _build_observation(self, step_number: int, feedback: str, new_alert: str = "") -> TriageObservation:
        s = self._scenario
        return TriageObservation(
            task_id=s["task_id"],
            incident_id=s["incident_id"],
            step_number=step_number,
            feedback=feedback,
            alert_type=s["alert_type"],
            service_name=s["service_name"],
            error_message=s["error_message"],
            metrics=s["metrics"],
            logs_snippet=s["logs_snippet"],
            time_of_day=s["time_of_day"],
            related_alerts=s["related_alerts"],
            service_dependencies=s["service_dependencies"],
            recent_deployments=s["recent_deployments"],
            new_alert=new_alert,
        )
