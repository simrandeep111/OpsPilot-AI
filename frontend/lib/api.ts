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
  prometheus: { configured: boolean; url: string | null; auth_type: "none" | "basic" | "bearer"; service_name: string };
};

export function getIntegrationStatus() {
  return getJson<IntegrationStatus>("/api/integrations", {
    ai: { configured: false, provider: null, model: null },
    decision_model: { configured: false, provider: "openrouter", model: null },
    slack: { configured: false },
    prometheus: { configured: false, url: null, auth_type: "none", service_name: "prometheus" },
  });
}
