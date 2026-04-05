"""Quick verification test for all features."""
from environment import IncidentTriageEnv
from models import TriageAction

env = IncidentTriageEnv()

# Test 1: All 18 scenarios reset
print("=== Test 1: Reset all 18 scenarios ===")
for prefix in ["easy", "medium", "hard"]:
    for i in range(1, 6):
        tid = f"{prefix}-{i}"
        obs = env.reset(task_id=tid)
        print(f"  OK {tid}: {obs.incident_id}")

for i in range(1, 4):
    tid = f"false-positive-{i}"
    obs = env.reset(task_id=tid)
    print(f"  OK {tid}: {obs.incident_id}")

# Test 2: Time-series metrics are lists
print("\n=== Test 2: Time-series metrics ===")
obs = env.reset(task_id="easy-1")
for k, v in obs.metrics.items():
    if k != "timestamps":
        assert isinstance(v, list), f"{k} should be list, got {type(v)}"
        assert len(v) == 5, f"{k} should have 5 values, got {len(v)}"
assert "timestamps" in obs.metrics
print("  OK: All metrics are 5-point time series")

# Test 3: Cascading failure trigger
print("\n=== Test 3: Cascading failures ===")
env.reset(task_id="hard-1")
action = TriageAction(
    severity="P3", team="backend", escalate=False, confidence=0.9,
    reasoning="Looks like a deploy issue, rolling back"
)
obs, reward, done, info = env.step(action)
assert info["cascade_triggered"] == True, "Cascade should trigger on wrong triage"
assert reward.cascade_penalty < 0, f"Should have penalty, got {reward.cascade_penalty}"
print(f"  OK: Cascade triggered, penalty={reward.cascade_penalty}")
print(f"     Feedback: {obs.feedback[:120]}...")

# Test 4: No cascade on correct triage
print("\n=== Test 4: No cascade on correct triage ===")
env.reset(task_id="hard-1")
action = TriageAction(
    severity="P1", team="database", escalate=True, confidence=0.85,
    reasoning="DB connection pool exhaustion causing cascading failures, max_connections reached, too many clients"
)
obs, reward, done, info = env.step(action)
assert info["cascade_triggered"] == False, "No cascade on correct answer"
assert reward.cascade_penalty == 0.0
print(f"  OK: No cascade, score={reward.score}")

# Test 5: False positive bonus
print("\n=== Test 5: False positive detection ===")
env.reset(task_id="false-positive-1")
action = TriageAction(
    severity="P4", team="infra", escalate=False, confidence=0.85,
    reasoning="Expected nightly backup behavior, memory usage is normal for this scheduled cron job and will finish shortly"
)
obs, reward, done, info = env.step(action)
assert reward.false_positive_bonus > 0, f"Should get FP bonus, got {reward.false_positive_bonus}"
print(f"  OK: FP bonus={reward.false_positive_bonus}, total score={reward.score}")

# Test 6: Expert team routing - alt team partial credit
print("\n=== Test 6: Expert team routing ===")
env.reset(task_id="hard-1")  # optimal=database, alt=infra
action = TriageAction(
    severity="P1", team="infra", escalate=True, confidence=0.7,
    reasoning="DB connection pool exhaustion causing cascading failures, max_connections reached"
)
obs, reward, done, info = env.step(action)
assert abs(reward.routing_score - 0.20) < 0.001, f"Alt team should get 0.20, got {reward.routing_score}"
print(f"  OK: Alt team routing_score={reward.routing_score}")

# Test 7: Trend bonus
print("\n=== Test 7: Trend detection bonus ===")
env.reset(task_id="medium-2")
action = TriageAction(
    severity="P3", team="backend", escalate=False, confidence=0.8,
    reasoning="Memory trending upward at 2%/hour, gradual increase from 70% to 78%. GC pressure increasing suggests a memory leak."
)
obs, reward, done, info = env.step(action)
assert reward.trend_bonus > 0, f"Should get trend bonus, got {reward.trend_bonus}"
print(f"  OK: Trend bonus={reward.trend_bonus}, total={reward.score}")

# Test 8: Multi-step (max 2 attempts)
print("\n=== Test 8: Multi-step episodes ===")
env.reset(task_id="easy-1")
action1 = TriageAction(
    severity="P3", team="infra", escalate=True, confidence=0.5,
    reasoning="Disk issue, not sure about severity"
)
obs1, reward1, done1, info1 = env.step(action1)
assert done1 == False, "Should not be done after 1st attempt"
assert "OBSERVATION:" in obs1.feedback, "Should have consequence observation"
print(f"  Step 1: score={reward1.score}, done={done1}")

action2 = TriageAction(
    severity="P2", team="database", escalate=False, confidence=0.85,
    reasoning="Disk 95% on postgres-primary, disk_percent trending upward. Database team should handle."
)
obs2, reward2, done2, info2 = env.step(action2)
assert done2 == True, "Should be done after 2nd attempt"
print(f"  Step 2: score={reward2.score}, done={done2}")
print(f"  Feedback: {reward2.feedback[:100]}...")

# Test 9: Reproducibility
print("\n=== Test 9: Reproducibility ===")
scores = []
for _ in range(3):
    env2 = IncidentTriageEnv()
    env2.reset(task_id="medium-3", seed=42)
    a = TriageAction(
        severity="P2", team="database", escalate=False, confidence=0.8,
        reasoning="Data migration causing slow queries, table lock on orders, connection pool near capacity"
    )
    _, r, _, _ = env2.step(a)
    scores.append(r.score)
assert len(set(scores)) == 1, f"Scores differ: {scores}"
print(f"  OK: Reproducible score={scores[0]} across 3 runs")

# Test 10: new_alert field in observation
print("\n=== Test 10: new_alert field ===")
env.reset(task_id="hard-3")
action = TriageAction(
    severity="P3", team="backend", escalate=False, confidence=0.7,
    reasoning="Just some CPU spike"
)
obs, reward, done, info = env.step(action)
assert obs.new_alert != "", f"Should have new_alert after cascade"
print(f"  OK: new_alert='{obs.new_alert[:80]}...'")

print("\n=== ALL TESTS PASSED ===")
