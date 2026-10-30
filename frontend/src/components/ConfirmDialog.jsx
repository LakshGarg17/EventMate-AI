import React, { useEffect, useRef } from 'react';
import { AlertTriangle } from 'lucide-react';

export default function ConfirmDialog({
  isOpen,
  title = 'Confirm Action',
  message = 'Are you sure you want to proceed? This action cannot be undone.',
  confirmLabel = 'Delete',
  cancelLabel = 'Cancel',
  isDanger = true,
  isLoading = false,
  onConfirm,
  onCancel,
}) {
  const dialogRef = useRef(null);
  const cancelBtnRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      // Focus cancel button by default for safety on destructive actions
      setTimeout(() => {
        cancelBtnRef.current?.focus();
      }, 50);

      const handleKeyDown = (e) => {
        if (e.key === 'Escape' && !isLoading) {
          e.preventDefault();
          onCancel();
        }
      };

      window.addEventListener('keydown', handleKeyDown);
      return () => window.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, isLoading, onCancel]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={(e) => {
        if (e.target === e.currentTarget && !isLoading) {
          onCancel();
        }
      }}
    >
      <div
        ref={dialogRef}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-description"
        className="relative w-full max-w-md rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-2xl space-y-5"
      >
        <div className="flex items-start gap-4">
          <div
            className={`p-3 rounded-xl border ${
              isDanger
                ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
            }`}
          >
            <AlertTriangle className="h-6 w-6" />
          </div>
          <div className="space-y-1">
            <h3 id="confirm-dialog-title" className="text-lg font-semibold text-white">
              {title}
            </h3>
            <p id="confirm-dialog-description" className="text-sm text-slate-400 leading-relaxed">
              {message}
            </p>
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            ref={cancelBtnRef}
            type="button"
            disabled={isLoading}
            onClick={onCancel}
            className="px-4 py-2.5 rounded-xl border border-slate-700 bg-slate-800/80 hover:bg-slate-700 text-sm font-medium text-slate-300 hover:text-white transition focus:outline-none focus:ring-2 focus:ring-slate-500 disabled:opacity-50"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            disabled={isLoading}
            onClick={onConfirm}
            className={`px-4 py-2.5 rounded-xl text-sm font-medium text-white transition focus:outline-none focus:ring-2 disabled:opacity-50 flex items-center gap-2 ${
              isDanger
                ? 'bg-rose-600 hover:bg-rose-500 focus:ring-rose-500 shadow-lg shadow-rose-950/40'
                : 'bg-indigo-600 hover:bg-indigo-500 focus:ring-indigo-500'
            }`}
          >
            {isLoading && (
              <span className="h-4 w-4 rounded-full border-2 border-white/20 border-t-white animate-spin" />
            )}
            <span>{isLoading ? 'Processing...' : confirmLabel}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
