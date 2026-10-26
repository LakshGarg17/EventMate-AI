import React from 'react';
import { Truck, ShieldAlert, CheckCircle, AlertTriangle } from 'lucide-react';

export default function LogisticsAndRisks({ vendors, risks }) {
  const vendorList = vendors || [];
  const riskList = risks || [];

  return (
    <div className="space-y-6">
      {/* Section 1: Vendor Logistics */}
      <section id="logistics-section" className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 shadow-xl backdrop-blur-md">
        <div className="pb-6 border-b border-slate-800/80">
          <div className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <Truck className="h-4 w-4" />
            </span>
            <h3 className="text-xl font-bold text-white tracking-tight">Vendor & Operational Requirements</h3>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Prerequisite supplier specifications, facility load-ins, and technical arrangements.
          </p>
        </div>

        <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
          {vendorList.map((req, idx) => (
            <div
              key={idx}
              className="flex items-start gap-3 rounded-xl border border-slate-800/80 bg-slate-950/40 p-3.5 transition hover:border-slate-700"
            >
              <CheckCircle className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
              <span className="text-xs text-slate-200 leading-snug">{req}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Section 2: Risk Management & Mitigations */}
      <section id="risks-section" className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 shadow-xl backdrop-blur-md">
        <div className="pb-6 border-b border-slate-800/80">
          <div className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <ShieldAlert className="h-4 w-4" />
            </span>
            <h3 className="text-xl font-bold text-white tracking-tight">Risk Assessment & Mitigation Playbook</h3>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Proactive vulnerability forecasting and contingency responses to safeguard execution.
          </p>
        </div>

        <div className="mt-6 space-y-3">
          {riskList.map((r, idx) => {
            const likelihood = r.likelihood || 'Medium';
            const badgeColor = {
              High: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
              Medium: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
              Low: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
            }[likelihood];

            return (
              <div
                key={idx}
                className="rounded-xl border border-slate-800/80 bg-slate-950/50 p-4 transition hover:border-slate-700"
              >
                <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-800/60">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-amber-400" />
                    <h5 className="text-sm font-semibold text-white">{r.risk}</h5>
                  </div>
                  <span className={`rounded-md px-2 py-0.5 text-[10px] font-bold uppercase border ${badgeColor}`}>
                    {likelihood} Likelihood
                  </span>
                </div>
                <div className="mt-2 text-xs text-slate-300">
                  <span className="font-semibold text-slate-400 mr-1.5">Action Plan:</span>
                  <span className="leading-relaxed">{r.mitigation}</span>
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
