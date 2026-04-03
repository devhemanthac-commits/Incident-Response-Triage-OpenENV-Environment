"""
Mock deterministic agent for end-to-end testing.
Tests all 18 scenarios with hardcoded decision logic (no LLM).
Suitable for reproducibility verification.
"""

import json
import requests

API_BASE_URL = "http://localhost:5000"


def reset(task_id: str, seed: int = 42) -> dict:
    resp = requests.post(
        f"{API_BASE_URL}/reset",
        json={"task_id": task_id, "seed": seed},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def step(action: dict) -> dict:
    resp = requests.post(
        f"{API_BASE_URL}/step",
        json=action,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def mock_triage(obs: dict) -> dict:
    """Hardcoded decision logic based on alert type and metrics."""
    alert = obs.get("alert_type", "").lower()
    service = obs.get("service_name", "").lower()
    error_msg = obs.get("error_message", "").lower()
    metrics = obs.get("metrics", {})
    task_id = obs.get("task_id", "")

    # Default
    severity = "P3"
    team = "backend"
    escalate = False
    confidence = 0.7
    reasoning = ""

    # ─── EASY scenarios ───────────────────────────────────────────────────────
    if task_id == "easy-1":  # disk_full
        severity = "P2"
        team = "database"
        escalate = False
        confidence = 0.95
        reasoning = "Disk at 95%, trending from 88%, database write operations at risk"

    elif task_id == "easy-2":  # 5xx_errors 100%
        severity = "P0"
        team = "backend"
        escalate = True
        confidence = 0.98
        reasoning = "Complete outage, 100% error rate, circuit breaker open, revenue impact"

    elif task_id == "easy-3":  # ssl_cert_expiry
        severity = "P1"
        team = "infra"
        escalate = True
        confidence = 0.95
        reasoning = "SSL certificate expired, CERT_DATE_INVALID, TLS handshake failures"

    elif task_id == "easy-4":  # single pod cpu spike
        severity = "P3"
        team = "backend"
        escalate = False
        confidence = 0.85
        reasoning = "Single pod CPU 99%, other pods nominal, Kubernetes auto-restarting"

    elif task_id == "easy-5":  # brute_force
        severity = "P1"
        team = "security"
        escalate = True
        confidence = 0.92
        reasoning = "50,000 failed login attempts from 200 IPs, credential stuffing pattern"

    # ─── MEDIUM scenarios ─────────────────────────────────────────────────────
    elif task_id == "medium-1":  # 2% error_rate post-deploy
        severity = "P2"
        team = "backend"
        escalate = False
        confidence = 0.80
        reasoning = "NullPointerException post-deploy, 2% error rate, majority requests succeeding"

    elif task_id == "medium-2":  # memory leak gradual
        severity = "P3"
        team = "backend"
        escalate = False
        confidence = 0.75
        reasoning = "Memory trending upward +2%/hour, GC pressure increasing"

    elif task_id == "medium-3":  # slow_queries during migration
        severity = "P2"
        team = "database"
        escalate = False
        confidence = 0.85
        reasoning = "Data migration causing table lock, expected slow queries during migration"

    elif task_id == "medium-4":  # packet_loss
        severity = "P2"
        team = "network"
        escalate = False
        confidence = 0.80
        reasoning = "3% packet loss on east-west, intermittent timeouts, service mesh issue"

    elif task_id == "medium-5":  # stale_cache
        severity = "P3"
        team = "frontend"
        escalate = False
        confidence = 0.75
        reasoning = "CDN serving stale assets post-deploy, cache invalidation issue"

    # ─── HARD scenarios ──────────────────────────────────────────────────────
    elif task_id == "hard-1":  # DB pool exhaustion
        severity = "P1"
        team = "database"
        escalate = True
        confidence = 0.88
        reasoning = "Connection pool exhaustion, max_connections reached, too many clients error"

    elif task_id == "hard-2":  # DNS failure
        severity = "P0"
        team = "network"
        escalate = True
        confidence = 0.90
        reasoning = "DNS resolution failures, ENOTFOUND errors across all services, cascading effect"

    elif task_id == "hard-3":  # crypto-mining
        severity = "P0"
        team = "security"
        escalate = True
        confidence = 0.92
        reasoning = "Fleet-wide CPU spike at 3 AM, unknown process, crontab modified, C2 traffic"

    elif task_id == "hard-4":  # shared lib memory leak
        severity = "P1"
        team = "infra"
        escalate = True
        confidence = 0.88
        reasoning = "Rolling OOM restarts across 6 services, shared library libcommon v4.2.1"

    elif task_id == "hard-5":  # upstream Stripe outage
        severity = "P2"
        team = "backend"
        escalate = False
        confidence = 0.80
        reasoning = "Internal processing normal, latency spike from stripe.com, upstream outage"

    # ─── FALSE POSITIVE scenarios ─────────────────────────────────────────────
    elif task_id == "false-positive-1":  # nightly backup
        severity = "P4"
        team = "infra"
        escalate = False
        confidence = 0.88
        reasoning = "Nightly backup using 89% heap, expected behavior, finishes in 5 minutes"

    elif task_id == "false-positive-2":  # staging load test
        severity = "P4"
        team = "backend"
        escalate = False
        confidence = 0.85
        reasoning = "Staging load test at 90% CPU, non-production, scheduled activity"

    elif task_id == "false-positive-3":  # canary deploy
        severity = "P3"
        team = "backend"
        escalate = False
        confidence = 0.80
        reasoning = "Canary deploy 5% error rate on 1% traffic, auto-rollback ready"

    return {
        "severity": severity,
        "team": team,
        "escalate": escalate,
        "confidence": confidence,
        "reasoning": reasoning,
    }


def run_scenario(task_id: str, seed: int = 42) -> dict:
    obs = reset(task_id, seed)
    action = mock_triage(obs)
    result = step(action)
    reward = result["reward"]

    return {
        "task_id": task_id,
        "incident_id": obs["incident_id"],
        "score": reward["score"],
        "severity_score": reward["severity_score"],
        "routing_score": reward["routing_score"],
        "escalation_score": reward["escalation_score"],
        "reasoning_score": reward["reasoning_score"],
        "calibration_score": reward["calibration_score"],
        "trend_bonus": reward["trend_bonus"],
        "false_positive_bonus": reward["false_positive_bonus"],
        "adaptation_bonus": reward["adaptation_bonus"],
        "cascade_penalty": reward["cascade_penalty"],
        "done": result["done"],
        "feedback": reward["feedback"][:60] + "..." if len(reward["feedback"]) > 60 else reward["feedback"],
    }


def main() -> None:
    all_tasks = [
        ("easy-1", "easy-2", "easy-3", "easy-4", "easy-5"),
        ("medium-1", "medium-2", "medium-3", "medium-4", "medium-5"),
        ("hard-1", "hard-2", "hard-3", "hard-4", "hard-5"),
        ("false-positive-1", "false-positive-2", "false-positive-3"),
    ]
    group_names = ["easy", "medium", "hard", "false-positive"]

    results = []
    group_scores = {name: [] for name in group_names}

    print("=" * 100)
    print("MOCK AGENT TEST — 18 SCENARIOS")
    print("=" * 100)

    for group_name, task_ids in zip(group_names, all_tasks):
        print(f"\n[{group_name.upper()}]")
        for task_id in task_ids:
            result = run_scenario(task_id, seed=42)
            results.append(result)
            group_scores[group_name].append(result["score"])

            status = "PASS" if result["score"] >= 0.95 else "PARTIAL" if result["score"] >= 0.70 else "FAIL"
            print(
                f"  {task_id:20} {result['incident_id']:10} "
                f"score={result['score']:.3f} {status:8} "
                f"sev={result['severity_score']:.2f} "
                f"route={result['routing_score']:.2f} "
                f"esc={result['escalation_score']:.2f} "
                f"trend={result['trend_bonus']:.2f} "
                f"fp={result['false_positive_bonus']:.2f}"
            )

        avg = sum(group_scores[group_name]) / len(group_scores[group_name])
        print(f"  GROUP AVG: {avg:.3f}")

    overall_avg = sum(r["score"] for r in results) / len(results)
    print("\n" + "=" * 100)
    print(f"OVERALL AVG: {overall_avg:.4f} ({len(results)} scenarios)")
    print("=" * 100)

    # Save results
    with open("test_agent_results.json", "w") as f:
        json.dump({"seed": 42, "results": results, "overall_avg": overall_avg}, f, indent=2)
    print(f"Results saved to test_agent_results.json")

    return overall_avg


if __name__ == "__main__":
    main()
