import React from 'react';
import {
  Calendar,
  Users,
  MapPin,
  DollarSign,
  AlertTriangle,
  Sparkles,
  Cpu,
  Palette,
} from 'lucide-react';
import { formatCurrency, formatDate } from '../utils/formatters';

export default function PlanOverview({ plan }) {
  if (!plan) return null;

  const isDemo = plan.source === 'demo';
  const eventDetails = plan.event_details || {};
  const warnings = plan.warnings || [];

  // Calculate days remaining to event relative to plan generated date
  const eventDateObj = new Date(eventDetails.event_date);
  const baseDateObj = new Date(plan.generated_at || eventDetails.event_date);
  baseDateObj.setHours(0, 0, 0, 0);
  const diffDays = Math.ceil((eventDateObj - baseDateObj) / (1000 * 60 * 60 * 24));


  return (
    <section id="plan-overview" className="space-y-6">
      {/* Top Header Card */}
      <div className="relative overflow-hidden rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900/90 via-slate-900/60 to-slate-950/80 p-6 shadow-xl backdrop-blur-md">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-6 border-b border-slate-800/80">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-2xl font-extrabold tracking-tight text-white">
                {eventDetails.event_name || 'Celebration Plan'}
              </h2>
              {/* Live AI vs Demo Badge */}
              {isDemo ? (
                <span
                  id="demo-mode-badge"
                  className="inline-flex items-center gap-1.5 rounded-full bg-amber-500/10 px-3 py-1 text-xs font-semibold text-amber-400 border border-amber-500/30"
                >
                  <Cpu className="h-3.5 w-3.5" />
                  <span>Demo Mode</span>
                </span>
              ) : (
                <span
                  id="ai-generated-badge"
                  className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-400 border border-emerald-500/30"
                >
                  <Sparkles className="h-3.5 w-3.5" />
                  <span>AI Generated ({plan.model || 'Gemini Flash'})</span>
                </span>
              )}
            </div>
            <p className="mt-1 text-xs text-slate-400">
              Generated on {formatDate(plan.generated_at)} • Plan ID: <span className="font-mono text-slate-300">{plan.id?.slice(0, 8)}</span>
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="rounded-lg bg-indigo-500/10 px-3 py-1.5 text-xs font-semibold text-indigo-400 border border-indigo-500/20">
              {eventDetails.event_type}
            </span>
          </div>
        </div>

        {/* Top-Level Warnings Banner */}
        {warnings.length > 0 && (
          <div className="mt-4 rounded-xl border border-amber-500/30 bg-amber-950/20 p-4" id="warnings-banner">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="text-xs font-semibold text-amber-300 uppercase tracking-wider">
                  Important Notices & Warnings ({warnings.length})
                </p>
                <ul className="list-disc list-inside space-y-0.5 text-xs text-amber-200/90">
                  {warnings.map((warn, i) => (
                    <li key={i}>{warn}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* Narrative Overview */}
        <div className="mt-6">
          <p className="text-sm leading-relaxed text-slate-300">
            {plan.overview}
          </p>
        </div>

        {/* 5-Column Key Metric Cards */}
        <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          <div className="rounded-xl border border-slate-800/80 bg-slate-950/50 p-4">
            <div className="flex items-center gap-2 text-slate-400 mb-1">
              <DollarSign className="h-4 w-4 text-emerald-400" />
              <span className="text-xs font-medium">Budget</span>
            </div>
            <p className="text-lg font-bold text-white">
              {formatCurrency(eventDetails.total_budget, eventDetails.currency)}
            </p>
            <span className="text-[10px] text-slate-500 font-medium uppercase">Fully Allocated</span>
          </div>

          <div className="rounded-xl border border-slate-800/80 bg-slate-950/50 p-4">
            <div className="flex items-center gap-2 text-slate-400 mb-1">
              <Users className="h-4 w-4 text-indigo-400" />
              <span className="text-xs font-medium">Guest Count</span>
            </div>
            <p className="text-lg font-bold text-white">
              {(eventDetails.guest_count || 0).toLocaleString()}
            </p>
            <span className="text-[10px] text-slate-500 font-medium">Confirmed Attendees</span>
          </div>

          <div className="rounded-xl border border-slate-800/80 bg-slate-950/50 p-4">
            <div className="flex items-center gap-2 text-slate-400 mb-1">
              <Calendar className="h-4 w-4 text-cyan-400" />
              <span className="text-xs font-medium">Event Date</span>
            </div>
            <p className="text-lg font-bold text-white">
              {formatDate(eventDetails.event_date)}
            </p>
            <span className={`text-[10px] font-medium ${diffDays < 7 ? 'text-amber-400 font-semibold' : 'text-slate-500'}`}>
              {diffDays > 0 ? `${diffDays} days away` : diffDays === 0 ? 'Today!' : 'Passed'}
            </span>
          </div>

          <div className="rounded-xl border border-slate-800/80 bg-slate-950/50 p-4">
            <div className="flex items-center gap-2 text-slate-400 mb-1">
              <MapPin className="h-4 w-4 text-rose-400" />
              <span className="text-xs font-medium">Location</span>
            </div>
            <p className="text-sm font-bold text-white truncate" title={eventDetails.location}>
              {eventDetails.location}
            </p>
            <span className="text-[10px] text-slate-500 font-medium">Selected Destination</span>
          </div>

          <div className="col-span-2 sm:col-span-1 rounded-xl border border-slate-800/80 bg-slate-950/50 p-4">
            <div className="flex items-center gap-2 text-slate-400 mb-1">
              <Palette className="h-4 w-4 text-violet-400" />
              <span className="text-xs font-medium">Theme</span>
            </div>
            <p className="text-sm font-bold text-white truncate" title={plan.recommended_theme?.name}>
              {plan.recommended_theme?.name || 'Curated Aesthetic'}
            </p>
            <span className="text-[10px] text-slate-500 font-medium">Color Palette Active</span>
          </div>
        </div>
      </div>
    </section>
  );
}
