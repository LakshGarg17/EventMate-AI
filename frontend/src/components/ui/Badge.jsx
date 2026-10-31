import React from 'react';

export default function Badge({
  children,
  variant = 'default',
  size = 'md',
  className = '',
  icon: Icon,
  ...props
}) {
  const variants = {
    default: 'bg-slate-800 text-slate-300 border-slate-700',
    indigo: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
    emerald: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    rose: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
    amber: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    sky: 'bg-sky-500/10 text-sky-400 border-sky-500/20',
    purple: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  };

  const sizes = {
    sm: 'px-2 py-0.5 text-[10px] gap-1',
    md: 'px-2.5 py-1 text-xs gap-1.5',
  };

  return (
    <span
      className={`inline-flex items-center font-semibold rounded-lg border uppercase tracking-wider ${
        variants[variant] || variants.default
      } ${sizes[size] || sizes.md} ${className}`}
      {...props}
    >
      {Icon && <Icon className="h-3 w-3 shrink-0" aria-hidden="true" />}
      {children}
    </span>
  );
}

