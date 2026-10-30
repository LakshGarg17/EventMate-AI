import React, { useState, useEffect } from 'react';
import { X, DollarSign } from 'lucide-react';

export default function ExpenseModal({
  isOpen,
  onClose,
  onSubmit,
  expense = null, // If provided, edit mode
  categories = [],
  currency = 'INR',
  isLoading = false,
}) {
  const isZeroDecimal = ['JPY', 'KRW'].includes(String(currency).toUpperCase());

  const [formData, setFormData] = useState({
    description: '',
    budget_category_id: '',
    estimated_amount: '',
    actual_amount: '',
    payment_status: 'Pending',
    expense_date: '',
    notes: '',
  });

  const [errors, setErrors] = useState({});

  useEffect(() => {
    if (expense) {
      setFormData({
        description: expense.description || '',
        budget_category_id: expense.budget_category_id || '',
        estimated_amount: expense.estimated_amount || '',
        actual_amount: expense.actual_amount !== null && expense.actual_amount !== undefined ? expense.actual_amount : '',
        payment_status: expense.payment_status || 'Pending',
        expense_date: expense.expense_date || '',
        notes: expense.notes || '',
      });
    } else {
      setFormData({
        description: '',
        budget_category_id: categories.length > 0 ? categories[0].id : '',
        estimated_amount: '',
        actual_amount: '',
        payment_status: 'Pending',
        expense_date: '',
        notes: '',
      });
    }
    setErrors({});
  }, [expense, categories, isOpen]);

  if (!isOpen) return null;

  const validate = () => {
    const newErrors = {};

    if (!formData.description.trim()) {
      newErrors.description = 'Description is required';
    }

    if (formData.estimated_amount === '' || formData.estimated_amount === null) {
      newErrors.estimated_amount = 'Estimated amount is required';
    } else {
      const num = Number(formData.estimated_amount);
      if (isNaN(num) || num < 0) {
        newErrors.estimated_amount = 'Estimated amount must be a non-negative number';
      } else {
        const parts = String(formData.estimated_amount).split('.');
        const maxDec = isZeroDecimal ? 0 : 2;
        if (parts.length > 1 && parts[1].length > maxDec) {
          newErrors.estimated_amount = `Amount cannot have more than ${maxDec} decimal places for ${currency}`;
        }
      }
    }

    if (formData.actual_amount !== '' && formData.actual_amount !== null) {
      const num = Number(formData.actual_amount);
      if (isNaN(num) || num < 0) {
        newErrors.actual_amount = 'Actual amount must be a non-negative number';
      } else {
        const parts = String(formData.actual_amount).split('.');
        const maxDec = isZeroDecimal ? 0 : 2;
        if (parts.length > 1 && parts[1].length > maxDec) {
          newErrors.actual_amount = `Amount cannot have more than ${maxDec} decimal places for ${currency}`;
        }
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors((prev) => {
        const updated = { ...prev };
        delete updated[name];
        return updated;
      });
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!validate() || isLoading) return;

    const payload = {
      description: formData.description.trim(),
      budget_category_id: formData.budget_category_id ? formData.budget_category_id : null,
      estimated_amount: String(formData.estimated_amount).trim(),
      actual_amount: formData.actual_amount !== '' ? String(formData.actual_amount).trim() : null,
      payment_status: formData.payment_status,
      expense_date: formData.expense_date ? formData.expense_date : null,
      notes: formData.notes ? formData.notes.trim() : null,
    };

    onSubmit(payload);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={(e) => {
        if (e.target === e.currentTarget && !isLoading) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="expense-modal-title"
        className="relative w-full max-w-lg rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-2xl space-y-6 max-h-[90vh] overflow-y-auto"
      >
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <DollarSign className="h-5 w-5" />
            </div>
            <h3 id="expense-modal-title" className="text-lg font-bold text-white">
              {expense ? 'Edit Expense' : 'Add New Expense'}
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={isLoading}
            className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Description */}
          <div>
            <label htmlFor="expense-description" className="block text-xs font-semibold text-slate-300 mb-1">
              Description <span className="text-rose-400">*</span>
            </label>
            <input
              id="expense-description"
              name="description"
              type="text"
              required
              value={formData.description}
              onChange={handleChange}
              placeholder="e.g. Venue advance deposit"
              aria-invalid={!!errors.description}
              aria-describedby={errors.description ? 'desc-error' : undefined}
              className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition"
            />
            {errors.description && (
              <p id="desc-error" className="mt-1 text-xs text-rose-400">{errors.description}</p>
            )}
          </div>

          {/* Budget Category */}
          <div>
            <label htmlFor="expense-category" className="block text-xs font-semibold text-slate-300 mb-1">
              Budget Category
            </label>
            <select
              id="expense-category"
              name="budget_category_id"
              value={formData.budget_category_id}
              onChange={handleChange}
              className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3.5 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-indigo-500 transition"
            >
              <option value="">(Uncategorized)</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.category_name} ({c.estimated_amount} {currency})
                </option>
              ))}
            </select>
          </div>

          {/* Amounts Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="expense-est-amount" className="block text-xs font-semibold text-slate-300 mb-1">
                Estimated ({currency}) <span className="text-rose-400">*</span>
              </label>
              <input
                id="expense-est-amount"
                name="estimated_amount"
                type="text"
                inputMode="decimal"
                required
                value={formData.estimated_amount}
                onChange={handleChange}
                placeholder="0.00"
                aria-invalid={!!errors.estimated_amount}
                aria-describedby={errors.estimated_amount ? 'est-error' : undefined}
                className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition"
              />
              {errors.estimated_amount && (
                <p id="est-error" className="mt-1 text-xs text-rose-400">{errors.estimated_amount}</p>
              )}
            </div>

            <div>
              <label htmlFor="expense-act-amount" className="block text-xs font-semibold text-slate-300 mb-1">
                Actual Paid ({currency})
              </label>
              <input
                id="expense-act-amount"
                name="actual_amount"
                type="text"
                inputMode="decimal"
                value={formData.actual_amount}
                onChange={handleChange}
                placeholder="Optional"
                aria-invalid={!!errors.actual_amount}
                aria-describedby={errors.actual_amount ? 'act-error' : undefined}
                className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition"
              />
              {errors.actual_amount && (
                <p id="act-error" className="mt-1 text-xs text-rose-400">{errors.actual_amount}</p>
              )}
            </div>
          </div>

          {/* Payment Status & Date Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="expense-status" className="block text-xs font-semibold text-slate-300 mb-1">
                Payment Status
              </label>
              <select
                id="expense-status"
                name="payment_status"
                value={formData.payment_status}
                onChange={handleChange}
                className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3.5 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-indigo-500 transition"
              >
                <option value="Pending">Pending</option>
                <option value="Partial">Partial</option>
                <option value="Paid">Paid</option>
              </select>
            </div>

            <div>
              <label htmlFor="expense-date" className="block text-xs font-semibold text-slate-300 mb-1">
                Expense Date
              </label>
              <input
                id="expense-date"
                name="expense_date"
                type="date"
                value={formData.expense_date}
                onChange={handleChange}
                className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3.5 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-indigo-500 transition"
              />
            </div>
          </div>

          {/* Notes */}
          <div>
            <label htmlFor="expense-notes" className="block text-xs font-semibold text-slate-300 mb-1">
              Notes
            </label>
            <textarea
              id="expense-notes"
              name="notes"
              rows={2}
              value={formData.notes}
              onChange={handleChange}
              placeholder="e.g. Receipt #4092, balance due upon delivery"
              className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition resize-none"
            />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              disabled={isLoading}
              className="px-4 py-2 rounded-xl border border-slate-700 bg-slate-800 text-sm font-medium text-slate-300 hover:text-white transition disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-sm font-semibold text-white shadow-lg shadow-indigo-600/30 transition disabled:opacity-50 flex items-center gap-2"
            >
              {isLoading && (
                <span className="h-4 w-4 rounded-full border-2 border-white/20 border-t-white animate-spin" />
              )}
              <span>{expense ? 'Save Changes' : 'Add Expense'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
