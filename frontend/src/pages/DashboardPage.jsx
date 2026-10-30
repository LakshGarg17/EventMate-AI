import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Calendar,
  Users,
  MapPin,
  CheckCircle2,
  AlertCircle,
  Clock,
  ArrowRight,
  PlusCircle,
  RefreshCw,
  Sparkles,
  Search,
} from 'lucide-react';
import { listEvents } from '../services/api';
import { formatCurrency, formatDate } from '../utils/formatters';

export default function DashboardPage() {
  const [events, setEvents] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState('ALL');

  const fetchEventsData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await listEvents();
      setEvents(data || []);
    } catch (err) {
      console.error('Failed to load events:', err);
      setError(err.message || 'Unable to load events from the server.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchEventsData();
  }, []);

  // Aggregated metrics across events (counts only; no cross-currency sums)
  const totalEvents = events.length;
  const totalTasks = events.reduce((sum, ev) => sum + (ev.task_counts?.total || ev.total_tasks || 0), 0);
  const completedTasks = events.reduce((sum, ev) => sum + (ev.task_counts?.completed || ev.completed_tasks || 0), 0);
  const overdueTasks = events.reduce((sum, ev) => sum + (ev.task_counts?.overdue || ev.overdue_tasks || 0), 0);

  // Filtered events
  const filteredEvents = events.filter((ev) => {
    const matchesSearch =
      ev.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ev.location.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = filterType === 'ALL' || ev.event_type === filterType;
    return matchesSearch && matchesType;
  });

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Page Title & Action */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
            Celebration Portfolio
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Persistent event tracking, deterministic budget allocation, and milestone timelines.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchEventsData}
            disabled={isLoading}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/80 px-3.5 py-2.5 text-xs font-semibold text-slate-300 hover:bg-slate-800 hover:text-white transition disabled:opacity-50"
            title="Refresh events"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">Refresh</span>
          </button>
          <Link
            to="/events/new"
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 px-4 py-2.5 text-xs font-semibold text-white shadow-lg shadow-indigo-600/30 transition"
            id="create-event-top-btn"
          >
            <PlusCircle className="h-4 w-4" />
            <span>Plan New Event</span>
          </Link>
        </div>
      </div>

      {/* Overview Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-5 shadow-lg backdrop-blur-sm">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Total Events</span>
            <Sparkles className="h-4 w-4 text-indigo-400" />
          </div>
          <p className="text-2xl sm:text-3xl font-black text-white">{totalEvents}</p>
          <span className="text-[11px] text-slate-500 font-medium">Saved in SQLite</span>
        </div>

        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-5 shadow-lg backdrop-blur-sm">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Total Tasks</span>
            <Clock className="h-4 w-4 text-cyan-400" />
          </div>
          <p className="text-2xl sm:text-3xl font-black text-white">{totalTasks}</p>
          <span className="text-[11px] text-slate-500 font-medium">Across all events</span>
        </div>

        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-5 shadow-lg backdrop-blur-sm">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Completed</span>
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          </div>
          <p className="text-2xl sm:text-3xl font-black text-emerald-400">{completedTasks}</p>
          <span className="text-[11px] text-slate-500 font-medium">
            {totalTasks > 0 ? `${Math.round((completedTasks / totalTasks) * 100)}% overall completion` : '0%'}
          </span>
        </div>

        <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-5 shadow-lg backdrop-blur-sm">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Overdue</span>
            <AlertCircle className="h-4 w-4 text-rose-400" />
          </div>
          <p className={`text-2xl sm:text-3xl font-black ${overdueTasks > 0 ? 'text-rose-400' : 'text-slate-400'}`}>
            {overdueTasks}
          </p>
          <span className="text-[11px] text-slate-500 font-medium">Requires attention</span>
        </div>
      </div>

      {/* Search & Filter Toolbar */}
      {events.length > 0 && (
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-slate-900/40 border border-slate-800/80 p-3 rounded-2xl">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search by event name or location..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs sm:text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition"
            />
          </div>

          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
            {['ALL', 'Wedding', 'Birthday', 'Community Event'].map((type) => (
              <button
                key={type}
                onClick={() => setFilterType(type)}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition ${
                  filterType === type
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'bg-slate-800/80 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                {type === 'ALL' ? 'All Types' : type}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Main Content Area */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4 animate-pulse"
            >
              <div className="h-5 bg-slate-800 rounded w-2/3" />
              <div className="h-4 bg-slate-800/60 rounded w-1/2" />
              <div className="h-16 bg-slate-950 rounded-xl" />
              <div className="h-4 bg-slate-800 rounded w-full" />
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="rounded-2xl border border-rose-500/30 bg-rose-950/20 p-8 text-center space-y-4">
          <AlertCircle className="h-10 w-10 text-rose-400 mx-auto" />
          <div className="space-y-1">
            <h3 className="text-lg font-bold text-white">Error Loading Events</h3>
            <p className="text-sm text-rose-300/90 max-w-md mx-auto">{error}</p>
          </div>
          <button
            onClick={fetchEventsData}
            className="px-5 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-xs font-semibold text-white shadow-lg transition"
          >
            Retry Connection
          </button>
        </div>
      ) : events.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-slate-800 bg-gradient-to-b from-slate-900/40 to-slate-950/80 p-12 text-center space-y-6">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-600/10 text-indigo-400 border border-indigo-500/20 mx-auto shadow-inner">
            <Calendar className="h-8 w-8" />
          </div>
          <div className="space-y-2 max-w-md mx-auto">
            <h3 className="text-xl font-extrabold text-white">No Saved Events Yet</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Generate an end-to-end celebration plan with Gemini AI or build your custom event from scratch.
            </p>
          </div>
          <div>
            <Link
              to="/events/new"
              className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 px-6 py-3 text-sm font-semibold text-white shadow-xl shadow-indigo-600/30 transition"
              id="empty-state-create-btn"
            >
              <PlusCircle className="h-5 w-5" />
              <span>Create Your First Event</span>
            </Link>
          </div>
        </div>
      ) : filteredEvents.length === 0 ? (
        <div className="p-12 text-center text-slate-400 space-y-2 border border-slate-800 rounded-2xl bg-slate-900/30">
          <p className="text-base font-semibold text-slate-300">No events matched your search.</p>
          <p className="text-xs">Try adjusting your search query or filter criteria.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredEvents.map((ev) => {
            const utilization = Number(ev.budget_utilization_percent) || 0;
            const progress = Number(ev.task_progress_percent) || 0;
            const completedCount = ev.task_counts?.completed || ev.completed_tasks || 0;
            const totalCount = ev.task_counts?.total || ev.total_tasks || 0;
            const overdueCount = ev.task_counts?.overdue || ev.overdue_tasks || 0;

            const isOverBudget = utilization > 100;
            const utilizationColor = isOverBudget
              ? 'bg-rose-500'
              : utilization > 80
              ? 'bg-amber-400'
              : 'bg-emerald-400';

            return (
              <div
                key={ev.id}
                className="group relative flex flex-col justify-between rounded-2xl border border-slate-800 bg-slate-900/70 p-6 shadow-xl hover:border-slate-700 hover:bg-slate-900 transition-all duration-200"
              >
                <div className="space-y-4">
                  {/* Card Header */}
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1 min-w-0">
                      <span className="inline-block rounded-md bg-indigo-500/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-indigo-400 border border-indigo-500/20">
                        {ev.event_type}
                      </span>
                      <h3
                        className="text-lg font-bold text-white truncate group-hover:text-indigo-300 transition"
                        title={ev.name}
                      >
                        {ev.name}
                      </h3>
                    </div>
                  </div>

                  {/* Metadata Chips */}
                  <div className="grid grid-cols-2 gap-2 text-xs text-slate-300">
                    <div className="flex items-center gap-1.5 truncate">
                      <Calendar className="h-3.5 w-3.5 text-cyan-400 shrink-0" />
                      <span>{formatDate(ev.event_date)}</span>
                    </div>
                    <div className="flex items-center gap-1.5 truncate">
                      <Users className="h-3.5 w-3.5 text-indigo-400 shrink-0" />
                      <span>{(ev.guest_count || 0).toLocaleString()} guests</span>
                    </div>
                    <div className="flex items-center gap-1.5 col-span-2 truncate" title={ev.location}>
                      <MapPin className="h-3.5 w-3.5 text-rose-400 shrink-0" />
                      <span className="truncate">{ev.location}</span>
                    </div>
                  </div>

                  {/* Financial & Metric Bars */}
                  <div className="space-y-3 pt-3 border-t border-slate-800/80">
                    {/* Budget utilization */}
                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-400">Budget Spent</span>
                        <span className="font-semibold text-slate-200">
                          {formatCurrency(ev.total_actual, ev.currency)} / {formatCurrency(ev.total_budget, ev.currency)}
                        </span>
                      </div>
                      <div className="h-2 w-full rounded-full bg-slate-950 overflow-hidden border border-slate-800/80">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${utilizationColor}`}
                          style={{ width: `${Math.min(utilization, 100)}%` }}
                        />
                      </div>
                      <div className="flex items-center justify-between text-[10px] text-slate-500 font-medium">
                        <span>{utilization}% utilized</span>
                        {isOverBudget && <span className="text-rose-400 font-semibold">Over Budget!</span>}
                      </div>
                    </div>

                    {/* Task progress */}
                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-400">Task Milestones</span>
                        <span className="font-semibold text-slate-200">
                          {completedCount} / {totalCount} done
                        </span>
                      </div>
                      <div className="h-2 w-full rounded-full bg-slate-950 overflow-hidden border border-slate-800/80">
                        <div
                          className="h-full rounded-full bg-indigo-500 transition-all duration-500"
                          style={{ width: `${Math.min(progress, 100)}%` }}
                        />
                      </div>
                      <div className="flex items-center justify-between text-[10px] text-slate-500 font-medium">
                        <span>{progress}% complete</span>
                        {overdueCount > 0 && (
                          <span className="text-rose-400 font-semibold">{overdueCount} overdue</span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Next Deadline Banner */}
                  <div className="rounded-xl bg-slate-950/60 border border-slate-800/80 p-2.5 text-xs">
                    <div className="flex items-center gap-1.5 text-slate-400 mb-0.5">
                      <Clock className="h-3 w-3 text-amber-400" />
                      <span className="text-[10px] uppercase font-bold text-slate-500">Next Deadline</span>
                    </div>
                    {ev.next_deadline ? (
                      <p className="text-slate-200 font-medium truncate">
                        {ev.next_deadline.title}{' '}
                        <span className="text-amber-400">({formatDate(ev.next_deadline.due_date)})</span>
                      </p>
                    ) : (
                      <p className="text-slate-500 italic text-[11px]">No pending deadlines</p>
                    )}
                  </div>
                </div>

                {/* Card Action Link */}
                <div className="pt-5 mt-4 border-t border-slate-800/60">
                  <Link
                    to={`/events/${ev.id}`}
                    className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-slate-800/80 hover:bg-indigo-600 px-4 py-2.5 text-xs font-semibold text-slate-200 hover:text-white border border-slate-700/80 hover:border-indigo-500 transition shadow-sm group/btn"
                    id={`view-event-${ev.id}`}
                  >
                    <span>Manage Event & Budget</span>
                    <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover/btn:translate-x-1" />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
