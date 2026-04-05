"""
Baseline LLM agent for the Incident Response Triage environment.

Stdout protocol  : [START] / [STEP] / [END]
Debug / errors   : stderr only
LLM calls budget : max ~72 per run (18 scenarios × 2 attempts × ~2 LLM calls)
                   Well under 20 min with gpt-4o-mini.
"""

import json
import os
import random
import re
import sys
from typing import Any

import requests
from openai import OpenAI

API_BASE_URL: str = os.environ.get("API_BASE_URL", "http://localhost:5000")
MODEL_NAME: str = os.environ.get("MODEL_NAME", "gpt-4o-mini")
OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")

TASK_IDS = [
    ("easy-1", "easy-2", "easy-3", "easy-4", "easy-5"),
    ("medium-1", "medium-2", "medium-3", "medium-4", "medium-5"),
    ("hard-1", "hard-2", "hard-3", "hard-4", "hard-5"),
    ("false-positive-1", "false-positive-2", "false-positive-3"),
]
TASK_NAMES = ["easy", "medium", "hard", "false-positive"]

_SYSTEM_PROMPT = """You are an expert SRE on-call engineer performing incident triage.
Analyze the incident observation and return ONLY a JSON object with these exact fields:
{
  "severity": "P0|P1|P2|P3|P4",
  "team": "backend|frontend|infra|database|security|network",
  "escalate": true|false,
  "confidence": 0.0-1.0,
  "reasoning": "concise explanation referencing specific metrics, log evidence, and trends"
}

Severity guide: P0=complete outage/security breach, P1=major degradation/data at risk,
P2=significant impact/SLO breach, P3=minor degradation/warning, P4=informational.

IMPORTANT analysis guidelines:
- Metrics are TIME SERIES (last 5 minutes). Analyze TRENDS: is the metric increasing,
  stable, or spiking? Rate of change matters.
- Some alerts may be FALSE POSITIVES (scheduled jobs, staging environments, canary deploys).
  Correctly identifying expected behavior as low-priority shows skill.
- Consider cascading effects: wrong triage can cause downstream failures.
- Route to the OPTIMAL team. Wrong team costs response time.
- If previous feedback is provided, ADAPT your response based on it.
Return ONLY valid JSON — no markdown fences, no extra text."""


def _log(*args: Any) -> None:
    print(*args, file=sys.stderr, flush=True)


def _reset(task_id: str) -> dict:
    resp = requests.post(f"{API_BASE_URL}/reset", json={"task_id": task_id}, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _step(action: dict) -> dict:
    resp = requests.post(f"{API_BASE_URL}/step", json=action, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _format_metrics_timeseries(metrics: dict) -> str:
    """Format time-series metrics as a readable trajectory table."""
    timestamps = metrics.get("timestamps", ["T-4min", "T-3min", "T-2min", "T-1min", "T-now"])
    lines = [f"  {'Metric':<22} {'  '.join(f'{t:>7}' for t in timestamps)}"]
    lines.append("  " + "-" * len(lines[0]))

    for key, values in metrics.items():
        if key == "timestamps":
            continue
        if isinstance(values, list):
            formatted = "  ".join(f"{v:7.1f}" for v in values)
            # Add trend indicator
            if len(values) >= 2:
                diff = values[-1] - values[0]
                if diff > 5:
                    trend = " ▲"
                elif diff < -5:
                    trend = " ▼"
                else:
                    trend = " ─"
            else:
                trend = ""
            lines.append(f"  {key:<22} {formatted}{trend}")
        else:
            lines.append(f"  {key:<22} {values}")

    return "\n".join(lines)


def _format_observation(obs: dict) -> str:
    metrics = obs.get("metrics", {})
    metrics_str = _format_metrics_timeseries(metrics)
    deps = ", ".join(obs.get("service_dependencies", []))
    alerts = ", ".join(obs.get("related_alerts", []))
    deployments = obs.get("recent_deployments", [])
    deploy_str = (
        "; ".join(
            f"{d['service']} {d['version']} by {d['author']} at {d['timestamp']}"
            for d in deployments
        )
        if deployments
        else "none"
    )
    feedback = obs.get("feedback", "")
    new_alert = obs.get("new_alert", "")

    lines = [
        f"=== INCIDENT {obs['incident_id']} (attempt {obs['step_number']}) ===",
        f"Alert type   : {obs['alert_type']}",
        f"Service      : {obs['service_name']}",
        f"Error        : {obs['error_message']}",
        f"Time         : {obs['time_of_day']}",
        f"Related alerts: {alerts}",
        f"Dependencies : {deps}",
        f"Recent deploys: {deploy_str}",
        f"\nMetrics (last 5 minutes — analyze trends):\n{metrics_str}",
        f"\nLogs:\n{obs['logs_snippet']}",
    ]
    if new_alert:
        lines.append(f"\n⚠️ NEW CASCADING ALERT: {new_alert}")
    if feedback:
        lines.append(f"\nPrevious feedback: {feedback}")
    return "\n".join(lines)


def _parse_action(raw: str) -> dict | None:
    """Robustly parse JSON from LLM response (handles markdown fences)."""
    raw = raw.strip()
    # strip markdown fences
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)
    raw = raw.strip()
    # find first {...} block
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group())
        # normalise types
        if isinstance(data.get("escalate"), str):
            data["escalate"] = data["escalate"].lower() == "true"
        if isinstance(data.get("confidence"), str):
            data["confidence"] = float(data["confidence"])
        return data
    except (json.JSONDecodeError, ValueError):
        return None


# Seeded RNG for reproducible mock LLM responses
_mock_rng = random.Random(42)


def _call_llm(client: OpenAI, prompt: str) -> str:
    # --- MOCK LLM OVERRIDE FOR TESTING (reproducible) ---
    if os.environ.get("MOCK_LLM", "false").lower() == "true":
        severity = _mock_rng.choice(["P0", "P1", "P2", "P3", "P4"])
        team = _mock_rng.choice(["backend", "frontend", "infra", "database", "security", "network"])
        escalate = _mock_rng.choice([True, False])
        confidence = round(_mock_rng.uniform(0.3, 0.95), 2)
        reasoning_options = [
            "Looks like a simple spike.",
            "The memory is steadily trending upward, rate of change is concerning.",
            "This is expected behavior for a scheduled backup.",
        ]
        action = {"severity": severity, "team": team, "escalate": escalate, "confidence": confidence, "reasoning": _mock_rng.choice(reasoning_options)}
        return json.dumps(action)
    # -------------------------------------

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
    )
    return response.choices[0].message.content or ""


def _format_learning_signals(reward: dict) -> str:
    """Format learning signals into actionable prompt context for step 2."""
    signals = reward.get("learning_signals", [])
    insights = reward.get("key_insights", [])
    if not signals and not insights:
        return ""

    lines = ["\n=== STRUCTURED FEEDBACK FROM PREVIOUS ATTEMPT ==="]
    incorrect = [s for s in signals if not s.get("correct", True)]
    correct = [s for s in signals if s.get("correct", True)]

    if correct:
        lines.append("What you got RIGHT:")
        for s in correct:
            lines.append(f"  [OK] {s['dimension']}: {s['reason']}")

    if incorrect:
        lines.append("What you got WRONG — fix these:")
        for s in incorrect:
            lines.append(f"  [FIX] {s['dimension']}: {s['reason']}")
            if s.get("improvement_hint"):
                lines.append(f"        Hint: {s['improvement_hint']}")

    if insights:
        lines.append("Key insights:")
        for insight in insights:
            lines.append(f"  {insight}")

    lines.append("=== USE THIS FEEDBACK TO IMPROVE YOUR ANSWER ===")
    return "\n".join(lines)


def run_episode(client: OpenAI, task_id: str) -> dict:
    """Run one episode (up to MAX_ATTEMPTS steps) for a single task_id."""
    _log(f"  [episode] task_id={task_id}")
    obs = _reset(task_id)
    episode_reward = None
    done = False
    prev_reward = None  # track step-1 reward for learning signal injection

    while not done:
        prompt = _format_observation(obs)

        # On step 2+, inject structured learning signals from previous attempt
        if prev_reward is not None:
            learning_context = _format_learning_signals(prev_reward)
            if learning_context:
                prompt = prompt + learning_context

        raw = _call_llm(client, prompt)
        _log(f"    LLM raw: {raw[:120]}...")

        action = _parse_action(raw)
        if action is None:
            _log("    WARNING: could not parse LLM response — using fallback")
            action = {
                "severity": "P2",
                "team": "backend",
                "escalate": False,
                "confidence": 0.3,
                "reasoning": "Could not parse model response; defaulting to P2/backend.",
            }

        result = _step(action)
        obs = result["observation"]
        episode_reward = result["reward"]
        done = result["done"]
        prev_reward = episode_reward  # save for next step's learning context

        _log(f"    score={episode_reward['score']:.3f} done={done}")
        if result.get("info", {}).get("cascade_triggered"):
            _log(f"    CASCADE TRIGGERED — penalty applied")

    return {"task_id": task_id, "reward": episode_reward}


def main() -> None:
    global MODEL_NAME
    if GEMINI_API_KEY:
        client = OpenAI(
            api_key=GEMINI_API_KEY,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        if MODEL_NAME == "gpt-4o-mini":
            MODEL_NAME = "gemini-2.5-flash"
    else:
        client = OpenAI(api_key=OPENAI_API_KEY)

    print("[START]", flush=True)

    all_results = []
    for task_name, task_ids in zip(TASK_NAMES, TASK_IDS):
        _log(f"\n=== Task group: {task_name} ===")
        group_scores = []
        for task_id in task_ids:
            result = run_episode(client, task_id)
            score = result["reward"]["score"]
            group_scores.append(score)

            print(
                f"[STEP] task_id={task_id} score={score:.3f} "
                f"severity={result['reward'].get('severity_score', 0):.2f} "
                f"routing={result['reward'].get('routing_score', 0):.2f} "
                f"escalation={result['reward'].get('escalation_score', 0):.2f} "
                f"cascade={result['reward'].get('cascade_penalty', 0):.2f} "
                f"fp_bonus={result['reward'].get('false_positive_bonus', 0):.2f} "
                f"trend={result['reward'].get('trend_bonus', 0):.2f}",
                flush=True,
            )
            all_results.append(result)

        avg = sum(group_scores) / len(group_scores)
        _log(f"  group avg: {avg:.3f}")

    overall = sum(r["reward"]["score"] for r in all_results) / len(all_results)
    print(f"[END] overall_avg={overall:.4f} episodes={len(all_results)}", flush=True)


if __name__ == "__main__":
    main()
