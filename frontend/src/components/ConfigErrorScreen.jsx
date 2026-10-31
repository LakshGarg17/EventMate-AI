import React from 'react';
import { AlertOctagon, Terminal, ExternalLink } from 'lucide-react';

export default function ConfigErrorScreen() {
  return (
    <div className="min-h-screen bg-[#0b0f19] text-slate-100 flex items-center justify-center p-6">
      <div className="w-full max-w-xl rounded-2xl border border-amber-500/30 bg-slate-900/90 p-8 shadow-2xl backdrop-blur-xl">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-400 mb-6">
          <AlertOctagon className="h-7 w-7" />
        </div>

        <h1 className="text-2xl font-bold text-slate-100 tracking-tight">
          Missing Production API Configuration
        </h1>

        <p className="mt-3 text-sm text-slate-300 leading-relaxed">
          The frontend was built for production without a configured backend API URL. In production, the client cannot fall back to <code className="text-amber-300 bg-slate-800 px-1.5 py-0.5 rounded text-xs">localhost:8000</code>.
        </p>

        <div className="mt-6 rounded-xl bg-slate-950 p-4 border border-slate-800 text-xs font-mono text-slate-300">
          <div className="flex items-center gap-2 text-slate-400 mb-2 font-sans font-semibold">
            <Terminal className="h-4 w-4" />
            <span>Required Environment Variable</span>
          </div>
          <p className="text-emerald-400">VITE_API_BASE_URL=https://your-eventmate-api.onrender.com</p>
        </div>

        <div className="mt-6 text-xs text-slate-400 space-y-2">
          <p>
            <strong>How to fix:</strong> Add <code className="text-indigo-300">VITE_API_BASE_URL</code> to your Vercel Project Settings &rarr; Environment Variables, and trigger a redeploy.
          </p>
        </div>
      </div>
    </div>
  );
}

