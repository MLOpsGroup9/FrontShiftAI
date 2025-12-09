# FrontShiftAI - Monitoring & Observability Documentation

**Status:** ✅ Fully Implemented  
**Tools:** Google Cloud Monitoring + Weights & Biases (W&B)

---

## 1. GCP Cloud Monitoring (Infrastructure) ✅

Infrastructure-level monitoring handles the "health" of the underlying services (Cloud Run, Cloud SQL).

### Metrics Tracked
- **Request Count**: Volume of incoming traffic
- **Response Latency (p95)**: 95th percentile latency (user experience)
- **Error Rate (5xx)**: Server-side errors
- **CPU Utilization**: Container resource usage
- **Memory Utilization**: Container memory usage
- **Container Instance Count**: Auto-scaling behavior (0-10 instances)

---

## 2. GCP Alerts ✅

Proactive alerting system configured to notify administrators of critical issues.

| Alert Name | Condition | Duration | Notification |
|------------|-----------|----------|--------------|
| **High Error Rate** | > 10 errors/min | 5 min | Email (group9mlops@gmail.com) |
| **High Response Latency** | > 3 seconds | 5 min | Email |
| **High CPU Usage** | > 80% utilization | 5 min | Email |

---

## 3. WANDB Request Monitoring (Application) ✅

Application-level request tracking logging every API hit to Weights & Biases.

| Metric | Description |
|--------|-------------|
| `request/endpoint` | API endpoint accessed (e.g., `/api/chat`) |
| `request/method` | HTTP method (GET, POST) |
| `request/status_code` | Response status (200, 403, 500) |
| `request/latency_ms` | Processing time in milliseconds |
| `request/success` | Binary indicator (1=success) |
| `request/error` | Binary indicator (1=error) |
| `request/company_id` | Multi-tenant isolation tracking |
| `request/user_id` | User activity tracking |

---

## 4. WANDB Agent Monitoring (Business Logic) ✅

Performance metrics for specific AI agents.

| Agent | Metric | Description |
|-------|--------|-------------|
| **PTO** | `agent/pto/execution_time_ms` | Time to process PTO request |
| | `agent/pto/success` | Successful completion |
| | `agent/pto/failure` | Failed execution |
| **HR Ticket** | `agent/hr_ticket/execution_time_ms` | Time to process ticket |
| | `agent/hr_ticket/success` | Successful completion |
| **RAG** | `agent/rag/execution_time_ms` | Retrieval & Generation time |
| | `agent/rag/success` | Successful query |
| **Website** | `agent/website_extraction/execution_time_ms` | Scraper performance |

---

## 5. WANDB Business Metrics (KPIs) ✅

High-level business value metrics.

### PTO System
- `business/pto_request_created`: New PTO submission
- `business/pto_approved`: Admin approval count
- `business/pto_denied`: Admin denial count
- `business/pto_days_approved`: Total days approved
- `business/pto_days_denied`: Total days denied

### HR Ticket System
- `business/hr_ticket_created`: New ticket count
- `business/hr_ticket_cancelled`: Cancellation count
- `business/hr_ticket_picked_up`: Admin pickup events
- `business/hr_meeting_scheduled`: Scheduled meetings
- `business/hr_ticket_resolved`: Resolution events
- `business/hr_ticket_resolution_time_hours`: Time to resolve

---

## 6. WANDB Database Monitoring ✅

Query performance tracking to identify slow database operations.

| Query Type | Metric |
|------------|--------|
| PTO Balance Check | `database/pto_balance_check/execution_time_ms` |
| View PTO Requests | `database/pto_requests_list/execution_time_ms` |
| Admin View PTO | `database/admin_pto_requests/execution_time_ms` |
| View HR Tickets | `database/hr_tickets_user_list/execution_time_ms` |
| Ticket Details | `database/hr_ticket_detail/execution_time_ms` |
| Admin Ticket Queue | `database/admin_hr_ticket_queue/execution_time_ms` |
| Ticket Stats | `database/hr_ticket_stats/execution_time_ms` |
| Rows Affected | `database/*/rows_affected` |

---

## 7. Code-Based Alerts (Real-time) ✅

The `ProductionMonitor` class implements immediate checking against defined thresholds.

| Threshold | Limit | Action |
|-----------|-------|--------|
| **Request Latency** | > 3000ms | Log Warning + W&B Alert |
| **Error Rate** | > 5% | Log Warning + W&B Alert |
| **Agent Success Rate** | < 90% | Log Warning + W&B Alert |
| **Database Query** | > 1000ms | Log Warning + W&B Alert |
| **Agent Execution** | > 5000ms | Log Warning + W&B Alert |

---

## Summary

| Component | Count | Status |
|-----------|-------|--------|
| **GCP Infrastructure Metrics** | 6 | ✅ Deployed |
| **GCP Alerts** | 3 | ✅ Deployed |
| **WANDB Request Metrics** | 8 | ✅ Coded |
| **WANDB Agent Metrics** | 12+ | ✅ Coded |
| **WANDB Business Metrics** | 11 | ✅ Coded |
| **WANDB Database Metrics** | 7+ | ✅ Coded |
| **Code-Based Alerts** | 5 | ✅ Coded |
| **TOTAL METRICS** | **52+** | **✅** |
