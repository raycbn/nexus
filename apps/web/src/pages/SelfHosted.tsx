import { useEffect, useState } from "react";
import { Server, ShieldCheck, Download } from "lucide-react";
import { api } from "../api/client";

type Status = Awaited<ReturnType<typeof api.getSelfHostedStatus>>;

export function SelfHostedPage() {
  const [status, setStatus] = useState<Status | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    void api.getSelfHostedStatus().then(setStatus).catch((e) => setError(e instanceof Error ? e.message : "Unable to load Self-Hosted status"));
  }, []);
  return <div className="space-y-6 max-w-4xl">
    <div><h1 className="text-2xl font-bold text-nexus-text">Self-Hosted</h1><p className="text-nexus-textMuted">Local AI, release channel and controlled upgrade status.</p></div>
    {error && <p role="alert" className="text-red-300">{error}</p>}
    {status && <>
      <section className="rounded-xl border border-nexus-border bg-nexus-surface p-5">
        <div className="flex items-center gap-3"><Server className="h-5 w-5 text-nexus-primary"/><h2 className="font-semibold">Release channel</h2></div>
        <div className="mt-4 grid gap-3 md:grid-cols-3"><div><span className="text-xs text-nexus-textMuted">Current</span><p className="font-semibold">{status.version}</p></div><div><span className="text-xs text-nexus-textMuted">Latest</span><p className="font-semibold">{status.latest_version}</p></div><div><span className="text-xs text-nexus-textMuted">Channel</span><p className="font-semibold">{status.channel}</p></div></div>
        <p className="mt-3 text-sm text-nexus-textMuted">{status.upgrade_available ? "An upgrade is available for the configured channel." : "This instance is current for the configured channel."}</p>
      </section>
      <section className="rounded-xl border border-nexus-border bg-nexus-surface p-5">
        <div className="flex items-center gap-3"><ShieldCheck className="h-5 w-5 text-nexus-primary"/><h2 className="font-semibold">Local AI and licensing</h2></div>
        <div className="mt-4 grid gap-3 md:grid-cols-2"><div><span className="text-xs text-nexus-textMuted">Local provider</span><p>{status.local_ai.provider} · {status.local_ai.model || "model not configured"}</p></div><div><span className="text-xs text-nexus-textMuted">License mode</span><p>{status.license_mode}</p></div></div>
        <p className="mt-3 text-sm text-nexus-textMuted">Offline-capable local AI: {status.local_ai.offline_capable ? "ready" : "not available"}. License selection remains owner-controlled.</p>
      </section>
      <section className="rounded-xl border border-nexus-border bg-nexus-surface p-5 flex items-center gap-3"><Download className="h-5 w-5 text-nexus-primary"/><div><h2 className="font-semibold">Upgrade workflow</h2><p className="text-sm text-nexus-textMuted">Release validation is automated; applying an upgrade remains an explicit operator action.</p>{status.manifest_url && <a className="btn-secondary mt-3 inline-flex" href={status.manifest_url} target="_blank" rel="noreferrer">Open release manifest</a>}</div></section>
    </>}
  </div>;
}
