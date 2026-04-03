"""
18 incident scenarios: 5 easy, 5 medium, 5 hard, 3 false-positive.
Each dict contains observation fields + ground truth.
Ground truth fields are NEVER exposed to the agent via TriageObservation.

Features:
  - Time-series metrics: each metric is a 5-point list (last 5 minutes)
  - Cascade triggers: hard scenarios can cascade on mis-triage
  - Team routing: optimal + alternative teams with penalties
  - Consequence observations: step-2 context after initial triage
  - False positives: "boy who cried wolf" scenarios (INC-0016 to INC-0018)
"""

SCENARIOS: list[dict] = [
    # ─── EASY (1-5) ──────────────────────────────────────────────────────────
    {
        "task_id": "easy-1",
        "incident_id": "INC-0001",
        "alert_type": "disk_full",
        "service_name": "postgres-primary",
        "error_message": "CRITICAL: Disk usage at 95% on /dev/sda1 — write operations may fail",
        "metrics": {
            "cpu_percent": [20.0, 21.0, 22.0, 22.0, 22.0],
            "memory_percent": [58.0, 59.0, 60.0, 61.0, 61.0],
            "error_rate": [0.0, 0.0, 0.0, 0.0, 0.0],
            "latency_p99_ms": [40.0, 42.0, 43.0, 44.0, 45.0],
            "disk_percent": [88.0, 90.0, 92.0, 94.0, 95.0],
            "connections_active": [115.0, 117.0, 118.0, 119.0, 120.0],
            "timestamps": ["T-4min", "T-3min", "T-2min", "T-1min", "T-now"],
        },
        "logs_snippet": (
            "2024-01-15 14:22:01 WARN  pg: checkpoint completing, write ahead log filling\n"
            "2024-01-15 14:22:05 WARN  pg: disk usage 94%\n"
            "2024-01-15 14:22:10 ERROR pg: disk usage 95% — approaching limit\n"
            "2024-01-15 14:22:15 WARN  pg: autovacuum delayed due to disk pressure\n"
            "2024-01-15 14:22:20 ERROR pg: could not write to file: no space left on device"
        ),
        "time_of_day": "2024-01-15T14:22:20Z",
        "related_alerts": ["WAL archiving delayed", "Autovacuum disabled"],
        "service_dependencies": ["payment-api", "order-service", "user-auth"],
        "recent_deployments": [],
        "expected_severity": "P2",
        "expected_team": "database",
        "expected_escalate": False,
        "key_indicators": ["disk_percent", "postgres-primary", "no space left on device"],
        "team_routing": {

            "alt_teams": ["infra"],
            "alt_penalty": 0.10,
        },
        "consequence_observation": "DBA team acknowledged. Identified old WAL segments consuming space. Running pg_archivecleanup to free disk.",
    },
    {
        "task_id": "easy-2",
        "incident_id": "INC-0002",
        "alert_type": "5xx_errors",
        "service_name": "payment-api",
        "error_message": "CRITICAL: 100% of requests returning HTTP 500 — complete service outage",
        "metrics": {
            "cpu_percent": [12.0, 10.0, 8.0, 6.0, 5.0],
            "memory_percent": [45.0, 43.0, 42.0, 41.0, 40.0],
            "error_rate": [0.1, 5.0, 40.0, 85.0, 100.0],
            "latency_p99_ms": [200.0, 5000.0, 15000.0, 25000.0, 30000.0],
            "disk_percent": [55.0, 55.0, 55.0, 55.0, 55.0],
            "connections_active": [250.0, 180.0, 80.0, 20.0, 0.0],
            "timestamps": ["T-4min", "T-3min", "T-2min", "T-1min", "T-now"],
        },
        "logs_snippet": (
            "2024-01-16 09:01:00 ERROR payment-api: connection refused to postgres-primary:5432\n"
            "2024-01-16 09:01:01 ERROR payment-api: payment processing failed — DB unreachable\n"
            "2024-01-16 09:01:02 ERROR payment-api: HTTP 500 returned to client\n"
            "2024-01-16 09:01:03 ERROR payment-api: circuit breaker OPEN\n"
            "2024-01-16 09:01:04 FATAL payment-api: all health checks failing"
        ),
        "time_of_day": "2024-01-16T09:01:04Z",
        "related_alerts": ["postgres-primary unreachable", "Revenue impact detected"],
        "service_dependencies": ["postgres-primary", "stripe-gateway", "fraud-detection"],
        "recent_deployments": [],
        "expected_severity": "P0",
        "expected_team": "backend",
        "expected_escalate": True,
        "key_indicators": ["error_rate 100%", "complete outage", "circuit breaker OPEN"],
        "team_routing": {

            "alt_teams": ["database", "infra"],
            "alt_penalty": 0.10,
        },
        "consequence_observation": "Incident commander paged. Confirmed postgres-primary is fully down. All payment processing halted. Revenue loss accumulating.",
    },
    {
        "task_id": "easy-3",
        "incident_id": "INC-0003",
        "alert_type": "ssl_cert_expiry",
        "service_name": "cdn-edge",
        "error_message": "CRITICAL: SSL certificate expired 2 hours ago — HTTPS connections rejected",
        "metrics": {
            "cpu_percent": [18.0, 18.0, 18.0, 18.0, 18.0],
            "memory_percent": [35.0, 35.0, 35.0, 35.0, 35.0],
            "error_rate": [0.0, 10.0, 50.0, 85.0, 98.0],
            "latency_p99_ms": [50.0, 50.0, 50.0, 50.0, 50.0],
            "disk_percent": [40.0, 40.0, 40.0, 40.0, 40.0],
            "connections_active": [3200.0, 2400.0, 800.0, 50.0, 12.0],
            "timestamps": ["T-4min", "T-3min", "T-2min", "T-1min", "T-now"],
        },
        "logs_snippet": (
            "2024-01-17 06:00:00 WARN  cdn-edge: SSL cert expires in 0 days\n"
            "2024-01-17 08:00:01 ERROR cdn-edge: SSL handshake failed — certificate expired\n"
            "2024-01-17 08:00:02 ERROR cdn-edge: SSL_ERROR_RX_RECORD_TOO_LONG\n"
            "2024-01-17 08:00:03 ERROR cdn-edge: client rejected — CERT_DATE_INVALID\n"
            "2024-01-17 08:00:04 ERROR cdn-edge: 98% of connections failing TLS negotiation"
        ),
        "time_of_day": "2024-01-17T08:00:04Z",
        "related_alerts": ["TLS handshake failures spiking", "User-facing errors on all HTTPS endpoints"],
        "service_dependencies": ["web-frontend", "mobile-api", "static-assets"],
        "recent_deployments": [],
        "expected_severity": "P1",
        "expected_team": "infra",
        "expected_escalate": True,
        "key_indicators": ["SSL certificate expired", "CERT_DATE_INVALID", "TLS handshake failures"],
        "team_routing": {

            "alt_teams": ["network"],
            "alt_penalty": 0.05,
        },
        "consequence_observation": "Infra team deploying renewed certificate via cert-manager. ETA 10 minutes for full propagation across CDN edge nodes.",
    },
    {
        "task_id": "easy-4",
        "incident_id": "INC-0004",
        "alert_type": "cpu_spike",
        "service_name": "user-auth",
        "error_message": "WARNING: Single pod CPU at 99% — pod may be throttled",
        "metrics": {
            "cpu_percent": [30.0, 45.0, 70.0, 92.0, 99.0],
            "memory_percent": [50.0, 50.0, 51.0, 52.0, 52.0],
            "error_rate": [0.0, 0.0, 0.1, 0.1, 0.2],
            "latency_p99_ms": [80.0, 120.0, 200.0, 280.0, 320.0],
            "disk_percent": [30.0, 30.0, 30.0, 30.0, 30.0],
            "connections_active": [40.0, 42.0, 43.0, 44.0, 45.0],
            "timestamps": ["T-4min", "T-3min", "T-2min", "T-1min", "T-now"],
        },
        "logs_snippet": (
            "2024-01-18 11:45:00 INFO  user-auth: pod user-auth-7d9b8-xkz99 CPU throttled\n"
            "2024-01-18 11:45:05 WARN  user-auth: JWT validation taking 280ms avg\n"
            "2024-01-18 11:45:10 INFO  user-auth: other 4 pods nominal (CPU 20-30%)\n"
            "2024-01-18 11:45:15 INFO  user-auth: no increase in error rate cluster-wide\n"
            "2024-01-18 11:45:20 INFO  user-auth: Kubernetes restarting throttled pod"
        ),
        "time_of_day": "2024-01-18T11:45:20Z",
        "related_alerts": [],
        "service_dependencies": ["api-gateway", "session-store"],
        "recent_deployments": [],
        "expected_severity": "P3",
        "expected_team": "backend",
        "expected_escalate": False,
        "key_indicators": ["single pod", "cpu_percent 99", "other pods nominal"],
        "team_routing": {

            "alt_teams": ["infra"],
            "alt_penalty": 0.05,
        },
        "consequence_observation": "Kubernetes restarted the affected pod. CPU normalized. Single pod issue confirmed — no cluster-wide impact.",
    },
    {
        "task_id": "easy-5",
        "incident_id": "INC-0005",
        "alert_type": "brute_force",
        "service_name": "user-auth",
        "error_message": "CRITICAL: 50,000 failed login attempts in 5 minutes from 200 IPs",
        "metrics": {
            "cpu_percent": [40.0, 50.0, 60.0, 70.0, 75.0],
            "memory_percent": [55.0, 58.0, 62.0, 65.0, 68.0],
            "error_rate": [0.5, 1.0, 1.5, 2.5, 3.0],
            "latency_p99_ms": [200.0, 400.0, 600.0, 800.0, 890.0],
            "disk_percent": [45.0, 45.0, 45.0, 45.0, 45.0],
            "connections_active": [500.0, 1200.0, 2500.0, 3800.0, 4800.0],
            "timestamps": ["T-4min", "T-3min", "T-2min", "T-1min", "T-now"],
        },
        "logs_snippet": (
            "2024-01-19 02:15:00 WARN  user-auth: login failure rate 10x normal\n"
            "2024-01-19 02:15:10 ERROR user-auth: rate limit triggered for 192.168.x.x/24\n"
            "2024-01-19 02:15:20 ERROR user-auth: 200 distinct IPs hitting /login endpoint\n"
            "2024-01-19 02:15:30 WARN  user-auth: credential stuffing pattern detected\n"
            "2024-01-19 02:15:40 ERROR user-auth: 50k failed attempts — possible account takeover campaign"
        ),
        "time_of_day": "2024-01-19T02:15:40Z",
        "related_alerts": ["WAF rate limit threshold reached", "Anomalous geographic login distribution"],
        "service_dependencies": ["api-gateway", "session-store", "user-db"],
        "recent_deployments": [],
        "expected_severity": "P1",
        "expected_team": "security",
        "expected_escalate": True,
        "key_indicators": ["brute_force", "50000 failed attempts", "credential stuffing", "200 IPs"],
        "team_routing": {

            "alt_teams": ["infra", "backend"],
            "alt_penalty": 0.15,
        },
        "consequence_observation": "Security team enabled geo-blocking and CAPTCHA enforcement. Attack traffic reduced 90%. Investigating compromised credential database.",
    },

    # ─── MEDIUM (6-10) ────────────────────────────────────────────────────────
    {
        "task_id": "medium-1",
        "incident_id": "INC-0006",
        "alert_type": "5xx_errors",
        "service_name": "checkout-service",
        "error_message": "WARNING: 2% error rate on checkout — elevated but service degraded, not down",
        "metrics": {
            "cpu_percent": [40.0, 45.0, 48.0, 52.0, 55.0],
            "memory_percent": [65.0, 67.0, 69.0, 70.0, 71.0],
            "error_rate": [0.1, 0.5, 1.0, 1.5, 2.0],
            "latency_p99_ms": [400.0, 800.0, 1200.0, 1500.0, 1800.0],
            "disk_percent": [48.0, 48.0, 48.0, 48.0, 48.0],
            "connections_active": [200.0, 240.0, 280.0, 300.0, 320.0],
            "timestamps": ["T-4min", "T-3min", "T-2min", "T-1min", "T-now"],
        },
        "logs_snippet": (
            "2024-01-20 15:30:00 INFO  checkout-service: v2.3.1 deployed successfully\n"
            "2024-01-20 15:31:00 WARN  checkout-service: error rate climbing 0.5% -> 2%\n"
            "2024-01-20 15:31:30 ERROR checkout-service: NullPointerException in CartValidator.validate()\n"
            "2024-01-20 15:31:45 WARN  checkout-service: p99 latency 1800ms (baseline 400ms)\n"
            "2024-01-20 15:32:00 INFO  checkout-service: majority of requests still succeeding"
        ),
        "time_of_day": "2024-01-20T15:32:00Z",
        "related_alerts": ["Latency SLO breach on checkout"],
        "service_dependencies": ["payment-api", "inventory-service", "postgres-primary"],
        "recent_deployments": [
            {"service": "checkout-service", "version": "v2.3.1", "timestamp": "2024-01-20T15:30:00Z", "author": "alice"}
        ],
        "expected_severity": "P2",
        "expected_team": "backend",
        "expected_escalate": False,
        "key_indicators": ["recent deploy", "NullPointerException", "2% error rate", "degraded not down"],
        "team_routing": {

            "alt_teams": ["infra"],
            "alt_penalty": 0.10,
        },
        "consequence_observation": "Backend team identified NullPointerException in v2.3.1. Rollback to v2.3.0 initiated. Error rate dropping.",
    },
    {
        "task_id": "medium-2",
        "incident_id": "INC-0007",
        "alert_type": "memory_leak",
        "service_name": "recommendation-engine",
        "error_message": "WARNING: Memory usage 78% and growing +2%/hour — potential leak",
        "metrics": {
            "cpu_percent": [38.0, 39.0, 40.0, 41.0, 42.0],
            "memory_percent": [70.0, 72.0, 74.0, 76.0, 78.0],
            "error_rate": [0.0, 0.0, 0.0, 0.1, 0.1],
            "latency_p99_ms": [180.0, 185.0, 195.0, 205.0, 210.0],
            "disk_percent": [50.0, 50.0, 50.0, 50.0, 50.0],
            "connections_active": [85.0, 86.0, 87.0, 87.0, 88.0],
            "timestamps": ["T-4min", "T-3min", "T-2min", "T-1min", "T-now"],
        },
        "logs_snippet": (
            "2024-01-21 08:00:00 INFO  recommendation-engine: memory 60% (baseline)\n"
            "2024-01-21 16:00:00 INFO  recommendation-engine: memory 70%\n"
            "2024-01-21 20:00:00 WARN  recommendation-engine: memory 76%\n"
            "2024-01-21 22:00:00 WARN  recommendation-engine: memory 78% — trending upward\n"
            "2024-01-21 22:00:01 INFO  recommendation-engine: GC pressure increasing, heap growing"
        ),
        "time_of_day": "2024-01-21T22:00:01Z",
        "related_alerts": ["GC pause duration increasing"],
        "service_dependencies": ["product-catalog", "user-profile"],
        "recent_deployments": [],
        "expected_severity": "P3",
        "expected_team": "backend",
        "expected_escalate": False,
        "key_indicators": ["memory_percent 78", "gradual increase", "+2%/hour", "GC pressure"],
        "team_routing": {

            "alt_teams": ["infra"],
            "alt_penalty": 0.05,
        },
        "consequence_observation": "Backend team attached profiler. Identified unbounded cache in recommendation model. Planning fix for next sprint — safe for now with scheduled pod restarts.",
    },
    {
        "task_id": "medium-3",
        "incident_id": "INC-0008",
        "alert_type": "slow_queries",
        "service_name": "postgres-primary",
        "error_message": "WARNING: Query latency 10x normal during active data migration",
        "metrics": {
            "cpu_percent": [50.0, 60.0, 72.0, 82.0, 88.0],
            "memory_percent": [68.0, 72.0, 76.0, 80.0, 82.0],
            "error_rate": [0.0, 0.1, 0.2, 0.3, 0.5],
            "latency_p99_ms": [200.0, 1500.0, 4000.0, 6500.0, 8500.0],
            "disk_percent": [68.0, 69.0, 69.0, 70.0, 70.0],
            "connections_active": [100.0, 130.0, 160.0, 180.0, 195.0],
            "timestamps": ["T-4min", "T-3min", "T-2min", "T-1min", "T-now"],
        },
        "logs_snippet": (
            "2024-01-22 03:00:00 INFO  postgres: migration job started — adding index on orders(user_id)\n"
            "2024-01-22 03:01:00 WARN  postgres: table lock acquired on orders — blocking reads\n"
            "2024-01-22 03:02:00 WARN  postgres: slow query log: SELECT * FROM orders — 8500ms\n"
            "2024-01-22 03:03:00 INFO  postgres: migration 45% complete\n"
            "2024-01-22 03:03:30 WARN  postgres: connection pool utilization 97%"
        ),
        "time_of_day": "2024-01-22T03:03:30Z",
        "related_alerts": ["Connection pool near capacity", "API latency elevated"],
        "service_dependencies": ["order-service", "payment-api", "analytics"],
        "recent_deployments": [
            {"service": "postgres-primary", "version": "migration-v14", "timestamp": "2024-01-22T03:00:00Z", "author": "dba-bot"}
        ],
        "expected_severity": "P2",
        "expected_team": "database",
        "expected_escalate": False,
        "key_indicators": ["migration job", "table lock", "slow_queries", "expected degradation"],
        "team_routing": {

            "alt_teams": ["infra"],
            "alt_penalty": 0.10,
        },
        "consequence_observation": "DBA team monitoring migration progress — now at 75%. Query latency expected to normalize once index creation completes (~15 min).",
    },
    {
        "task_id": "medium-4",
        "incident_id": "INC-0009",
        "alert_type": "packet_loss",
        "service_name": "service-mesh",
        "error_message": "WARNING: 3% packet loss detected across service mesh — intermittent connectivity",
        "metrics": {
            "cpu_percent": [28.0, 29.0, 30.0, 30.0, 30.0],
            "memory_percent": [44.0, 44.0, 45.0, 45.0, 45.0],
            "error_rate": [0.2, 0.5, 0.8, 1.2, 1.5],
            "latency_p99_ms": [300.0, 500.0, 650.0, 800.0, 950.0],
            "disk_percent": [38.0, 38.0, 38.0, 38.0, 38.0],
            "connections_active": [1100.0, 1120.0, 1150.0, 1180.0, 1200.0],
            "timestamps": ["T-4min", "T-3min", "T-2min", "T-1min", "T-now"],
        },
        "logs_snippet": (
            "2024-01-23 13:00:00 WARN  envoy: upstream connect error — reset before headers\n"
            "2024-01-23 13:00:15 WARN  envoy: retries exhausted for order-service -> payment-api\n"
            "2024-01-23 13:00:30 INFO  envoy: 3% packet loss on east-west traffic\n"
            "2024-01-23 13:01:00 WARN  envoy: intermittent timeouts, not consistent\n"
            "2024-01-23 13:01:30 INFO  envoy: no single node fully unreachable"
        ),
        "time_of_day": "2024-01-23T13:01:30Z",
        "related_alerts": ["Increased retry rates across cluster", "Intermittent timeout errors"],
        "service_dependencies": ["all-services"],
        "recent_deployments": [],
        "expected_severity": "P2",
        "expected_team": "network",
        "expected_escalate": False,
        "key_indicators": ["packet_loss 3%", "service mesh", "intermittent", "no full outage"],
        "team_routing": {

            "alt_teams": ["infra"],
            "alt_penalty": 0.10,
        },
        "consequence_observation": "Network team running traceroutes and checking switch health. Identified flapping NIC on rack switch — replacing hardware.",
    },
    {
        "task_id": "medium-5",
        "incident_id": "INC-0010",
        "alert_type": "stale_cache",
        "service_name": "cdn-edge",
        "error_message": "WARNING: CDN serving stale assets after frontend deploy — cache not invalidated",
        "metrics": {
            "cpu_percent": [15.0, 15.0, 15.0, 15.0, 15.0],
            "memory_percent": [30.0, 30.0, 30.0, 30.0, 30.0],
            "error_rate": [0.0, 0.0, 0.0, 0.0, 0.0],
            "latency_p99_ms": [80.0, 80.0, 80.0, 80.0, 80.0],
            "disk_percent": [55.0, 55.0, 55.0, 55.0, 55.0],
            "connections_active": [3100.0, 3150.0, 3180.0, 3190.0, 3200.0],
            "timestamps": ["T-4min", "T-3min", "T-2min", "T-1min", "T-now"],
        },
        "logs_snippet": (
            "2024-01-24 10:00:00 INFO  cdn-edge: frontend v5.2.0 deployed\n"
            "2024-01-24 10:00:30 INFO  cdn-edge: cache invalidation request sent\n"
            "2024-01-24 10:02:00 WARN  cdn-edge: cache hit rate 99.8% — old assets still being served\n"
            "2024-01-24 10:03:00 INFO  cdn-edge: user reports of broken UI — button styles missing\n"
            "2024-01-24 10:04:00 WARN  cdn-edge: cache-control headers missing on new build artifacts"
        ),
        "time_of_day": "2024-01-24T10:04:00Z",
        "related_alerts": ["Frontend asset version mismatch"],
        "service_dependencies": ["web-frontend", "static-assets-s3"],
        "recent_deployments": [
            {"service": "cdn-edge", "version": "frontend-v5.2.0", "timestamp": "2024-01-24T10:00:00Z", "author": "ci-bot"}
        ],
        "expected_severity": "P3",
        "expected_team": "frontend",
        "expected_escalate": False,
        "key_indicators": ["stale_cache", "post-deploy", "no errors", "cache-control headers missing"],
        "team_routing": {

            "alt_teams": ["infra"],
            "alt_penalty": 0.10,
        },
        "consequence_observation": "Frontend team adding cache-busting hashes to build output. Manual CDN purge underway — assets refreshing across edge nodes.",
    },

    # ─── HARD (11-15) ─────────────────────────────────────────────────────────
    {
        "task_id": "hard-1",
        "incident_id": "INC-0011",
        "alert_type": "5xx_errors",
        "service_name": "order-service",
        "error_message": "ERROR: 15% error rate on order-service — backend 5xx errors, recent deploy suspect",
        "metrics": {
            "cpu_percent": [42.0, 43.0, 44.0, 44.0, 45.0],
            "memory_percent": [55.0, 56.0, 58.0, 59.0, 60.0],
            "error_rate": [0.5, 3.0, 7.0, 12.0, 15.0],
            "latency_p99_ms": [500.0, 2000.0, 5000.0, 9000.0, 12000.0],
            "disk_percent": [50.0, 50.0, 50.0, 50.0, 50.0],
            "connections_active": [200.0, 350.0, 420.0, 480.0, 498.0],
            "timestamps": ["T-4min", "T-3min", "T-2min", "T-1min", "T-now"],
        },
        "logs_snippet": (
            "2024-01-25 16:00:00 INFO  order-service: v3.1.0 deployed\n"
            "2024-01-25 16:05:00 ERROR order-service: FATAL: remaining connection slots reserved for replication\n"
            "2024-01-25 16:05:01 ERROR order-service: could not connect to server: FATAL: sorry, too many clients\n"
            "2024-01-25 16:05:02 ERROR order-service: HikariPool-1 — Connection is not available, timeout 30000ms\n"
            "2024-01-25 16:05:03 WARN  postgres: max_connections=500 REACHED — all slots exhausted"
        ),
        "time_of_day": "2024-01-25T16:05:03Z",
        "related_alerts": ["postgres-primary: max connections reached", "Multiple services experiencing DB errors"],
        "service_dependencies": ["postgres-primary", "payment-api", "inventory-service"],
        "recent_deployments": [
            {"service": "order-service", "version": "v3.1.0", "timestamp": "2024-01-25T16:00:00Z", "author": "bob"}
        ],
        "expected_severity": "P1",
        "expected_team": "database",
        "expected_escalate": True,
        "key_indicators": ["connection pool exhaustion", "max_connections reached", "too many clients", "DB root cause not deploy"],
        "team_routing": {

            "alt_teams": ["infra"],
            "alt_penalty": 0.10,
        },
        "cascade_trigger": {
            "condition": "wrong_severity_or_team",
            "feedback": "ACTION CAUSED ESCALATION: Payment API crashed due to DB overload. Revenue impact detected. Connection pool exhaustion spread to 3 additional services.",
            "new_alert": "payment-api CPU spike, 50% 5xx errors — cascading from DB pool exhaustion",
            "penalty": -0.20,
        },
        "consequence_observation": "Escalation team arrived, found DB connection pool at limit. Payment API experiencing cascading failures. DBA increasing max_connections and killing idle sessions.",
    },
    {
        "task_id": "hard-2",
        "incident_id": "INC-0012",
        "alert_type": "service_timeout",
        "service_name": "api-gateway",
        "error_message": "CRITICAL: Widespread service timeouts — appears to be multiple service failures",
        "metrics": {
            "cpu_percent": [22.0, 21.0, 20.0, 20.0, 20.0],
            "memory_percent": [40.0, 39.0, 38.0, 38.0, 38.0],
            "error_rate": [0.5, 15.0, 45.0, 70.0, 85.0],
            "latency_p99_ms": [200.0, 5000.0, 15000.0, 25000.0, 30000.0],
            "disk_percent": [42.0, 42.0, 42.0, 42.0, 42.0],
            "connections_active": [3000.0, 1500.0, 500.0, 50.0, 15.0],
            "timestamps": ["T-4min", "T-3min", "T-2min", "T-1min", "T-now"],
        },
        "logs_snippet": (
            "2024-01-26 04:30:00 ERROR api-gateway: upstream timeout — payment-api unreachable\n"
            "2024-01-26 04:30:01 ERROR api-gateway: upstream timeout — order-service unreachable\n"
            "2024-01-26 04:30:02 ERROR api-gateway: upstream timeout — user-auth unreachable\n"
            "2024-01-26 04:30:03 ERROR api-gateway: getaddrinfo ENOTFOUND payment-api.internal\n"
            "2024-01-26 04:30:04 ERROR api-gateway: getaddrinfo ENOTFOUND order-service.internal"
        ),
        "time_of_day": "2024-01-26T04:30:04Z",
        "related_alerts": ["DNS resolution failures cluster-wide", "All internal service discovery failing"],
        "service_dependencies": ["payment-api", "order-service", "user-auth", "internal-dns"],
        "recent_deployments": [],
        "expected_severity": "P0",
        "expected_team": "network",
        "expected_escalate": True,
        "key_indicators": ["ENOTFOUND", "DNS resolution failures", "all services affected", "getaddrinfo"],
        "team_routing": {

            "alt_teams": ["infra"],
            "alt_penalty": 0.10,
        },
        "cascade_trigger": {
            "condition": "wrong_severity_or_team",
            "feedback": "ACTION CAUSED ESCALATION: DNS outage not addressed — all microservices now unreachable. Complete platform outage. Customer-facing 502 errors on all endpoints.",
            "new_alert": "TOTAL PLATFORM OUTAGE: 100% of customer requests failing, all services returning 502",
            "penalty": -0.20,
        },
        "consequence_observation": "Network team identified CoreDNS pods crashed. Internal DNS resolution fully broken. Restarting CoreDNS deployment — services recovering.",
    },
    {
        "task_id": "hard-3",
        "incident_id": "INC-0013",
        "alert_type": "cpu_spike",
        "service_name": "worker-fleet",
        "error_message": "CRITICAL: Fleet-wide CPU 95%+ at 3 AM — all worker nodes affected simultaneously",
        "metrics": {
            "cpu_percent": [25.0, 40.0, 65.0, 85.0, 97.0],
            "memory_percent": [50.0, 60.0, 70.0, 80.0, 85.0],
            "error_rate": [0.0, 0.5, 1.0, 1.5, 2.0],
            "latency_p99_ms": [300.0, 1000.0, 2500.0, 4000.0, 5000.0],
            "disk_percent": [60.0, 62.0, 65.0, 68.0, 72.0],
            "connections_active": [100.0, 90.0, 70.0, 55.0, 50.0],
            "timestamps": ["T-4min", "T-3min", "T-2min", "T-1min", "T-now"],
        },
        "logs_snippet": (
            "2024-01-27 03:00:00 WARN  worker-fleet: CPU spike begins simultaneously on all 40 nodes\n"
            "2024-01-27 03:00:05 ERROR worker-fleet: unknown process 'kworker2' consuming 40% CPU per node\n"
            "2024-01-27 03:00:10 ERROR worker-fleet: outbound traffic to 45.33.32.156:4444 detected\n"
            "2024-01-27 03:00:15 ERROR worker-fleet: /tmp/.x11-unix/proc found — suspicious binary\n"
            "2024-01-27 03:00:20 FATAL worker-fleet: crontab modified on all nodes — persistence mechanism"
        ),
        "time_of_day": "2024-01-27T03:00:20Z",
        "related_alerts": ["Anomalous outbound network traffic", "Unknown processes on all nodes", "Crontab modifications detected"],
        "service_dependencies": ["batch-jobs", "data-pipeline", "ml-training"],
        "recent_deployments": [],
        "expected_severity": "P0",
        "expected_team": "security",
        "expected_escalate": True,
        "key_indicators": ["unknown process", "outbound C2 traffic", "3 AM simultaneous", "crontab modified", "suspicious binary"],
        "team_routing": {

            "alt_teams": ["infra"],
            "alt_penalty": 0.15,
        },
        "cascade_trigger": {
            "condition": "wrong_severity_or_team",
            "feedback": "ACTION CAUSED ESCALATION: Malware spread to control plane nodes. Attacker now has cluster-admin access. Data exfiltration in progress — customer PII at risk.",
            "new_alert": "SECURITY BREACH: Control plane compromised, unauthorized kubectl exec detected, data exfiltration to external IP",
            "penalty": -0.20,
        },
        "consequence_observation": "Security team isolating affected nodes from network. Forensics capturing memory dumps. Revoking all cluster credentials. Incident response plan activated.",
    },
    {
        "task_id": "hard-4",
        "incident_id": "INC-0014",
        "alert_type": "oom_restart",
        "service_name": "multiple-services",
        "error_message": "ERROR: Rolling OOM restarts across 6 different services — spreading over 2 hours",
        "metrics": {
            "cpu_percent": [35.0, 36.0, 38.0, 39.0, 40.0],
            "memory_percent": [80.0, 85.0, 89.0, 93.0, 96.0],
            "error_rate": [1.0, 2.0, 4.0, 6.0, 8.0],
            "latency_p99_ms": [800.0, 1200.0, 1800.0, 2500.0, 3200.0],
            "disk_percent": [55.0, 55.0, 55.0, 55.0, 55.0],
            "connections_active": [250.0, 240.0, 230.0, 220.0, 210.0],
            "timestamps": ["T-4min", "T-3min", "T-2min", "T-1min", "T-now"],
        },
        "logs_snippet": (
            "2024-01-28 18:00:00 WARN  payment-api: OOMKilled — restarting\n"
            "2024-01-28 18:30:00 WARN  order-service: OOMKilled — restarting\n"
            "2024-01-28 19:00:00 WARN  user-auth: OOMKilled — restarting (all use libcommon v4.2.1)\n"
            "2024-01-28 19:30:00 WARN  checkout-service: OOMKilled — restarting\n"
            "2024-01-28 20:00:00 ERROR k8s: 6 services OOMKilled — libcommon v4.2.1 upgraded 3h ago"
        ),
        "time_of_day": "2024-01-28T20:00:00Z",
        "related_alerts": ["Kubernetes OOMKilled events across namespaces", "Shared library recently upgraded"],
        "service_dependencies": ["libcommon", "payment-api", "order-service", "user-auth", "checkout-service"],
        "recent_deployments": [
            {"service": "libcommon", "version": "v4.2.1", "timestamp": "2024-01-28T17:00:00Z", "author": "platform-team"}
        ],
        "expected_severity": "P1",
        "expected_team": "infra",
        "expected_escalate": True,
        "key_indicators": ["shared library", "libcommon v4.2.1", "rolling OOM", "multiple services affected"],
        "team_routing": {

            "alt_teams": ["backend"],
            "alt_penalty": 0.10,
        },
        "cascade_trigger": {
            "condition": "wrong_severity_or_team",
            "feedback": "ACTION CAUSED ESCALATION: OOM kills now affecting auth service. Users cannot log in. Customer complaints flooding support channels.",
            "new_alert": "user-auth COMPLETELY DOWN: OOMKilled 5 times in 10 minutes, all login attempts failing",
            "penalty": -0.20,
        },
        "consequence_observation": "Infra team identified memory leak in libcommon v4.2.1 HTTP connection pooling. Rolling back to v4.2.0 across all services.",
    },
    {
        "task_id": "hard-5",
        "incident_id": "INC-0015",
        "alert_type": "latency_spike",
        "service_name": "payment-api",
        "error_message": "WARNING: Payment API p99 latency 8x baseline — correlates with recent deploy",
        "metrics": {
            "cpu_percent": [32.0, 33.0, 34.0, 34.0, 35.0],
            "memory_percent": [52.0, 53.0, 54.0, 54.0, 55.0],
            "error_rate": [0.0, 0.1, 0.1, 0.2, 0.3],
            "latency_p99_ms": [200.0, 1500.0, 5000.0, 9000.0, 12000.0],
            "disk_percent": [45.0, 45.0, 45.0, 45.0, 45.0],
            "connections_active": [120.0, 125.0, 130.0, 135.0, 140.0],
            "timestamps": ["T-4min", "T-3min", "T-2min", "T-1min", "T-now"],
        },
        "logs_snippet": (
            "2024-01-29 11:00:00 INFO  payment-api: v4.5.0 deployed\n"
            "2024-01-29 11:05:00 WARN  payment-api: p99 latency climbing 1500ms -> 12000ms\n"
            "2024-01-29 11:05:30 INFO  payment-api: internal processing time normal (200ms)\n"
            "2024-01-29 11:06:00 WARN  payment-api: stripe.com API calls timing out — 11800ms external wait\n"
            "2024-01-29 11:06:30 INFO  stripe-status: Stripe reports ongoing incident — elevated API latency"
        ),
        "time_of_day": "2024-01-29T11:06:30Z",
        "related_alerts": ["Stripe status page: elevated latency", "Third-party payment processor degraded"],
        "service_dependencies": ["stripe-gateway", "postgres-primary", "fraud-detection"],
        "recent_deployments": [
            {"service": "payment-api", "version": "v4.5.0", "timestamp": "2024-01-29T11:00:00Z", "author": "carol"}
        ],
        "expected_severity": "P2",
        "expected_team": "backend",
        "expected_escalate": False,
        "key_indicators": ["stripe outage", "external latency", "internal processing normal", "upstream dependency"],
        "team_routing": {

            "alt_teams": ["infra"],
            "alt_penalty": 0.05,
        },
        "consequence_observation": "Backend team confirmed internal systems healthy. Latency entirely from Stripe API. Monitoring Stripe status page — no action needed on our side.",
    },

    # ─── FALSE POSITIVES (16-18) ─────────────────────────────────────────────
    {
        "task_id": "false-positive-1",
        "incident_id": "INC-0016",
        "alert_type": "memory_warning",
        "service_name": "cron-job",
        "error_message": "WARNING: Memory usage 89% on cron-job worker",
        "metrics": {
            "cpu_percent": [15.0, 20.0, 45.0, 70.0, 82.0],
            "memory_percent": [30.0, 45.0, 65.0, 80.0, 89.0],
            "error_rate": [0.0, 0.0, 0.0, 0.0, 0.0],
            "latency_p99_ms": [50.0, 50.0, 50.0, 50.0, 50.0],
            "disk_percent": [55.0, 55.0, 55.0, 55.0, 55.0],
            "connections_active": [5.0, 5.0, 5.0, 5.0, 5.0],
            "timestamps": ["T-4min", "T-3min", "T-2min", "T-1min", "T-now"],
        },
        "logs_snippet": (
            "2024-02-01 02:00:00 INFO  cron-job: nightly backup job started (scheduled)\n"
            "2024-02-01 02:01:00 INFO  cron-job: loading database dump into memory for compression\n"
            "2024-02-01 02:02:00 INFO  cron-job: memory 65% — normal for backup workload\n"
            "2024-02-01 02:03:00 INFO  cron-job: compression phase — peak memory expected 85-90%\n"
            "2024-02-01 02:04:00 INFO  cron-job: memory 89% — on track, ETA 5 min to complete"
        ),
        "time_of_day": "2024-02-01T02:04:00Z",
        "related_alerts": [],
        "service_dependencies": [],
        "recent_deployments": [],
        "expected_severity": "P4",
        "expected_team": "infra",
        "expected_escalate": False,
        "key_indicators": ["nightly backup", "scheduled", "expected peak memory", "ETA 5 min", "no errors"],
        "is_false_positive": True,
        "false_positive_bonus": 0.10,
        "team_routing": {

            "alt_teams": ["backend"],
            "alt_penalty": 0.05,
        },
        "consequence_observation": "Backup job completed successfully in 4 minutes. Memory returned to 15%. This is expected nightly behavior.",
    },
    {
        "task_id": "false-positive-2",
        "incident_id": "INC-0017",
        "alert_type": "cpu_spike",
        "service_name": "staging-api",
        "error_message": "WARNING: CPU at 90% on staging-api — all pods affected",
        "metrics": {
            "cpu_percent": [10.0, 30.0, 55.0, 78.0, 90.0],
            "memory_percent": [40.0, 50.0, 60.0, 68.0, 75.0],
            "error_rate": [0.0, 2.0, 5.0, 8.0, 12.0],
            "latency_p99_ms": [100.0, 500.0, 1500.0, 3000.0, 5000.0],
            "disk_percent": [30.0, 30.0, 30.0, 30.0, 30.0],
            "connections_active": [10.0, 50.0, 200.0, 500.0, 800.0],
            "timestamps": ["T-4min", "T-3min", "T-2min", "T-1min", "T-now"],
        },
        "logs_snippet": (
            "2024-02-02 10:00:00 INFO  staging-api: load test initiated by QA team\n"
            "2024-02-02 10:00:30 INFO  staging-api: ramping to 10,000 concurrent users\n"
            "2024-02-02 10:01:00 INFO  staging-api: ENVIRONMENT=staging (non-production)\n"
            "2024-02-02 10:02:00 WARN  staging-api: CPU 78% under load test — expected\n"
            "2024-02-02 10:03:00 INFO  staging-api: load test scheduled to end at 10:15"
        ),
        "time_of_day": "2024-02-02T10:03:00Z",
        "related_alerts": ["Staging environment load test in progress"],
        "service_dependencies": ["staging-db", "staging-cache"],
        "recent_deployments": [],
        "expected_severity": "P4",
        "expected_team": "backend",
        "expected_escalate": False,
        "key_indicators": ["staging", "load test", "non-production", "scheduled", "QA team initiated"],
        "is_false_positive": True,
        "false_positive_bonus": 0.10,
        "team_routing": {

            "alt_teams": ["infra"],
            "alt_penalty": 0.05,
        },
        "consequence_observation": "Load test completed at 10:15 as scheduled. CPU returned to 10%. Staging environment operating normally.",
    },
    {
        "task_id": "false-positive-3",
        "incident_id": "INC-0018",
        "alert_type": "5xx_errors",
        "service_name": "canary-deploy",
        "error_message": "WARNING: 5% error rate on canary-deploy — elevated errors detected",
        "metrics": {
            "cpu_percent": [20.0, 22.0, 25.0, 28.0, 30.0],
            "memory_percent": [40.0, 42.0, 45.0, 48.0, 50.0],
            "error_rate": [0.0, 1.0, 2.5, 4.0, 5.0],
            "latency_p99_ms": [100.0, 200.0, 350.0, 500.0, 600.0],
            "disk_percent": [35.0, 35.0, 35.0, 35.0, 35.0],
            "connections_active": [10.0, 12.0, 15.0, 18.0, 20.0],
            "timestamps": ["T-4min", "T-3min", "T-2min", "T-1min", "T-now"],
        },
        "logs_snippet": (
            "2024-02-03 14:00:00 INFO  canary-deploy: v6.0.0-rc1 deployed to canary (1% of traffic)\n"
            "2024-02-03 14:01:00 INFO  canary-deploy: auto-rollback threshold set at 10% error rate\n"
            "2024-02-03 14:02:00 WARN  canary-deploy: 5% error rate on canary slice (99% traffic unaffected)\n"
            "2024-02-03 14:03:00 INFO  canary-deploy: production traffic on v5.9.0 healthy (0.01% errors)\n"
            "2024-02-03 14:04:00 INFO  canary-deploy: monitoring canary — auto-rollback will trigger at 10%"
        ),
        "time_of_day": "2024-02-03T14:04:00Z",
        "related_alerts": ["Canary deployment monitoring active"],
        "service_dependencies": ["api-gateway", "feature-flags"],
        "recent_deployments": [
            {"service": "canary-deploy", "version": "v6.0.0-rc1", "timestamp": "2024-02-03T14:00:00Z", "author": "ci-bot"}
        ],
        "expected_severity": "P3",
        "expected_team": "backend",
        "expected_escalate": False,
        "key_indicators": ["canary", "1% of traffic", "auto-rollback", "production healthy", "monitoring active"],
        "is_false_positive": True,
        "false_positive_bonus": 0.10,
        "team_routing": {

            "alt_teams": ["infra"],
            "alt_penalty": 0.05,
        },
        "consequence_observation": "Canary auto-rolled back at 10% error threshold. Production unaffected. Backend team investigating v6.0.0-rc1 regression.",
    },
]
