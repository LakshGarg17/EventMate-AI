import React from 'react';

export default function Input({
  label,
  id,
  error,
  helperText,
  required = false,
  className = '',
  ...props
}) {
  return (
    <div className="space-y-1.5 w-full">
      {label && (
        <label htmlFor={id} className="block text-xs font-semibold text-slate-300">
          {label} {required && <span className="text-rose-400">*</span>}
        </label>
      )}
      <input
        id={id}
        className={`w-full rounded-xl border bg-slate-900/80 px-3.5 py-2.5 text-xs sm:text-sm text-slate-100 placeholder-slate-500 transition focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-1 focus-visible:ring-offset-slate-950 min-h-[44px] ${
          error
            ? 'border-rose-500/60 focus-visible:ring-rose-500'
            : 'border-slate-800 focus:border-indigo-500/80 focus-visible:ring-indigo-500'
        } ${className}`}
        {...props}
      />
      {error ? (
        <p className="text-[11px] text-rose-400" role="alert">{error}</p>
      ) : helperText ? (
        <p className="text-[11px] text-slate-400">{helperText}</p>
      ) : null}
    </div>
  );
}

