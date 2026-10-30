import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Sparkles, Activity, Cpu, LayoutDashboard, PlusCircle } from 'lucide-react';

export default function Navbar({ health }) {
  const location = useLocation();
  const isAiConfigured = health?.ai_configured;

  const isDashboard = location.pathname === '/';
  const isNewEvent = location.pathname === '/events/new';

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800 bg-slate-900/90 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Brand */}
        <div className="flex items-center gap-6">
          <Link to="/" className="flex items-center gap-3 group">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-violet-500 text-white shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg font-bold tracking-tight text-white group-hover:text-indigo-300 transition">
                  EventMate AI
                </span>
                <span className="rounded-md bg-indigo-500/10 px-2 py-0.5 text-xs font-semibold text-indigo-400 border border-indigo-500/20">
                  Day 2
                </span>
              </div>
              <p className="text-[11px] text-slate-400 hidden sm:block">Persistent Celebration & Event Manager</p>
            </div>
          </Link>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-1 pl-4 border-l border-slate-800">
            <Link
              to="/"
              className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                isDashboard
                  ? 'bg-slate-800 text-white font-semibold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
              id="nav-link-dashboard"
            >
              <LayoutDashboard className="h-3.5 w-3.5" />
              <span>Portfolio</span>
            </Link>

            <Link
              to="/events/new"
              className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                isNewEvent
                  ? 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 font-semibold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
              id="nav-link-new-event"
            >
              <PlusCircle className="h-3.5 w-3.5" />
              <span>Plan Event</span>
            </Link>
          </nav>
        </div>

        {/* Status & Actions */}
        <div className="flex items-center gap-3">
          {health ? (
            <div
              className={`flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium border ${
                isAiConfigured
                  ? 'bg-emerald-950/40 text-emerald-300 border-emerald-500/30'
                  : 'bg-amber-950/40 text-amber-300 border-amber-500/30'
              }`}
              title={isAiConfigured ? `Active Model: ${health.model}` : 'Running in Demo Mode (deterministic mock engine)'}
            >
              <Cpu className="h-3.5 w-3.5" />
              <span className="hidden xs:inline">
                {isAiConfigured ? `Gemini Live (${health.model})` : 'Demo Engine'}
              </span>
              <span className={`h-2 w-2 rounded-full ${isAiConfigured ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
            </div>
          ) : (
            <div className="flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium bg-slate-800 text-slate-400 border border-slate-700">
              <Activity className="h-3.5 w-3.5 animate-spin" />
              <span>Connecting...</span>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
