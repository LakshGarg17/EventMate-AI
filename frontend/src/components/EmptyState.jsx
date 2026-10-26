import React from 'react';
import { Sparkles, PieChart, CalendarCheck, ShieldCheck, ArrowUp } from 'lucide-react';

export default function EmptyState() {
  return (
    <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-8 text-center shadow-xl backdrop-blur-md">
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 shadow-inner">
        <Sparkles className="h-7 w-7" />
      </div>

      <h3 className="mt-4 text-xl font-bold tracking-tight text-white">
        No Active Plan Generated Yet
      </h3>
      <p className="mx-auto mt-2 max-w-lg text-xs leading-relaxed text-slate-400">
        Fill out the celebration blueprint above and click <span className="font-semibold text-indigo-400">"Generate AI Celebration Plan"</span> to synthesize a complete event execution schedule, exact mathematical budget, and curated aesthetics.
      </p>

      {/* Feature Pills */}
      <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3 max-w-2xl mx-auto text-left">
        <div className="rounded-xl border border-slate-800/80 bg-slate-950/40 p-4">
          <div className="flex items-center gap-2 text-indigo-400 mb-1.5">
            <PieChart className="h-4 w-4" />
            <span className="text-xs font-semibold">Reconciled Budget</span>
          </div>
          <p className="text-[11px] text-slate-400 leading-snug">
            Guaranteed 100% exact allocation down to integer currency units with contingency reserve.
          </p>
        </div>

        <div className="rounded-xl border border-slate-800/80 bg-slate-950/40 p-4">
          <div className="flex items-center gap-2 text-emerald-400 mb-1.5">
            <CalendarCheck className="h-4 w-4" />
            <span className="text-xs font-semibold">Validated Timeline</span>
          </div>
          <p className="text-[11px] text-slate-400 leading-snug">
            Real dates with automated overdue detection and preparation milestone safeguards.
          </p>
        </div>

        <div className="rounded-xl border border-slate-800/80 bg-slate-950/40 p-4">
          <div className="flex items-center gap-2 text-amber-400 mb-1.5">
            <ShieldCheck className="h-4 w-4" />
            <span className="text-xs font-semibold">Risk Playbook</span>
          </div>
          <p className="text-[11px] text-slate-400 leading-snug">
            Actionable contingency plans for weather, crowd shifts, noise curfews, and logistics.
          </p>
        </div>
      </div>

      <div className="mt-8 flex items-center justify-center gap-2 text-xs text-slate-500 font-medium">
        <ArrowUp className="h-4 w-4 animate-bounce text-indigo-400" />
        <span>Choose a sample preset or input custom details above to start</span>
      </div>
    </div>
  );
}
