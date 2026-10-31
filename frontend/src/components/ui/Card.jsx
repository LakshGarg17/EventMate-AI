import React from 'react';

export default function Card({
  children,
  className = '',
  hoverEffect = false,
  ...props
}) {
  return (
    <div
      className={`rounded-2xl border border-slate-800 bg-slate-900/60 p-5 sm:p-6 shadow-xl backdrop-blur-sm ${
        hoverEffect ? 'hover:border-slate-700/80 transition duration-200' : ''
      } ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

