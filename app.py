import os
import uuid
from flask import Flask, request, jsonify
from pydantic import ValidationError
from models import TriageAction
from environment import IncidentTriageEnv

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

    return jsonify({
        "observation": obs.model_dump(),
        "reward": reward.model_dump(),
        "done": done,
        "info": safe_info,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
