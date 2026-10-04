import argparse
import json
import os

import httpx

from app.intelligence.jev.detector import OPENROUTER_DECISIONS_URL, QUESTIONS


parser = argparse.ArgumentParser(description="Test Jev with mock infrastructure metrics.")
parser.add_argument("metrics", help="Mock metrics as a text description")
args = parser.parse_args()

api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    parser.error("OPENROUTER_API_KEY is required")

response = httpx.post(
    OPENROUTER_DECISIONS_URL,
    headers={"Authorization": f"Bearer {api_key}"},
    json={
        "model": os.getenv("JEV_MODEL", "typesafe/jev-1.13"),
        "state": args.metrics,
        "questions": QUESTIONS,
    },
    timeout=10,
)
response.raise_for_status()
print(json.dumps(response.json()["answers"], indent=2))
