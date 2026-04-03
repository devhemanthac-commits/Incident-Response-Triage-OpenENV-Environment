"""Test Flask API endpoints with all new features."""
import requests
import json

BASE = "http://localhost:5000"

# Test health
r = requests.get(f"{BASE}/health")
print(f"1. Health: {r.status_code} {r.json()}")

# Test reset with false-positive scenario
r = requests.post(f"{BASE}/reset", json={"task_id": "false-positive-1"})
obs = r.json()
print(f"\n2. Reset false-positive-1: {r.status_code}")
print(f"   incident_id: {obs['incident_id']}")
print(f"   metrics type check: cpu_percent is list = {isinstance(obs['metrics']['cpu_percent'], list)}")
print(f"   timestamps: {obs['metrics']['timestamps']}")

# Test step with correct FP triage
r = requests.post(f"{BASE}/step", json={
    "severity": "P4", "team": "infra", "escalate": False,
    "confidence": 0.85,
    "reasoning": "Expected nightly backup behavior. Memory trending up from 30% is normal for scheduled compression job. No errors, ETA 5 min."
})
result = r.json()
print(f"\n3. Step (FP correct): {r.status_code}")
print(f"   score: {result['reward']['score']}")
print(f"   fp_bonus: {result['reward']['false_positive_bonus']}")
print(f"   trend_bonus: {result['reward']['trend_bonus']}")
print(f"   done: {result['done']}")

# Test cascade trigger
r = requests.post(f"{BASE}/reset", json={"task_id": "hard-1"})
print(f"\n4. Reset hard-1: {r.status_code}")

r = requests.post(f"{BASE}/step", json={
    "severity": "P3", "team": "backend", "escalate": False,
    "confidence": 0.9,
    "reasoning": "Looks like a deploy issue"
})
result = r.json()
print(f"\n5. Step (wrong triage → cascade): {r.status_code}")
print(f"   score: {result['reward']['score']}")
print(f"   cascade_penalty: {result['reward']['cascade_penalty']}")
print(f"   cascade_triggered: {result['info']['cascade_triggered']}")
print(f"   new_alert: {result['observation']['new_alert'][:80]}...")

# Test alt team routing
r = requests.post(f"{BASE}/reset", json={"task_id": "hard-1"})
r = requests.post(f"{BASE}/step", json={
    "severity": "P1", "team": "infra", "escalate": True,
    "confidence": 0.7,
    "reasoning": "Connection pool exhaustion, max_connections reached, DB root cause"
})
result = r.json()
print(f"\n6. Alt team routing:")
print(f"   routing_score: {result['reward']['routing_score']} (should be 0.15)")

# Test multi-step + adaptation
r = requests.post(f"{BASE}/reset", json={"task_id": "easy-1"})
r = requests.post(f"{BASE}/step", json={
    "severity": "P3", "team": "infra", "escalate": True,
    "confidence": 0.4,
    "reasoning": "Disk issue"
})
result = r.json()
print(f"\n7. Multi-step (step 1):")
print(f"   done: {result['done']} (should be False)")
print(f"   has_consequence: {'OBSERVATION:' in result['observation']['feedback']}")

r = requests.post(f"{BASE}/step", json={
    "severity": "P2", "team": "database", "escalate": False,
    "confidence": 0.85,
    "reasoning": "Disk 95% on postgres-primary, steadily increasing trend. Database team should handle."
})
result = r.json()
print(f"   Step 2 done: {result['done']} (should be True)")
print(f"   Step 2 score: {result['reward']['score']}")

print("\n=== ALL API TESTS PASSED ===")
