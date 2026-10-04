# OpsPilot AI

OpsPilot automatically discovers AWS resources, reads their CloudWatch metrics,
calculates 60-minute trends, and sends the trends plus correlated resource health to Jev through
OpenRouter. Jev determines whether an incident exists and classifies its type and severity. After two
consecutive abnormal checks, OpsPilot asks the selected AI provider for a cause and action, stores
the incident, and optionally sends a Slack webhook notification.

## Run the backend

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add your OPENROUTER_API_KEY to .env.
uvicorn app.main:app --reload --env-file .env
```

In another terminal, run the UI:

```bash
cd frontend
npm run dev
```

OpenAI, Anthropic Claude, Groq, and AWS can be connected from the Integrations page. UI credentials
are held only in backend memory and must be re-entered after a backend restart.
For durable production storage, use a secrets manager.

The AWS IAM role must allow these read-only actions:

```text
ec2:DescribeInstances
ec2:DescribeInstanceStatus
ec2:DescribeRegions
ecs:ListClusters
ecs:ListServices
ecs:ListTasks
ecs:DescribeServices
ecs:DescribeTasks
elasticloadbalancing:DescribeLoadBalancers
elasticloadbalancing:DescribeTargetGroups
elasticloadbalancing:DescribeTargetHealth
cloudwatch:GetMetricStatistics
rds:DescribeDBInstances
```

Its trust policy must allow the identity running OpsPilot to call
`sts:AssumeRole` with the configured external ID.

## Test with mock metrics

With the backend running, send a snapshot twice (the confirmation check) without needing a live
AWS account:

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

# Repeat the same request once to confirm the Jev result.
```

View incidents at `http://localhost:8000/api/incidents` and API documentation at
`http://localhost:8000/docs`.

Run the isolated test suite with:

```bash
cd backend
python -m unittest discover -s tests -v
```
