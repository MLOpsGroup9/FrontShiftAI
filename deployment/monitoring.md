Complete Monitoring Plan for FrontShiftAI

Here's what we'll implement across all steps:
Step 1: GCP Cloud Monitoring (Infrastructure)

    Request count and throughput
    Response latency (p50, p95, p99)
    Error rates (4xx, 5xx errors)
    CPU and memory usage
    Container instances count
    Cold start metrics

Step 2: WANDB Monitoring (ML/AI Metrics)

    Agent execution times (LangGraph workflows)
    Token usage per request
    RAG retrieval quality (ChromaDB queries)
    Embedding generation performance
    Success/failure rates of AI operations
    Cost tracking (API calls to Mercury/Groq)

Step 3: Application Metrics (Business Logic)

    PTO requests processed
    HR tickets created/resolved
    Multi-tenant usage per company
    API endpoint usage patterns
    Database query performance

Step 4: Alerts & Documentation

    Set up alerts for critical thresholds
    Create monitoring documentation for coursework

So in total: Infrastructure + AI/ML + Business metrics + Alerting


