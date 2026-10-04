import { AIProviderIntegrationCard, DecisionModelIntegrationCard, PrometheusIntegrationCard, SlackIntegrationCard } from "@/components/AICloudIntegrationCards";
import { getIntegrationStatus } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function IntegrationsPage() {
  const status = await getIntegrationStatus();
  return (
    <div>
      <h1 className="text-3xl font-semibold tracking-tight">Integrations</h1>
      <p className="mt-3 text-neutral-500">Connect the tools OpsPilot uses to monitor and notify you.</p>
      <div className="mt-8 grid auto-rows-fr gap-5 md:grid-cols-2">
        <PrometheusIntegrationCard
          initiallyConnected={status.prometheus?.configured ?? false}
          initialUrl={status.prometheus?.url ?? null}
          initialAuthType={status.prometheus?.auth_type ?? "none"}
          initialServiceName={status.prometheus?.service_name ?? "prometheus"}
        />
        <DecisionModelIntegrationCard initiallyConnected={status.decision_model.configured} initialModel={status.decision_model.model} />
        <AIProviderIntegrationCard initiallyConnected={status.ai.configured} initialProvider={status.ai.provider} initialModel={status.ai.model} />
        <SlackIntegrationCard initiallyConnected={status.slack.configured} />
      </div>
    </div>
  );
}
