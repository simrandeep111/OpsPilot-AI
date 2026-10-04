export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function getJson<T>(path: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(`${API_URL}${path}`, { cache: "no-store" });
    return response.ok ? await response.json() : fallback;
  } catch {
    return fallback;
  }
}

export type IntegrationStatus = {
  ai: { configured: boolean; provider: "openai" | "anthropic" | "groq" | null; model: string | null };
  decision_model: { configured: boolean; provider: "openrouter"; model: string | null };
  slack: { configured: boolean };
  aws: { configured: boolean; role_arn: string | null; regions: string[] };
};

export function getIntegrationStatus() {
  return getJson<IntegrationStatus>("/api/integrations", {
    ai: { configured: false, provider: null, model: null },
    decision_model: { configured: false, provider: "openrouter", model: null },
    slack: { configured: false },
    aws: { configured: false, role_arn: null, regions: [] },
  });
}
