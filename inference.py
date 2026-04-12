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
import time
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


def _request_with_retry(method: str, url: str, max_retries: int = 5, **kwargs) -> requests.Response:
    """POST/GET with exponential backoff for transient failures."""
    delay = 1.0
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            resp = requests.request(method, url, timeout=30, **kwargs)
            if resp.status_code < 500:
                resp.raise_for_status()
                return resp
            # 5xx — server-side transient error, retry
            _log(f"    Server error {resp.status_code} on {url} (attempt {attempt + 1}/{max_retries}), retrying in {delay:.1f}s…")
            _log(f"    Response body: {resp.text[:200]}")
        except requests.exceptions.ConnectionError as exc:
            _log(f"    Connection error on {url} (attempt {attempt + 1}/{max_retries}), retrying in {delay:.1f}s…")
            last_exc = exc
        except requests.exceptions.HTTPError:
            raise  # 4xx are not retryable
        time.sleep(delay)
        delay = min(delay * 2, 30)
    raise RuntimeError(f"Failed after {max_retries} attempts: {url}") from last_exc


def _wait_for_server(timeout: int = 60) -> None:
    """Block until the API server responds or timeout (seconds) elapses."""
    deadline = time.time() + timeout
    delay = 1.0
    while time.time() < deadline:
        try:
            resp = requests.get(f"{API_BASE_URL}/health", timeout=5)
            if resp.status_code == 200:
                _log(f"  API server ready (status {resp.status_code})")
                return
        except requests.exceptions.RequestException:
            pass
        _log(f"  Waiting for API server… (retrying in {delay:.0f}s)")
        time.sleep(delay)
        delay = min(delay * 2, 10)
    raise RuntimeError(f"API server at {API_BASE_URL} not reachable after {timeout}s")


def _reset(task_id: str) -> dict:
    resp = _request_with_retry("POST", f"{API_BASE_URL}/reset", json={"task_id": task_id})
    return resp.json()


def _step(action: dict) -> dict:
    resp = _request_with_retry("POST", f"{API_BASE_URL}/step", json=action)
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
            try:
                formatted = "  ".join(f"{float(v):7.1f}" for v in values)
            except (TypeError, ValueError):
                formatted = "  ".join(f"{str(v):>7}" for v in values)
            # Add trend indicator
            try:
                numeric = [float(v) for v in values]
                if len(numeric) >= 2:
                    diff = numeric[-1] - numeric[0]
                    trend = " ▲" if diff > 5 else (" ▼" if diff < -5 else " ─")
                else:
                    trend = ""
            except (TypeError, ValueError):
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
            f"{d.get('service','?')} {d.get('version','?')} by {d.get('author','?')} at {d.get('timestamp','?')}"
            for d in deployments
        )
        if deployments
        else "none"
    )
    feedback = obs.get("feedback", "")
    new_alert = obs.get("new_alert", "")

    lines = [
        f"=== INCIDENT {obs.get('incident_id', 'UNKNOWN')} (attempt {obs.get('step_number', '?')}) ===",
        f"Alert type   : {obs.get('alert_type', 'unknown')}",
        f"Service      : {obs.get('service_name', 'unknown')}",
        f"Error        : {obs.get('error_message', 'unknown')}",
        f"Time         : {obs.get('time_of_day', 'unknown')}",
        f"Related alerts: {alerts}",
        f"Dependencies : {deps}",
        f"Recent deploys: {deploy_str}",
        f"\nMetrics (last 5 minutes — analyze trends):\n{metrics_str}",
        f"\nLogs:\n{obs.get('logs_snippet', '')}",
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


MAX_STEPS_PER_EPISODE = 10  # safety cap; environment typically uses 2


def run_episode(client: OpenAI, task_id: str) -> dict:
    """Run one episode (up to MAX_STEPS_PER_EPISODE steps) for a single task_id."""
    _log(f"  [episode] task_id={task_id}")
    obs = _reset(task_id)
    episode_reward: dict = {"score": 0.0}
    done = False
    prev_reward = None  # track step-1 reward for learning signal injection
    steps = 0

    while not done and steps < MAX_STEPS_PER_EPISODE:
        steps += 1
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
        obs = result.get("observation") or {}
        episode_reward = result.get("reward") or {"score": 0.0}
        done = result.get("done", True)
        prev_reward = episode_reward  # save for next step's learning context

        _log(f"    score={episode_reward.get('score', 0.0):.3f} done={done}")
        if result.get("info", {}).get("cascade_triggered"):
            _log(f"    CASCADE TRIGGERED — penalty applied")

    return {"task_id": task_id, "reward": episode_reward}


def main() -> None:
    global MODEL_NAME
    try:
        if GEMINI_API_KEY:
            client = OpenAI(
                api_key=GEMINI_API_KEY,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            )
            if MODEL_NAME == "gpt-4o-mini":
                MODEL_NAME = "gemini-2.5-flash"
        else:
            client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as exc:
        _log(f"ERROR: failed to initialise LLM client: {exc}")
        print("[END] overall_avg=0.0000 episodes=0", flush=True)
        sys.exit(1)

    _wait_for_server()
    print("[START]", flush=True)

    all_results = []
    try:
        for task_name, task_ids in zip(TASK_NAMES, TASK_IDS):
            _log(f"\n=== Task group: {task_name} ===")
            group_scores = []
            for task_id in task_ids:
                try:
                    result = run_episode(client, task_id)
                except Exception as exc:
                    _log(f"    ERROR in task {task_id}: {exc}")
                    result = {
                        "task_id": task_id,
                        "reward": {
                            "score": 0.0,
                            "severity_score": 0.0,
                            "routing_score": 0.0,
                            "escalation_score": 0.0,
                            "cascade_penalty": 0.0,
                            "false_positive_bonus": 0.0,
                            "trend_bonus": 0.0,
                        },
                    }
                score = result["reward"].get("score", 0.0)
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

            avg = sum(group_scores) / len(group_scores) if group_scores else 0.0
            _log(f"  group avg: {avg:.3f}")
    finally:
        episodes = len(all_results)
        overall = sum(r["reward"].get("score", 0.0) for r in all_results) / episodes if episodes else 0.0
        print(f"[END] overall_avg={overall:.4f} episodes={episodes}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        _log(f"FATAL: {exc}")
        print("[END] overall_avg=0.0000 episodes=0", flush=True)
        sys.exit(1)
