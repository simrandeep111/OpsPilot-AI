# OpsPilot AI

OpsPilot AI is a monitoring demo that reads Prometheus metrics, detects emerging incidents with a structured decision model, generates a likely cause and recommended action, and sends the result to Slack.

The project includes:

- A Next.js landing page and integration dashboard
- A FastAPI backend with automatic and manual monitoring endpoints
- Prometheus HTTP API integration with None, Basic, and Bearer authentication
- 60-minute PromQL metric trends
- Jev decision models through OpenRouter
- Incident explanations through OpenAI, Anthropic Claude, or Groq
- Slack webhook notifications
- A credential-free Try Demo flow using simulated metrics

OpsPilot confirms an abnormal result twice before creating an incident. Incidents and credentials entered through the UI are stored only in backend memory and reset when the backend restarts.

## Project structure

```text
backend/    FastAPI API, Prometheus client, decision model, and monitoring services
frontend/   Next.js UI built with React, Tailwind CSS, and Radix UI
```

## Prerequisites

- Python 3.11 or newer
- Node.js 20 or newer
- An OpenRouter API key for incident decisions
- Optional Prometheus, AI-provider, and Slack credentials

## Local setup

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --env-file .env
```

The backend runs at `http://localhost:8000`. API documentation is available at `http://localhost:8000/docs`.

### Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000` and select **Get Started**.

## Configuration

Copy `backend/.env.example` to `backend/.env`:

| Variable | Purpose | Default |
| --- | --- | --- |
| `MONITORING_ENABLED` | Run the automatic Prometheus monitoring loop | `true` |
| `MONITORING_INTERVAL_SECONDS` | Delay between automatic checks | `60` |
| `CORS_ORIGINS` | Comma-separated frontend URLs allowed to call the API | `http://localhost:3000` |
| `OPENROUTER_API_KEY` | OpenRouter key used by the decision model | Empty |
| `JEV_MODEL` | OpenRouter decision-model ID | `typesafe/jev-1.13` |
| `JEV_INCIDENT_PROBABILITY` | Minimum incident probability | `0.70` |
| `AI_PROVIDER` | `openai`, `anthropic`, or `groq` | `groq` |
| `AI_API_KEY` | API key for the selected AI provider | Empty |
| `AI_MODEL` | Model used for cause and action analysis | `openai/gpt-oss-20b` |
| `SLACK_WEBHOOK_URL` | Slack incoming-webhook URL | Empty |
| `PROMETHEUS_URL` | Base URL of the Prometheus HTTP API | Empty |
| `PROMETHEUS_AUTH_TYPE` | `none`, `basic`, or `bearer` | `none` |
| `PROMETHEUS_USERNAME` | Basic Auth username | Empty |
| `PROMETHEUS_PASSWORD` | Basic Auth password | Empty |
| `PROMETHEUS_TOKEN` | Bearer token | Empty |
| `PROMETHEUS_SERVICE_NAME` | Service name attached to collected snapshots | `prometheus` |
| `PROMETHEUS_ALLOW_PRIVATE` | Allow localhost/private Prometheus URLs | `false` |

Integrations can also be configured from the UI. Use environment variables or a secrets manager for deployed environments.

## Prometheus setup

The integration tests the connection with `GET /api/v1/query?query=up` and reads one hour of data through `/api/v1/query_range` at five-minute resolution.

OpsPilot queries these common metric names:

| Signal | Expected Prometheus metric |
| --- | --- |
| CPU | `node_cpu_seconds_total` |
| Memory | `node_memory_MemAvailable_bytes`, `node_memory_MemTotal_bytes` |
| P95 latency | `http_request_duration_seconds_bucket` |
| Errors and request rate | `http_requests_total` |
| Target availability | `up` |

Metric names vary between applications. Adjust `PROMQL_QUERIES` in `backend/app/integrations/prometheus/client.py` if your exporters use different names.

For local Prometheus at `http://localhost:9090`, set:

```ini
PROMETHEUS_ALLOW_PRIVATE=true
```

Keep this `false` on a public deployment. A deployed backend can connect only to a Prometheus server reachable from its network; it cannot reach Prometheus running on a recruiter's laptop.

## Try Demo

Try Demo does not require Prometheus. Connect the Decision Model, AI Provider, and Slack, then select **Try Demo**. OpsPilot sends a simulated abnormal snapshot twice, creates the confirmed incident, generates the analysis, and sends the Slack alert.

You can also submit the same sample manually twice:

```bash
curl -X POST http://localhost:8000/api/metrics/analyze \
  -H 'Content-Type: application/json' \
  -d '{
    "service": "payment-api",
    "cpu_percent": 98,
    "memory_percent": 70,
    "latency_ms": 2400,
    "error_rate_percent": 18,
    "request_rate": 120,
    "baseline_cpu_percent": 45,
    "baseline_latency_ms": 180,
    "baseline_error_rate_percent": 0.4,
    "baseline_request_rate": 50
  }'
```

## Main API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Backend health and integration summary |
| `GET` | `/api/integrations` | Current integration status |
| `POST` | `/api/integrations/prometheus` | Test and configure Prometheus |
| `POST` | `/api/integrations/decision-model` | Test and configure OpenRouter/Jev |
| `POST` | `/api/integrations/ai` | Test and configure the AI provider |
| `POST` | `/api/integrations/slack` | Test and configure Slack |
| `POST` | `/api/metrics/collect` | Collect Prometheus metrics and analyze them |
| `POST` | `/api/metrics/analyze` | Analyze a supplied metric snapshot |
| `GET` | `/api/incidents` | List incidents |
| `PATCH` | `/api/incidents/{id}/resolve` | Resolve an incident |

## Tests and checks

```bash
cd backend
source .venv/bin/activate
python -m unittest discover -s tests -v
```

```bash
cd frontend
npm run check
npm run build
```

## Deployment notes

- Set `NEXT_PUBLIC_API_URL` to the deployed backend URL before building the frontend.
- Set `CORS_ORIGINS` to the deployed frontend URL in the backend environment.
- Keep `PROMETHEUS_ALLOW_PRIVATE=false` on public deployments.
- Store credentials in the hosting provider's secret manager or environment settings.
- The current incident store and UI-provided credentials are in-memory and intended for a demo, not durable production storage.
