import os
import uuid
from flask import Flask, request, jsonify
from pydantic import ValidationError
from models import TriageAction
from environment import IncidentTriageEnv
from analytics import AgentAnalytics
from consequences import get_consequences, all_consequences

app = Flask(__name__)

# BUG 2 FIX: Per-session environments instead of global singleton
_sessions: dict[str, IncidentTriageEnv] = {}
_default_session = "default"


def _get_env(session_id: str | None = None) -> IncidentTriageEnv:
    sid = session_id or _default_session
    if sid not in _sessions:
        _sessions[sid] = IncidentTriageEnv()
    return _sessions[sid]


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/reset")
def reset():
    body = request.get_json(silent=True) or {}
    task_id = body.get("task_id")
    session_id = body.get("session_id")

    # BUG 10 FIX: Handle bad seed gracefully
    try:
        seed = int(body.get("seed", 42))
    except (ValueError, TypeError):
        return jsonify({"error": "seed must be an integer"}), 400

    env = _get_env(session_id)
    try:
        obs = env.reset(task_id=task_id, seed=seed)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(obs.model_dump())


@app.post("/step")
def step():
    body = request.get_json(silent=True) or {}
    session_id = body.pop("session_id", None)

    try:
        action = TriageAction(**body)
    except (ValidationError, TypeError) as exc:
        return jsonify({"error": str(exc)}), 422

    env = _get_env(session_id)
    try:
        obs, reward, done, info = env.step(action)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 400

    # BUG 1 FIX: Only expose ground truth AFTER episode is done
    safe_info = {
        "attempt": info["attempt"],
        "cascade_triggered": info["cascade_triggered"],
        "cascade_penalty_total": info["cascade_penalty_total"],
    }
    if done:
        safe_info["expected_severity"] = info["expected_severity"]
        safe_info["expected_team"] = info["expected_team"]
        safe_info["expected_escalate"] = info["expected_escalate"]

    # Only expose detailed breakdown AFTER episode is done to prevent answer leakage
    if done:
        reward_data = reward.model_dump()
    else:
        # During episode: only score + learning signals (not answer, just learning)
        reward_data = {
            "score": reward.score,
            "learning_signals": [
                {
                    "dimension": sig.dimension,
                    "correct": sig.correct,
                    "reason": sig.reason,
                    "improvement_hint": sig.improvement_hint
                }
                for sig in reward.learning_signals
            ],
            "key_insights": reward.key_insights
        }

    return jsonify({
        "observation": obs.model_dump(),
        "reward": reward_data,
        "done": done,
        "info": safe_info,
    })


@app.post("/analyze")
def analyze():
    """
    Analyze agent performance across all scenarios.

    Body:
    {
        "agent_name": "gpt-4",
        "results": [
            {"task_id": "easy-1", "reward": {"score": 0.75, ...}},
            ...
        ]
    }
    """
    body = request.get_json(silent=True) or {}
    agent_name = body.get("agent_name", "unknown")
    results = body.get("results", [])

    if not results:
        return jsonify({"error": "No results provided"}), 400

    try:
        analytics = AgentAnalytics(agent_name, results)
        analysis = analytics.analyze()
        return jsonify(analysis)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.get("/consequences/<task_id>")
def get_scenario_consequences(task_id: str):
    """
    Get realistic incident consequence timelines for a scenario.
    Shows the impact of different triage decisions.

    Returns timelines for correct and incorrect decisions.
    """
    consequences = get_consequences(task_id)
    if not consequences:
        return jsonify({"error": f"No consequences data for {task_id}"}), 404

    return jsonify(consequences)


@app.get("/consequences")
def list_all_consequences():
    """List all available consequence timelines."""
    all_cons = all_consequences()
    return jsonify({
        "total_scenarios": len(all_cons),
        "scenarios": list(all_cons.keys()),
        "info": "Use GET /consequences/<task_id> to view detailed timelines"
    })


@app.get("/state")
@app.post("/state")
def state():
    """Return current environment state (OpenEnv spec required endpoint)."""
    body = request.get_json(silent=True) or {}
    session_id = body.get("session_id") if request.method == "POST" else request.args.get("session_id")
    env = _get_env(session_id)
    return jsonify(env.state())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
