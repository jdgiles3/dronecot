# Multi-Agent AI System

Orchestrated small language models with full data pipeline integration for autonomous task execution.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACE                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Chat UI   │  │  Dashboard  │  │  Shift Log  │  │   Alerts    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATION LAYER                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Agent Coordinator (FastAPI)                       │   │
│  │  - Task routing    - Model selection    - Response aggregation      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
┌───────────────┐         ┌───────────────┐         ┌───────────────┐
│  ALERT AGENT  │         │ ANALYSIS AGENT│         │  TASK AGENT   │
│  (Phi-3/Qwen) │         │ (Mistral/Llama)│        │ (CodeLlama)   │
│               │         │               │         │               │
│ - Anomaly det │         │ - Pattern rec │         │ - Code gen    │
│ - Threshold   │         │ - Insights    │         │ - Playwright  │
│ - Notify      │         │ - Reports     │         │ - Vision      │
└───────────────┘         └───────────────┘         └───────────────┘
        │                           │                           │
        └───────────────────────────┼───────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          MESSAGE BROKER (Kafka)                              │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐          │
│  │ alerts  │  │ tasks   │  │ ingest  │  │ results │  │  logs   │          │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
┌───────────────┐         ┌───────────────┐         ┌───────────────┐
│    REDIS      │         │  OPENSEARCH   │         │  SEAWEEDFS    │
│    Cache      │         │    Index      │         │   Storage     │
│               │         │               │         │               │
│ - Sessions    │         │ - Full-text   │         │ - Files       │
│ - Hot data    │         │ - Vectors     │         │ - Blobs       │
│ - Rate limit  │         │ - Analytics   │         │ - Metadata    │
└───────────────┘         └───────────────┘         └───────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TIKA PROCESSING                                      │
│  - Document extraction    - OCR    - Metadata parsing    - Content analysis │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Components

### Agents (Small Language Models)

| Agent | Model | Purpose |
|-------|-------|---------|
| Alert Agent | Phi-3-mini / Qwen2-0.5B | Real-time anomaly detection, threshold monitoring |
| Analysis Agent | Mistral-7B / Llama-3.2-3B | Pattern recognition, insights, report generation |
| Task Agent | CodeLlama-7B / Qwen2.5-Coder | Code generation, Playwright automation |
| Vision Agent | LLaVA / Moondream | Image analysis, visual task execution |
| Data Agent | TinyLlama / Phi-3 | Database queries, data retrieval |

### Services

- **Kafka**: Message broker for async communication
- **OpenSearch**: Full-text search and vector storage
- **Redis**: Caching and session management
- **SeaweedFS**: Distributed file storage
- **Tika**: Document processing and extraction

### Capabilities

1. **Alert Generation**: Anomaly detection, threshold alerts, pattern-based notifications
2. **Data Analysis**: Pattern inference, trend analysis, statistical insights
3. **Task Execution**: Playwright browser automation, API calls, file operations
4. **Data Management**: Ingestion, tagging, metadata extraction, search
5. **Shift Logs**: Activity tracking, handoff reports, audit trails
6. **Vision Tasks**: Image analysis, screenshot interpretation, visual automation

## Quick Start

```bash
# Start infrastructure
docker-compose up -d

# Start agents
./start_agents.sh

# Access UI
open http://localhost:3001
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat` | POST | Send message to agent coordinator |
| `/tasks` | POST | Submit autonomous task |
| `/alerts` | GET | Get active alerts |
| `/search` | POST | Search indexed data |
| `/ingest` | POST | Ingest new data |
| `/shift-log` | GET/POST | Manage shift logs |
| `/ws` | WebSocket | Real-time updates |
