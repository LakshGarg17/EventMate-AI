import React from 'react';
import {
  FileText,
  PieChart,
  CalendarCheck,
  Palette,
  Truck,
  ShieldAlert,
  ChevronRight,
  X,
  Sparkles,

} from 'lucide-react';

export default function Sidebar({ hasPlan, activeSection, onSelectSection, isMobileOpen, setIsMobileOpen }) {
  const navItems = [
    { id: 'planner-form', label: 'Event Details', icon: FileText, alwaysShow: true },
    { id: 'plan-overview', label: 'Executive Overview', icon: Sparkles, requiresPlan: true },
    { id: 'budget-section', label: 'Budget Allocation', icon: PieChart, requiresPlan: true },
    { id: 'timeline-section', label: 'Timeline & Checklist', icon: CalendarCheck, requiresPlan: true },
    { id: 'creative-section', label: 'Themes & Aesthetics', icon: Palette, requiresPlan: true },
    { id: 'logistics-section', label: 'Vendors & Logistics', icon: Truck, requiresPlan: true },
    { id: 'risks-section', label: 'Risk Analysis', icon: ShieldAlert, requiresPlan: true },
  ];

  const handleNavClick = (id) => {
    onSelectSection(id);
    if (setIsMobileOpen) {
      setIsMobileOpen(false);
    }
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <>
      {/* Mobile Drawer Backdrop */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm lg:hidden"
          onClick={() => setIsMobileOpen(false)}
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
                onClick={() => setIsMobileOpen(false)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <nav className="space-y-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isDisabled = item.requiresPlan && !hasPlan;
                const isActive = activeSection === item.id;

                return (
                  <button
                    key={item.id}
                    disabled={isDisabled}
                    onClick={() => handleNavClick(item.id)}
                    className={`group flex w-full items-center justify-between rounded-xl px-3.5 py-2.5 text-xs font-medium transition ${
                      isDisabled
                        ? 'cursor-not-allowed opacity-40 text-slate-500'
                        : isActive
                        ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 font-semibold'
                        : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                    }`}
                    id={`sidebar-link-${item.id}`}
                  >
                    <div className="flex items-center gap-3">
                      <Icon className={`h-4 w-4 ${isActive ? 'text-indigo-400' : 'text-slate-500 group-hover:text-slate-300'}`} />
                      <span>{item.label}</span>
                    </div>
                    {isDisabled ? (
                      <span className="text-[10px] uppercase text-slate-600 font-mono">locked</span>
                    ) : (
                      <ChevronRight className={`h-3 w-3 opacity-0 transition group-hover:opacity-100 ${isActive ? 'opacity-100 text-indigo-400' : ''}`} />
                    )}
                  </button>
                );
              })}
            </nav>
          </div>

          <div className="rounded-xl border border-slate-800/80 bg-slate-950/40 p-3 text-xs text-slate-400">
            <p className="font-semibold text-slate-300 mb-1">Target Milestone</p>
            <p className="text-[11px] leading-relaxed text-slate-400">
              EventMate AI Day 1: Autonomous Plan Generation Engine.
            </p>
          </div>
        </div>
      </aside>
    </>
  );
}
