import React from 'react';

export default function Button({
  children,
  type = 'button',
  variant = 'primary',
  size = 'md',
  disabled = false,
  isLoading = false,
  className = '',
  icon: Icon,
  ...props
}) {
  const baseStyles = 'inline-flex items-center justify-center font-medium transition duration-150 rounded-xl focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 cursor-pointer disabled:cursor-not-allowed disabled:opacity-50 min-h-[44px] min-w-[44px]';

  const variants = {
    primary: 'bg-indigo-600 text-white hover:bg-indigo-500 focus-visible:ring-indigo-500 active:bg-indigo-700 shadow-md shadow-indigo-600/20',
    secondary: 'bg-slate-800 text-slate-200 hover:bg-slate-700 hover:text-white border border-slate-700 focus-visible:ring-slate-500',
    outline: 'border border-slate-700 text-slate-300 hover:bg-slate-800/80 hover:text-white focus-visible:ring-slate-500',
    danger: 'bg-rose-600/20 text-rose-300 hover:bg-rose-600/30 border border-rose-500/30 focus-visible:ring-rose-500 hover:text-rose-200',
    ghost: 'text-slate-400 hover:text-white hover:bg-slate-800/50 focus-visible:ring-slate-500',
    emerald: 'bg-emerald-600/20 text-emerald-300 hover:bg-emerald-600/30 border border-emerald-500/30 focus-visible:ring-emerald-500',
  };

  const sizes = {
    sm: 'px-3 py-1.5 text-xs gap-1.5',
    md: 'px-4 py-2 text-xs sm:text-sm gap-2',
    lg: 'px-5 py-2.5 text-sm gap-2.5',
  };

  return (
    <button
      type={type}
      disabled={disabled || isLoading}
      className={`${baseStyles} ${variants[variant] || variants.primary} ${sizes[size] || sizes.md} ${className}`}
      {...props}
    >
      {isLoading ? (
        <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-current" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
        </svg>
      ) : Icon ? (
        <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
      ) : null}
      {children}
    </button>
  );
}

