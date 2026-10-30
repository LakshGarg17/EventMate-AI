import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  PlusCircle,
  FileText,
  PieChart,
  ListTodo,
  Sparkles,
  ChevronRight,
  ArrowLeft,
  X,
} from 'lucide-react';

export default function Sidebar({ isMobileOpen, setIsMobileOpen }) {
  const location = useLocation();
  const pathname = location.pathname;

  const isEventDetail = pathname.startsWith('/events/') && pathname !== '/events/new';
  const isNewEvent = pathname === '/events/new';
  const isDashboard = pathname === '/';

  const closeMobile = () => {
    if (setIsMobileOpen) setIsMobileOpen(false);
  };

  return (
    <>
      {/* Mobile Drawer Backdrop */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm lg:hidden"
          onClick={closeMobile}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed top-16 bottom-0 left-0 z-40 w-64 border-r border-slate-800 bg-slate-900/95 transition-transform lg:static lg:block lg:translate-x-0 ${
          isMobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-full flex-col justify-between p-4">
          <div className="space-y-6">
            <div className="flex items-center justify-between lg:hidden pb-2 border-b border-slate-800">
              <span className="text-sm font-semibold text-slate-300">Navigation Menu</span>
              <button
                onClick={closeMobile}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Navigation for Event Detail Page */}
            {isEventDetail ? (
              <div className="space-y-4">
                <Link
                  to="/"
                  onClick={closeMobile}
                  className="flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-indigo-400 transition"
                >
                  <ArrowLeft className="h-3.5 w-3.5" />
                  <span>Back to Portfolio</span>
                </Link>

                <div className="space-y-1">
                  <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 px-3">
                    Event Management
                  </span>

                  <Link
                    to={`${pathname}?tab=overview`}
                    onClick={closeMobile}
                    className="group flex w-full items-center justify-between rounded-xl px-3.5 py-2.5 text-xs font-medium text-slate-300 hover:bg-slate-800/60 hover:text-white transition"
                    id="sidebar-link-overview"
                  >
                    <div className="flex items-center gap-3">
                      <FileText className="h-4 w-4 text-indigo-400" />
                      <span>Overview & Settings</span>
                    </div>
                    <ChevronRight className="h-3 w-3 opacity-0 group-hover:opacity-100 transition" />
                  </Link>

                  <Link
                    to={`${pathname}?tab=budget`}
                    onClick={closeMobile}
                    className="group flex w-full items-center justify-between rounded-xl px-3.5 py-2.5 text-xs font-medium text-slate-300 hover:bg-slate-800/60 hover:text-white transition"
                    id="sidebar-link-budget"
                  >
                    <div className="flex items-center gap-3">
                      <PieChart className="h-4 w-4 text-emerald-400" />
                      <span>Budget & Expenses</span>
                    </div>
                    <ChevronRight className="h-3 w-3 opacity-0 group-hover:opacity-100 transition" />
                  </Link>

                  <Link
                    to={`${pathname}?tab=tasks`}
                    onClick={closeMobile}
                    className="group flex w-full items-center justify-between rounded-xl px-3.5 py-2.5 text-xs font-medium text-slate-300 hover:bg-slate-800/60 hover:text-white transition"
                    id="sidebar-link-tasks"
                  >
                    <div className="flex items-center gap-3">
                      <ListTodo className="h-4 w-4 text-cyan-400" />
                      <span>Timeline & Tasks</span>
                    </div>
                    <ChevronRight className="h-3 w-3 opacity-0 group-hover:opacity-100 transition" />
                  </Link>

                  <Link
                    to={`${pathname}?tab=plan`}
                    onClick={closeMobile}
                    className="group flex w-full items-center justify-between rounded-xl px-3.5 py-2.5 text-xs font-medium text-slate-300 hover:bg-slate-800/60 hover:text-white transition"
                    id="sidebar-link-plan"
                  >
                    <div className="flex items-center gap-3">
                      <Sparkles className="h-4 w-4 text-amber-400" />
                      <span>AI Master Plan</span>
                    </div>
                    <ChevronRight className="h-3 w-3 opacity-0 group-hover:opacity-100 transition" />
                  </Link>
                </div>
              </div>
            ) : isNewEvent ? (
              <div className="space-y-4">
                <Link
                  to="/"
                  onClick={closeMobile}
                  className="flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-indigo-400 transition"
                >
                  <ArrowLeft className="h-3.5 w-3.5" />
                  <span>Back to Portfolio</span>
                </Link>

                <div className="space-y-1">
                  <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 px-3">
                    Plan Creation
                  </span>

                  <button
                    onClick={() => {
                      closeMobile();
                      document.getElementById('planner-form')?.scrollIntoView({ behavior: 'smooth' });
                    }}
                    className="group flex w-full items-center justify-between rounded-xl px-3.5 py-2.5 text-xs font-medium text-slate-300 hover:bg-slate-800/60 hover:text-white transition"
                  >
                    <div className="flex items-center gap-3">
                      <FileText className="h-4 w-4 text-indigo-400" />
                      <span>Event Input Form</span>
                    </div>
                  </button>

                  <button
                    onClick={() => {
                      closeMobile();
                      document.getElementById('generated-plan-preview')?.scrollIntoView({ behavior: 'smooth' });
                    }}
                    className="group flex w-full items-center justify-between rounded-xl px-3.5 py-2.5 text-xs font-medium text-slate-300 hover:bg-slate-800/60 hover:text-white transition"
                  >
                    <div className="flex items-center gap-3">
                      <Sparkles className="h-4 w-4 text-amber-400" />
                      <span>Generated Plan</span>
                    </div>
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 px-3">
                  Main Navigation
                </span>

                <nav className="space-y-1">
                  <Link
                    to="/"
                    onClick={closeMobile}
                    className={`group flex w-full items-center justify-between rounded-xl px-3.5 py-2.5 text-xs font-medium transition ${
                      isDashboard
                        ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 font-semibold'
                        : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                    }`}
                    id="sidebar-link-home"
                  >
                    <div className="flex items-center gap-3">
                      <LayoutDashboard className="h-4 w-4" />
                      <span>Event Portfolio</span>
                    </div>
                    <ChevronRight className={`h-3 w-3 ${isDashboard ? 'text-indigo-400' : 'opacity-0'}`} />
                  </Link>

                  <Link
                    to="/events/new"
                    onClick={closeMobile}
                    className="group flex w-full items-center justify-between rounded-xl px-3.5 py-2.5 text-xs font-medium text-slate-400 hover:bg-slate-800/60 hover:text-slate-200 transition"
                    id="sidebar-link-new"
                  >
                    <div className="flex items-center gap-3">
                      <PlusCircle className="h-4 w-4 text-emerald-400" />
                      <span>Plan New Event</span>
                    </div>
                    <ChevronRight className="h-3 w-3 opacity-0 group-hover:opacity-100 transition" />
                  </Link>
                </nav>
              </div>
            )}
          </div>

          {/* Bottom Card */}
          <div className="rounded-xl border border-slate-800/80 bg-slate-950/40 p-3.5 text-xs space-y-1">
            <p className="font-semibold text-slate-300">EventMate AI Engine</p>
            <p className="text-[11px] leading-relaxed text-slate-400">
              Persistent SQLite storage, deterministic math, and deadline tracking.
            </p>
          </div>
        </div>
      </aside>
    </>
  );
}
