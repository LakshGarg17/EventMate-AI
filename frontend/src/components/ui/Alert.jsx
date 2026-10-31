import React from 'react';
import { AlertCircle, AlertTriangle, CheckCircle, Info } from 'lucide-react';

export default function Alert({
  type = 'info',
  title,
  message,
  children,
  className = '',
  action,
}) {
  const configs = {
    info: {
      bg: 'bg-indigo-950/30 border-indigo-500/30 text-indigo-300',
      icon: Info,
    },
    warning: {
      bg: 'bg-amber-950/30 border-amber-500/30 text-amber-300',
      icon: AlertTriangle,
    },
    error: {
      bg: 'bg-rose-950/30 border-rose-500/30 text-rose-300',
      icon: AlertCircle,
    },
    success: {
      bg: 'bg-emerald-950/30 border-emerald-500/30 text-emerald-300',
      icon: CheckCircle,
    },
  };

  const current = configs[type] || configs.info;
  const IconComponent = current.icon;

  return (
    <div
      role="alert"
      className={`flex items-start gap-3 rounded-xl border p-4 text-xs sm:text-sm ${current.bg} ${className}`}
    >
      <IconComponent className="h-5 w-5 shrink-0 mt-0.5" aria-hidden="true" />
      <div className="flex-1 space-y-1">
        {title && <h4 className="font-semibold text-white">{title}</h4>}
        {message && <p>{message}</p>}
        {children}
      </div>
      {action && <div className="shrink-0 ml-2">{action}</div>}
    </div>
  );
}

