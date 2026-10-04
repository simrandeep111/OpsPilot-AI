# OpsPilot AI

OpsPilot AI is a cloud-operations demo that monitors AWS infrastructure, detects emerging incidents with a structured decision model, generates a likely cause and recommended action, and optionally sends the result to Slack.

The project includes:

- A Next.js landing page and integration dashboard
- A FastAPI backend with automatic and manual monitoring endpoints
- AWS discovery for EC2, ECS, Application Load Balancers, and RDS
- 60-minute CloudWatch metric trends
- Jev decision models through OpenRouter
- Incident explanations through OpenAI, Anthropic Claude, or Groq
- Slack webhook notifications

OpsPilot confirms an abnormal result twice before creating an incident. Incidents and credentials entered through the UI are stored only in backend memory and reset when the backend restarts.

## Project structure

```text
backend/    FastAPI API, AWS collectors, decision model, and monitoring services
frontend/   Next.js UI built with React, Tailwind CSS, and Radix UI
```

## Prerequisites

- Python 3.11 or newer
- Node.js 20 or newer
- An OpenRouter API key for incident decisions
- Optional AWS, AI-provider, and Slack credentials

## Local setup

### 1. Start the backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --env-file .env
```

The backend runs at `http://localhost:8000`. API documentation is available at `http://localhost:8000/docs`.

### 2. Start the frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`, select **Get Started**, and configure the integrations you want to use.

## Configuration

Copy `backend/.env.example` to `backend/.env` and configure any integrations that should be available when the backend starts:

| Variable | Purpose | Default |
| --- | --- | --- |
| `MONITORING_ENABLED` | Run the automatic AWS monitoring loop | `true` |
| `MONITORING_INTERVAL_SECONDS` | Delay between automatic checks | `60` |
| `OPENROUTER_API_KEY` | OpenRouter key used by the decision model | Empty |
| `JEV_MODEL` | OpenRouter decision-model ID | `typesafe/jev-1.13` |
| `JEV_INCIDENT_PROBABILITY` | Minimum incident probability | `0.70` |
| `AI_PROVIDER` | `openai`, `anthropic`, or `groq` | `groq` |
| `AI_API_KEY` | API key for the selected AI provider | Empty |
| `AI_MODEL` | Model used for cause and action analysis | `openai/gpt-oss-20b` |
| `SLACK_WEBHOOK_URL` | Slack incoming-webhook URL | Empty |
| `AWS_ROLE_ARN` | Monitoring role assumed by OpsPilot | Empty |
| `AWS_EXTERNAL_ID` | External ID required by the role trust policy | Empty |
| `AWS_REGIONS` | Comma-separated AWS regions | `us-east-1` |

The same services can be configured from the Integrations page. Values entered in the UI are kept only in backend memory. Use environment variables or a secrets manager for deployed environments.

## AWS IAM setup

OpsPilot uses the AWS SDK's default credential chain to obtain its initial identity, then calls `sts:AssumeRole` to access the monitoring role. Configure the following three IAM policies separately.

For local development, provide the caller identity through a normal AWS profile or standard AWS credential environment variables. In a hosted environment, attach an execution role to the backend service. Do not place long-lived AWS access keys in the repository.

### 1. Monitoring role permissions policy

Attach this read-only permissions policy to the role identified by `AWS_ROLE_ARN`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:DescribeInstanceStatus",
        "ec2:DescribeRegions",
        "ecs:ListClusters",
        "ecs:ListServices",
        "ecs:ListTasks",
        "ecs:DescribeServices",
        "ecs:DescribeTasks",
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeTargetGroups",
        "elasticloadbalancing:DescribeTargetHealth",
        "cloudwatch:GetMetricStatistics",
        "rds:DescribeDBInstances"
      ],
      "Resource": "*"
    }
  ]
}
```

### 2. OpsPilot caller permissions policy

Attach this policy to the IAM user or execution role that runs OpsPilot. Replace the resource with the monitoring role ARN:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Resource": "arn:aws:iam::<AWS_ACCOUNT_ID>:role/<OPSPILOT_MONITORING_ROLE>"
    }
  ]
}
```

### 3. Monitoring role trust policy

Set the monitoring role's trust relationship to the identity running OpsPilot. Use the same external ID in this policy and in `AWS_EXTERNAL_ID` or the Integrations page.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::<CALLER_ACCOUNT_ID>:role/<OPSPILOT_CALLER_ROLE>"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "<RANDOM_EXTERNAL_ID>"
        }
      }
    }
  ]
}
```

If OpsPilot runs under an IAM user during local development, replace the role ARN under `Principal` with that user's ARN. Use a unique, randomly generated external ID.

## Test without an AWS account

Configure the OpenRouter decision model, start the backend, and submit the same abnormal snapshot twice. The second request satisfies the confirmation check:

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

Repeat the request once, then view incidents at `http://localhost:8000/api/incidents`.

## Main API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Backend health and configuration summary |
| `GET` | `/api/integrations` | Current integration status |
| `POST` | `/api/integrations/decision-model` | Test and configure OpenRouter/Jev |
| `POST` | `/api/integrations/ai` | Test and configure the AI provider |
| `POST` | `/api/integrations/aws` | Test and configure the AWS role |
| `POST` | `/api/integrations/slack` | Test and configure Slack |
| `GET` | `/api/integrations/aws/inventory` | Collect the AWS resource inventory |
| `POST` | `/api/metrics/collect` | Collect AWS metrics and analyze them |
| `POST` | `/api/metrics/analyze` | Analyze a supplied metric snapshot |
| `GET` | `/api/incidents` | List incidents |
| `PATCH` | `/api/incidents/{id}/resolve` | Resolve an incident |

## Tests and checks

Run the backend test suite:

```bash
cd backend
source .venv/bin/activate
python -m unittest discover -s tests -v
```

Check and build the frontend:

```bash
cd frontend
npm run check
npm run build
```

## Deployment notes

- Set `NEXT_PUBLIC_API_URL` to the deployed backend URL before building the frontend.
- Add the deployed frontend origin to `allow_origins` in `backend/app/main.py`.
- Store credentials in the hosting provider's secret manager or environment settings.
- The current incident store and UI-provided credentials are in-memory and are intended for a demo, not durable production storage.
