"use client";

import { FormEvent, useState } from "react";
import { Activity, BrainCircuit, CheckCircle2, CircleAlert, GitBranch, Loader2, MessageSquare, X } from "lucide-react";
import { API_URL } from "@/lib/api";
import { Badge, Button, Card, Dialog } from "./ui";


type Status = "idle" | "testing" | "success" | "error";
type Provider = "openai" | "anthropic" | "groq";
type PrometheusAuthType = "none" | "basic" | "bearer";

const PROVIDERS: Record<Provider, { label: string; models: { id: string; label: string }[] }> = {
  openai: {
    label: "OpenAI",
    models: [
      { id: "gpt-5.6-luna", label: "GPT-5.6 Luna" },
      { id: "gpt-5.6-terra", label: "GPT-5.6 Terra" },
      { id: "gpt-5.6-sol", label: "GPT-5.6 Sol" },
    ],
  },
  anthropic: {
    label: "Anthropic Claude",
    models: [
      { id: "claude-sonnet-5", label: "Claude Sonnet 5" },
      { id: "claude-opus-5", label: "Claude Opus 5" },
      { id: "claude-fable-5", label: "Claude Fable 5" },
    ],
  },
  groq: {
    label: "Groq",
    models: [
      { id: "llama-3.1-8b-instant", label: "Llama 3.1 8B" },
      { id: "llama-3.3-70b-versatile", label: "Llama 3.3 70B" },
      { id: "openai/gpt-oss-20b", label: "GPT-OSS 20B" },
      { id: "openai/gpt-oss-120b", label: "GPT-OSS 120B" },
      { id: "qwen/qwen3.8-27b", label: "Qwen 3.8 27B" },
    ],
  },
};

const DECISION_MODELS = [
  { id: "~typesafe/jev-latest", label: "Jev Latest" },
  { id: "typesafe/jev-1.13", label: "Jev 1.13" },
];

function Notice({ status, message }: { status: Status; message: string }) {
  if (status !== "success" && status !== "error") return null;
  const Icon = status === "success" ? CheckCircle2 : CircleAlert;
  return <div className={`flex items-center gap-2 rounded-lg p-3 text-sm ${status === "success" ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"}`}><Icon className="size-4 shrink-0" />{message}</div>;
}

function Toast({ status, message, onClose }: { status: Status; message: string; onClose: () => void }) {
  if (status !== "success" && status !== "error") return null;
  const Icon = status === "success" ? CheckCircle2 : CircleAlert;
  return (
    <div role={status === "error" ? "alert" : "status"} className={`toast-enter fixed right-4 top-20 z-[60] flex w-[calc(100%-2rem)] max-w-sm items-start gap-3 rounded-xl border p-4 shadow-xl ${status === "success" ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-red-200 bg-red-50 text-red-800"}`}>
      <Icon className="mt-0.5 size-4 shrink-0" />
      <span className="min-w-0 flex-1 text-sm leading-5">{message}</span>
      <button type="button" onClick={onClose} aria-label="Close notification" className="grid size-6 shrink-0 place-items-center rounded-md opacity-60 hover:bg-black/5 hover:opacity-100">
        <X className="size-4" />
      </button>
    </div>
  );
}

async function connect(path: string, body: object) {
  const response = await fetch(`${API_URL}/api/integrations/${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail ?? "Connection failed");
  return payload;
}

export function DecisionModelIntegrationCard({ initiallyConnected, initialModel }: {
  initiallyConnected: boolean;
  initialModel: string | null;
}) {
  const [open, setOpen] = useState(false);
  const [connected, setConnected] = useState(initiallyConnected);
  const [status, setStatus] = useState<Status>("idle");
  const [message, setMessage] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState(
    DECISION_MODELS.some((item) => item.id === initialModel) ? initialModel! : DECISION_MODELS[0].id
  );

  async function submit(event: FormEvent) {
    event.preventDefault();
    setStatus("testing");
    try {
      await connect("decision-model", { provider: "openrouter", api_key: apiKey, model });
      setConnected(true);
      setApiKey("");
      setMessage("OpenRouter decision model connected successfully.");
      setStatus("success");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Decision model connection failed.");
      setStatus("error");
    }
  }

  return (
    <Card className="p-6 sm:p-7">
      <div className="flex items-start justify-between gap-5">
        <div className="grid size-10 place-items-center rounded-lg border bg-neutral-50"><GitBranch className="size-5 text-neutral-700" /></div>
        {connected && <Badge tone="green"><span className="mr-1.5 size-1.5 rounded-full bg-emerald-500" />Connected</Badge>}
      </div>
      <h2 className="mt-6 text-lg font-semibold">Decision Model</h2>
      <p className="mt-2 max-w-md text-sm leading-6 text-neutral-500">Use an OpenRouter decision model to detect and classify infrastructure incidents.</p>
      <div className="mt-6">
        <Dialog open={open} onOpenChange={(value) => { setOpen(value); if (!value) setStatus("idle"); }} trigger={<Button variant={connected ? "secondary" : "primary"}>{connected ? "Manage" : "Connect"}</Button>} title="Connect Decision Model" description="Choose a decision model and enter your OpenRouter API key.">
          <form className="mt-6 space-y-4" onSubmit={submit}>
            <label className="block text-sm font-medium">Provider
              <select disabled value="openrouter" className="mt-2 h-10 w-full rounded-lg border bg-neutral-50 px-3 text-sm text-neutral-600">
                <option value="openrouter">OpenRouter</option>
              </select>
            </label>
            <label className="block text-sm font-medium">Decision model
              <select value={model} onChange={(event) => setModel(event.target.value)} className="mt-2 h-10 w-full rounded-lg border bg-white px-3 text-sm outline-none focus:border-neutral-500 focus:ring-2 focus:ring-neutral-100">
                {DECISION_MODELS.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
              </select>
            </label>
            <label className="block text-sm font-medium">OpenRouter API key
              <input type="password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} required minLength={10} autoComplete="off" placeholder="sk-or-v1-..." className="mt-2 h-10 w-full rounded-lg border px-3 text-sm outline-none focus:border-neutral-500 focus:ring-2 focus:ring-neutral-100" />
            </label>
            <Notice status={status} message={message} />
            <div className="flex justify-end pt-2"><Button type="submit" disabled={status === "testing"}>{status === "testing" && <Loader2 className="mr-2 size-4 animate-spin" />}{status === "testing" ? "Testing" : "Test and Connect"}</Button></div>
          </form>
        </Dialog>
      </div>
    </Card>
  );
}

export function AIProviderIntegrationCard({ initiallyConnected, initialProvider, initialModel }: {
  initiallyConnected: boolean;
  initialProvider: Provider | null;
  initialModel: string | null;
}) {
  const defaultProvider = initialProvider ?? "openai";
  const defaultModel = PROVIDERS[defaultProvider].models.some((item) => item.id === initialModel)
    ? initialModel!
    : PROVIDERS[defaultProvider].models[0].id;
  const [open, setOpen] = useState(false);
  const [connected, setConnected] = useState(initiallyConnected);
  const [status, setStatus] = useState<Status>("idle");
  const [message, setMessage] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [provider, setProvider] = useState<Provider>(defaultProvider);
  const [model, setModel] = useState(defaultModel);

  function changeProvider(value: Provider) {
    setProvider(value);
    setModel(PROVIDERS[value].models[0].id);
    setStatus("idle");
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setStatus("testing");
    try {
      await connect("ai", { provider, api_key: apiKey, model });
      setConnected(true);
      setApiKey("");
      setMessage(`${PROVIDERS[provider].label} connected successfully.`);
      setStatus("success");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "AI provider connection failed.");
      setStatus("error");
    }
  }

  return (
    <Card className="p-6 sm:p-7">
      <div className="flex items-start justify-between gap-5">
        <div className="grid size-10 place-items-center rounded-lg border bg-neutral-50"><BrainCircuit className="size-5 text-neutral-700" /></div>
        {connected && <Badge tone="green"><span className="mr-1.5 size-1.5 rounded-full bg-emerald-500" />Connected</Badge>}
      </div>
      <h2 className="mt-6 text-lg font-semibold">AI Provider</h2>
      <p className="mt-2 max-w-md text-sm leading-6 text-neutral-500">Choose OpenAI, Anthropic Claude, or Groq to explain incidents and recommend solutions.</p>
      <div className="mt-6">
        <Dialog open={open} onOpenChange={(value) => { setOpen(value); if (!value) setStatus("idle"); }} trigger={<Button variant={connected ? "secondary" : "primary"}>{connected ? "Manage" : "Connect"}</Button>} title="Connect AI Provider" description="Choose a provider and model, then enter that provider's API key.">
          <form className="mt-6 space-y-4" onSubmit={submit}>
            <label className="block text-sm font-medium">Provider
              <select value={provider} onChange={(event) => changeProvider(event.target.value as Provider)} className="mt-2 h-10 w-full rounded-lg border bg-white px-3 text-sm outline-none focus:border-neutral-500 focus:ring-2 focus:ring-neutral-100">
                {Object.entries(PROVIDERS).map(([id, item]) => <option key={id} value={id}>{item.label}</option>)}
              </select>
            </label>
            <label className="block text-sm font-medium">Model
              <select value={model} onChange={(event) => setModel(event.target.value)} className="mt-2 h-10 w-full rounded-lg border bg-white px-3 text-sm outline-none focus:border-neutral-500 focus:ring-2 focus:ring-neutral-100">
                {PROVIDERS[provider].models.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
              </select>
            </label>
            <label className="block text-sm font-medium">{PROVIDERS[provider].label} API key
              <input type="password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} required autoComplete="off" placeholder="Enter API key" className="mt-2 h-10 w-full rounded-lg border px-3 text-sm outline-none focus:border-neutral-500 focus:ring-2 focus:ring-neutral-100" />
            </label>
            <Notice status={status} message={message} />
            <div className="flex justify-end pt-2"><Button type="submit" disabled={status === "testing"}>{status === "testing" && <Loader2 className="mr-2 size-4 animate-spin" />}{status === "testing" ? "Testing" : "Test and Connect"}</Button></div>
          </form>
        </Dialog>
      </div>
    </Card>
  );
}

export function PrometheusIntegrationCard({ initiallyConnected, initialUrl, initialAuthType, initialServiceName }: {
  initiallyConnected: boolean;
  initialUrl: string | null;
  initialAuthType: PrometheusAuthType;
  initialServiceName: string;
}) {
  const [open, setOpen] = useState(false);
  const [connected, setConnected] = useState(initiallyConnected);
  const [status, setStatus] = useState<Status>("idle");
  const [message, setMessage] = useState("");
  const [demoStatus, setDemoStatus] = useState<Status>("idle");
  const [demoMessage, setDemoMessage] = useState("");
  const [url, setUrl] = useState(initialUrl ?? "");
  const [authType, setAuthType] = useState<PrometheusAuthType>(initialAuthType);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState("");
  const [serviceName, setServiceName] = useState(initialServiceName || "prometheus");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setStatus("testing");
    try {
      const payload = await connect("prometheus", {
        url,
        auth_type: authType,
        username: authType === "basic" ? username : null,
        password: authType === "basic" ? password : null,
        token: authType === "bearer" ? token : null,
        service_name: serviceName,
      });
      setConnected(true);
      setPassword("");
      setToken("");
      setMessage(`Prometheus connected. ${payload.targets} target${payload.targets === 1 ? "" : "s"} visible.`);
      setStatus("success");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Prometheus connection failed.");
      setStatus("error");
    }
  }

  async function tryDemo() {
    const metrics = {
      service: `demo-checkout-${Date.now()}`,
      cpu_percent: 96,
      memory_percent: 82,
      latency_ms: 2400,
      error_rate_percent: 18,
      request_rate: 120,
      baseline_cpu_percent: 45,
      baseline_latency_ms: 180,
      baseline_error_rate_percent: 0.4,
      baseline_request_rate: 50,
    };
    setDemoStatus("testing");
    setDemoMessage("");
    try {
      const statusResponse = await fetch(`${API_URL}/api/integrations`, { cache: "no-store" });
      if (!statusResponse.ok) throw new Error("Unable to check integration status.");
      const integrations = await statusResponse.json();
      if (!integrations.decision_model.configured || !integrations.ai.configured || !integrations.slack.configured) {
        throw new Error("Connect the Decision Model, AI Provider, and Slack before running Try Demo.");
      }
      let incident = null;
      for (let check = 0; check < 2; check++) {
        const response = await fetch(`${API_URL}/api/metrics/analyze`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(metrics),
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail ?? "Demo failed.");
        incident = payload.incident;
      }
      if (!incident) throw new Error("No incident was confirmed. Connect the Decision Model and try again.");
      setDemoMessage(`${incident.severity} demo incident created successfully.`);
      setDemoStatus("success");
    } catch (error) {
      setDemoMessage(error instanceof Error ? error.message : "Demo failed.");
      setDemoStatus("error");
    }
  }

  return (
    <Card className="p-6 sm:p-7">
      <div className="flex items-start justify-between gap-5">
        <div className="grid size-10 place-items-center rounded-lg border bg-neutral-50"><Activity className="size-5 text-neutral-700" /></div>
        {connected && <Badge tone="green"><span className="mr-1.5 size-1.5 rounded-full bg-emerald-500" />Connected</Badge>}
      </div>
      <h2 className="mt-6 text-lg font-semibold">Prometheus Monitoring</h2>
      <p className="mt-2 max-w-md text-sm leading-6 text-neutral-500">Connect Prometheus to track CPU, memory, latency, errors, request traffic, and service availability.</p>
      <div className="mt-6 flex flex-wrap gap-2">
        <Dialog open={open} onOpenChange={(value) => { setOpen(value); if (!value) setStatus("idle"); }} trigger={<Button variant={connected ? "secondary" : "primary"}>{connected ? "Manage" : "Connect"}</Button>} title="Connect Prometheus" description="Connect a reachable Prometheus HTTP API using optional authentication.">
          <form className="mt-6 space-y-4" onSubmit={submit}>
            <label className="block text-sm font-medium">Prometheus URL
              <input type="url" value={url} onChange={(event) => setUrl(event.target.value)} required placeholder="https://prometheus.example.com" className="mt-2 h-10 w-full rounded-lg border px-3 text-sm outline-none focus:border-neutral-500 focus:ring-2 focus:ring-neutral-100" />
            </label>
            <label className="block text-sm font-medium">Service name
              <input value={serviceName} onChange={(event) => setServiceName(event.target.value)} required pattern="[a-zA-Z0-9_.:/-]+" placeholder="payment-api" className="mt-2 h-10 w-full rounded-lg border px-3 text-sm outline-none focus:border-neutral-500 focus:ring-2 focus:ring-neutral-100" />
            </label>
            <label className="block text-sm font-medium">Authentication
              <select value={authType} onChange={(event) => setAuthType(event.target.value as PrometheusAuthType)} className="mt-2 h-10 w-full rounded-lg border bg-white px-3 text-sm outline-none focus:border-neutral-500 focus:ring-2 focus:ring-neutral-100">
                <option value="none">None</option>
                <option value="basic">Basic Auth</option>
                <option value="bearer">Bearer Token</option>
              </select>
            </label>
            {authType === "basic" && <>
              <label className="block text-sm font-medium">Username
                <input value={username} onChange={(event) => setUsername(event.target.value)} required autoComplete="username" className="mt-2 h-10 w-full rounded-lg border px-3 text-sm outline-none focus:border-neutral-500 focus:ring-2 focus:ring-neutral-100" />
              </label>
              <label className="block text-sm font-medium">Password
                <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required autoComplete="current-password" className="mt-2 h-10 w-full rounded-lg border px-3 text-sm outline-none focus:border-neutral-500 focus:ring-2 focus:ring-neutral-100" />
              </label>
            </>}
            {authType === "bearer" && <label className="block text-sm font-medium">Bearer token
              <input type="password" value={token} onChange={(event) => setToken(event.target.value)} required autoComplete="off" className="mt-2 h-10 w-full rounded-lg border px-3 text-sm outline-none focus:border-neutral-500 focus:ring-2 focus:ring-neutral-100" />
            </label>}
            <Notice status={status} message={message} />
            <div className="flex justify-end pt-2"><Button type="submit" disabled={status === "testing"}>{status === "testing" && <Loader2 className="mr-2 size-4 animate-spin" />}{status === "testing" ? "Testing" : "Test and Connect"}</Button></div>
          </form>
        </Dialog>
        <Button variant="secondary" onClick={tryDemo} disabled={demoStatus === "testing"}>
          {demoStatus === "testing" && <Loader2 className="mr-2 size-4 animate-spin" />}
          {demoStatus === "testing" ? "Running Demo" : "Try Demo"}
        </Button>
      </div>
      <p className="mt-3 text-xs text-neutral-400">Try Demo requires Decision Model, AI Provider, and Slack.</p>
      <Toast status={demoStatus} message={demoMessage} onClose={() => { setDemoStatus("idle"); setDemoMessage(""); }} />
    </Card>
  );
}

export function SlackIntegrationCard({ initiallyConnected }: { initiallyConnected: boolean }) {
  const [open, setOpen] = useState(false);
  const [connected, setConnected] = useState(initiallyConnected);
  const [status, setStatus] = useState<Status>("idle");
  const [message, setMessage] = useState("");
  const [webhookUrl, setWebhookUrl] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setStatus("testing");
    try {
      await connect("slack", { webhook_url: webhookUrl });
      setConnected(true);
      setWebhookUrl("");
      setMessage("Test alert sent successfully.");
      setStatus("success");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Slack connection failed.");
      setStatus("error");
    }
  }

  return (
    <Card className="p-6 sm:p-7">
      <div className="flex items-start justify-between gap-5">
        <div className="grid size-10 place-items-center rounded-lg border bg-neutral-50"><MessageSquare className="size-5 text-neutral-700" /></div>
        {connected && <Badge tone="green"><span className="mr-1.5 size-1.5 rounded-full bg-emerald-500" />Connected</Badge>}
      </div>
      <h2 className="mt-6 text-lg font-semibold">Slack</h2>
      <p className="mt-2 max-w-md text-sm leading-6 text-neutral-500">Receive proactive incident alerts and AI recommendations in Slack.</p>
      <div className="mt-6">
        <Dialog open={open} onOpenChange={(value) => { setOpen(value); if (!value) setStatus("idle"); }} trigger={<Button variant={connected ? "secondary" : "primary"}>{connected ? "Manage" : "Connect"}</Button>} title="Connect Slack" description="Paste the incoming webhook URL created for your OpsPilot alerts channel.">
          <form className="mt-6 space-y-4" onSubmit={submit}>
            <label className="block text-sm font-medium">Incoming webhook URL
              <input type="password" value={webhookUrl} onChange={(event) => setWebhookUrl(event.target.value)} required autoComplete="off" placeholder="https://hooks.slack.com/services/..." className="mt-2 h-10 w-full rounded-lg border px-3 text-sm outline-none focus:border-neutral-500 focus:ring-2 focus:ring-neutral-100" />
            </label>
            <p className="text-xs leading-5 text-neutral-400">The webhook remains hidden and is stored only in backend memory.</p>
            <Notice status={status} message={message} />
            <div className="flex justify-end pt-2"><Button type="submit" disabled={status === "testing"}>{status === "testing" && <Loader2 className="mr-2 size-4 animate-spin" />}{status === "testing" ? "Testing" : "Test and Connect"}</Button></div>
          </form>
        </Dialog>
      </div>
    </Card>
  );
}
