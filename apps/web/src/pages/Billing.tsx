import { useEffect, useState } from "react";
import { CreditCard } from "lucide-react";
import { api } from "../api/client";

type Plan = { key: string; name: string; description: string; monthly_price_cents: number; currency: string; included_units: number };
type Overview = { plan: string; subscription_status: string; current_period_end: string | null; entitlements: { feature_key: string; limit_value: number | null; enabled: boolean }[] };

export function BillingPage() {
  const [plans, setPlans] = useState<Plan[]>([]); const [overview, setOverview] = useState<Overview | null>(null);
  const [subscription, setSubscription] = useState<{ plan: string; status: string; current_period_end: string | null } | null>(null); const [error, setError] = useState<string | null>(null);
  const load = async () => { try { const [p, s, o] = await Promise.all([api.getBillingPlans(), api.getBillingSubscription(), api.getBillingOverview()]); setPlans(p); setSubscription(s); setOverview(o); } catch (e) { setError(e instanceof Error ? e.message : "Unable to load billing"); } };
  useEffect(() => { void load(); }, []);
  const checkout = async (key: string) => { try { const r = await api.createBillingCheckout(key); if (r.checkout_url) window.location.assign(r.checkout_url); } catch (e) { setError(e instanceof Error ? e.message : "Checkout unavailable"); } };
  const portal = async () => { try { const r = await api.openBillingPortal(); if (r.portal_url) window.location.assign(r.portal_url); } catch (e) { setError(e instanceof Error ? e.message : "Billing portal unavailable"); } };
  return <div className="space-y-6"><div><h1 className="text-2xl font-bold text-nexus-text">Billing</h1><p className="text-nexus-textMuted">Plans, subscription status and payment management.</p></div>{error && <p role="alert" className="text-red-300">{error}</p>}
    <div className="rounded-xl border border-nexus-border bg-nexus-surface p-5"><div className="flex items-center gap-3"><CreditCard className="h-5 w-5 text-nexus-primary"/><div><h2 className="font-semibold text-nexus-text">Current subscription</h2><p className="text-sm text-nexus-textMuted">{subscription ? `${subscription.plan} · ${subscription.status}` : "No paid subscription"}</p></div>{subscription && <button onClick={() => void portal()} className="ml-auto btn-secondary">Manage billing</button>}</div></div>
    {overview && <div className="rounded-xl border border-nexus-border bg-nexus-surface p-5"><h2 className="font-semibold text-nexus-text">Plan entitlements</h2><p className="mt-1 text-sm text-nexus-textMuted">{overview.plan} · {overview.subscription_status}</p><div className="mt-4 grid gap-2 md:grid-cols-2">{overview.entitlements.map(e => <div key={e.feature_key} className="flex justify-between text-sm"><span className="text-nexus-textMuted">{e.feature_key}</span><span className="text-nexus-text">{e.limit_value === null ? "Unlimited" : e.limit_value.toLocaleString()}</span></div>)}</div></div>}
    <div className="grid gap-4 md:grid-cols-3">{plans.map(p => <div key={p.key} className="rounded-xl border border-nexus-border bg-nexus-surface p-5"><h2 className="text-lg font-semibold text-nexus-text">{p.name}</h2><p className="mt-2 text-sm text-nexus-textMuted">{p.description}</p><p className="mt-5 text-2xl font-bold text-nexus-text">{p.monthly_price_cents === 0 ? "Free" : `${(p.monthly_price_cents / 100).toFixed(0)} € / month`}</p><p className="mt-2 text-xs text-nexus-textMuted">{p.included_units ? `${p.included_units.toLocaleString()} usage units included` : "Custom limits"}</p>{p.key !== "free" && <button onClick={() => void checkout(p.key)} className="mt-5 btn-primary w-full">Choose {p.name}</button>}</div>)}</div>
  </div>;
}
