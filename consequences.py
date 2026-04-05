"""
Realistic incident consequence timelines - shows impact of different triage decisions.
This demonstrates why good triage matters in real-world SRE scenarios.
"""

CONSEQUENCE_TIMELINES = {
    "easy-1": {
        "description": "Disk full on primary database",
        "correct_decision": {
            "action": "P2 severity | database team | no escalation",
            "timeline": [
                {"time": "T+0min", "event": "Alert fires"},
                {"time": "T+1min", "event": "Database team alerted"},
                {"time": "T+3min", "event": "DBA identifies disk issue, checks WAL segments"},
                {"time": "T+5min", "event": "Runs pg_archivecleanup, frees 40GB"},
                {"time": "T+8min", "event": "Disk back to 55%, incident resolved"},
            ],
            "cost": "$0 (minimal impact, quick resolution)",
            "lessons": ["Analyze TRENDS not just thresholds", "Disk trends + DB symptoms = database team domain"],
        },
        "wrong_severity": {
            "action": "P1 severity (over-escalated) | database team | escalation",
            "timeline": [
                {"time": "T+0min", "event": "Alert fires"},
                {"time": "T+1min", "event": "Database team + oncall paged (unnecessary escalation)"},
                {"time": "T+5min", "event": "Oncall approves emergency access"},
                {"time": "T+8min", "event": "DBA resolves (same as correct, but with overhead)"},
            ],
            "cost": "$200 (oncall overhead, false alarm fatigue)",
            "lessons": ["Not everything is a P1", "Unnecessary escalation costs SRE team sleep"],
        },
        "wrong_team": {
            "action": "P2 severity | infra team (wrong) | no escalation",
            "timeline": [
                {"time": "T+0min", "event": "Alert fires"},
                {"time": "T+1min", "event": "Infra team alerted (WRONG - not their domain)"},
                {"time": "T+5min", "event": "Infra team checks servers, OS disk, network"},
                {"time": "T+10min", "event": "After 9 minutes, escalates to database team"},
                {"time": "T+13min", "event": "DBA resolves (5 min delay = escalating impact)"},
            ],
            "cost": "$1,400 (wasted response time, customer impact)",
            "lessons": ["Wrong team = exponential delay", "Root cause = database symptoms → database team"],
        },
    },
    "medium-1": {
        "description": "Memory leak causing OOM in payment service",
        "correct_decision": {
            "action": "P1 severity | backend team | escalation",
            "timeline": [
                {"time": "T+0min", "event": "Memory breach alert (memory_percent trending 70->85%)"},
                {"time": "T+2min", "event": "Backend team alerted + oncall escalation approved"},
                {"time": "T+5min", "event": "Team rolls back recent deployment"},
                {"time": "T+8min", "event": "Memory normalizes, incident resolved"},
                {"time": "T+15min", "event": "Root cause: NullPointerException in release"},
            ],
            "cost": "$0 (fast mitigation, minimal customer impact)",
            "lessons": ["Trending metrics reveal patterns", "Escalation justified for P1 + ongoing growth"],
        },
        "wrong_severity": {
            "action": "P2 severity (under-escalated)",
            "timeline": [
                {"time": "T+0min", "event": "Memory breach detected"},
                {"time": "T+3min", "event": "Backend team alerted (no escalation)"},
                {"time": "T+8min", "event": "Memory hits 95%, service becomes sluggish"},
                {"time": "T+10min", "event": "OOM killer kicks in, pod crashes"},
                {"time": "T+12min", "event": "Kubernetes auto-restarts, brief outage"},
                {"time": "T+20min", "event": "Memory leaks again, repeat cycle (frivolous restarts)"},
            ],
            "cost": "$45,000 (customer outage, auto-restarts, ops fatigue)",
            "lessons": ["Growing trends = escalation needed", "Waiting 'until P1' is already too late"],
        },
    },
    "hard-1": {
        "description": "Database connection pool exhaustion",
        "correct_decision": {
            "action": "P1 severity | database team | escalation",
            "timeline": [
                {"time": "T+0min", "event": "Connection pool breach alert"},
                {"time": "T+1min", "event": "Database team + oncall paged"},
                {"time": "T+3min", "event": "DBA increases pool size from 100 to 200"},
                {"time": "T+5min", "event": "New connections served, error rate drops"},
                {"time": "T+8min", "event": "Root cause investigated: N+1 query in backend"},
            ],
            "cost": "$0 (quick mitigation, expert knowledge applied)",
            "lessons": ["Connection pool exhaustion = database team domain", "Escalation justified for infrastructure tier"],
        },
        "wrong_team": {
            "action": "P1 severity | backend team (wrong)",
            "timeline": [
                {"time": "T+0min", "event": "Connection pool alert fires"},
                {"time": "T+1min", "event": "Backend team starts debugging application"},
                {"time": "T+8min", "event": "Backend team suspects database, escalates"},
                {"time": "T+10min", "event": "Database team takes over (9 min wasted)"},
                {"time": "T+15min", "event": "DBA increases pool (could have been done at T+3)"},
            ],
            "cost": "$18,000 (12min outage, 10K+ users affected, data loss risk)",
            "lessons": ["Wrong routing = exponential cascade", "Connection pool = infrastructure domain"],
        },
    },
    "false-positive-1": {
        "description": "High disk usage during scheduled backup",
        "correct_decision": {
            "action": "P4 severity (low priority) | infra team | no escalation",
            "timeline": [
                {"time": "T+0min", "event": "Disk at 85% detected"},
                {"time": "T+1min", "event": "Infra team acknowledges (routine backup)"},
                {"time": "T+30min", "event": "Backup completes, disk returns to 45%"},
                {"time": "T+31min", "event": "Alert auto-resolves"},
            ],
            "cost": "$0 (correct categorization, no unnecessary alerts)",
            "lessons": ["Know your baselines", "Expected high-load periods aren't emergencies"],
        },
        "wrong_severity": {
            "action": "P1 severity | oncall paged | escalation",
            "timeline": [
                {"time": "T+0min", "event": "Disk at 85% triggers P1 alert"},
                {"time": "T+1min", "event": "Oncall paged immediately (WRONG)"},
                {"time": "T+5min", "event": "Oncall investigates, sees it's the backup"},
                {"time": "T+6min", "event": "False alarm, but oncall is now awake at 3am"},
            ],
            "cost": "$500 (oncall sleep disruption, context switching)",
            "lessons": ["False positives = SRE burnout", "Understanding expected behavior saves alerts"],
        },
    },
}


def get_consequences(task_id: str) -> dict | None:
    """Get consequence timeline for a scenario."""
    return CONSEQUENCE_TIMELINES.get(task_id)


def all_consequences() -> dict:
    """Get all consequence timelines."""
    return CONSEQUENCE_TIMELINES
