import React from 'react';
import { Link } from 'react-router-dom';
import { Compass, Home, CalendarPlus } from 'lucide-react';

export default function NotFoundPage() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center px-4">
      <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 mb-6">
        <Compass className="h-8 w-8 animate-pulse" />
      </div>

      <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-800 px-3 py-1 text-xs font-semibold text-indigo-300 border border-slate-700 mb-4">
        404 Not Found
      </span>

      <h1 className="text-3xl font-extrabold text-slate-100 tracking-tight sm:text-4xl">
        Page Not Found
      </h1>

      <p className="mt-3 max-w-md text-sm text-slate-400 leading-relaxed">
        The celebration or page you are looking for does not exist or may have been moved.
      </p>

      <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
        <Link
          to="/"
          className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-xs font-semibold text-white shadow-lg shadow-indigo-600/25 hover:bg-indigo-500 transition"
        >
          <Home className="h-4 w-4" />
          <span>Back to Dashboard</span>
        </Link>
        <Link
          to="/events/new"
          className="inline-flex items-center gap-2 rounded-xl bg-slate-800/80 px-4 py-2.5 text-xs font-semibold text-slate-200 border border-slate-700 hover:bg-slate-700 transition"
        >
          <CalendarPlus className="h-4 w-4" />
          <span>Plan New Event</span>
        </Link>
      </div>
    </div>
  );
}

