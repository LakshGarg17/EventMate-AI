import React from 'react';

export default function Select({
  label,
  id,
  options = [],
  error,
  helperText,
  required = false,
  className = '',
  children,
  ...props
}) {
  return (
    <div className="space-y-1.5 w-full">
      {label && (
        <label htmlFor={id} className="block text-xs font-semibold text-slate-300">
          {label} {required && <span className="text-rose-400">*</span>}
        </label>
      )}
      <select
        id={id}
        className={`w-full rounded-xl border bg-slate-900/80 px-3.5 py-2.5 text-xs sm:text-sm text-slate-100 transition focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-1 focus-visible:ring-offset-slate-950 min-h-[44px] ${
          error
            ? 'border-rose-500/60 focus-visible:ring-rose-500'
            : 'border-slate-800 focus:border-indigo-500/80 focus-visible:ring-indigo-500'
        } ${className}`}
        {...props}
      >
        {children
          ? children
          : options.map((opt) => {
              const val = typeof opt === 'object' ? opt.value : opt;
              const lbl = typeof opt === 'object' ? opt.label : opt;
              return (
                <option key={val} value={val} className="bg-slate-900 text-slate-100">
                  {lbl}
                </option>
              );
            })}
      </select>
      {error ? (
        <p className="text-[11px] text-rose-400" role="alert">{error}</p>
      ) : helperText ? (
        <p className="text-[11px] text-slate-400">{helperText}</p>
      ) : null}
    </div>
  );
}

