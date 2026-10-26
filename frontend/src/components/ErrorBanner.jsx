import React from 'react';
import { AlertCircle, RefreshCw, X } from 'lucide-react';

export default function ErrorBanner({ message, onRetry, onDismiss }) {
  if (!message) return null;

  return (
    <div
      role="alert"
      id="error-banner"
      className="rounded-2xl border border-rose-500/40 bg-rose-950/30 p-5 shadow-xl backdrop-blur-md"
    >
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
          <div>
            <h4 className="text-sm font-bold text-rose-300">Plan Generation Interrupted</h4>
            <p className="mt-1 text-xs text-rose-200/90 leading-relaxed max-w-2xl">{message}</p>
          </div>
        </div>

        <div className="flex items-center gap-2 self-end sm:self-center">
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="inline-flex items-center gap-1.5 rounded-lg bg-rose-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-rose-500 shadow-sm transition"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              <span>Retry</span>
            </button>
          )}
          {onDismiss && (
            <button
              type="button"
              onClick={onDismiss}
              className="rounded-lg p-1.5 text-rose-400 hover:bg-rose-900/40 hover:text-white transition"
              aria-label="Dismiss error"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
