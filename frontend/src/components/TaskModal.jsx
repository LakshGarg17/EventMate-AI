import React, { useState, useEffect } from 'react';
import { X, CheckSquare, AlertCircle } from 'lucide-react';

export default function TaskModal({
  isOpen,
  onClose,
  onSubmit,
  task = null, // If provided, edit mode
  eventDate = null,
  isLoading = false,
}) {
  const [formData, setFormData] = useState({
    title: '',
    category: '',
    priority: 'Medium',
    due_date: '',
    status: 'Pending',
    description: '',
  });

  const [errors, setErrors] = useState({});

  useEffect(() => {
    if (task) {
      setFormData({
        title: task.title || '',
        category: task.category || '',
        priority: task.priority || 'Medium',
        due_date: task.due_date || '',
        status: task.status || 'Pending',
        description: task.description || '',
      });
    } else {
      setFormData({
        title: '',
        category: 'General',
        priority: 'Medium',
        due_date: eventDate || '',
        status: 'Pending',
        description: '',
      });
    }
    setErrors({});
  }, [task, eventDate, isOpen]);

  if (!isOpen) return null;

  const validate = () => {
    const newErrors = {};

    if (!formData.title.trim()) {
      newErrors.title = 'Title is required (1-120 characters)';
    } else if (formData.title.trim().length > 120) {
      newErrors.title = 'Title must not exceed 120 characters';
    }

    if (!formData.category.trim()) {
      newErrors.category = 'Category is required (1-50 characters)';
    } else if (formData.category.trim().length > 50) {
      newErrors.category = 'Category must not exceed 50 characters';
    }

    if (!formData.due_date) {
      newErrors.due_date = 'Due date is required';
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
      title: formData.title.trim(),
      category: formData.category.trim(),
      priority: formData.priority,
      due_date: formData.due_date,
      status: formData.status,
      description: formData.description ? formData.description.trim() : null,
    };

    onSubmit(payload);
  };

  const isAfterEvent = eventDate && formData.due_date && formData.due_date > eventDate;

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
        aria-labelledby="task-modal-title"
        className="relative w-full max-w-lg rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-2xl space-y-6 max-h-[90vh] overflow-y-auto"
      >
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <CheckSquare className="h-5 w-5" />
            </div>
            <h3 id="task-modal-title" className="text-lg font-bold text-white">
              {task ? 'Edit Task' : 'Add New Task'}
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
          {/* Title */}
          <div>
            <label htmlFor="task-title" className="block text-xs font-semibold text-slate-300 mb-1">
              Task Title <span className="text-rose-400">*</span>
            </label>
            <input
              id="task-title"
              name="title"
              type="text"
              required
              value={formData.title}
              onChange={handleChange}
              placeholder="e.g. Confirm sound engineer arrival time"
              aria-invalid={!!errors.title}
              aria-describedby={errors.title ? 'task-title-error' : undefined}
              className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition"
            />
            {errors.title && (
              <p id="task-title-error" className="mt-1 text-xs text-rose-400">{errors.title}</p>
            )}
          </div>

          {/* Category & Priority Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="task-category" className="block text-xs font-semibold text-slate-300 mb-1">
                Category <span className="text-rose-400">*</span>
              </label>
              <input
                id="task-category"
                name="category"
                type="text"
                required
                value={formData.category}
                onChange={handleChange}
                placeholder="e.g. Venue, Catering, Entertainment"
                aria-invalid={!!errors.category}
                aria-describedby={errors.category ? 'task-cat-error' : undefined}
                className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition"
              />
              {errors.category && (
                <p id="task-cat-error" className="mt-1 text-xs text-rose-400">{errors.category}</p>
              )}
            </div>

            <div>
              <label htmlFor="task-priority" className="block text-xs font-semibold text-slate-300 mb-1">
                Priority
              </label>
              <select
                id="task-priority"
                name="priority"
                value={formData.priority}
                onChange={handleChange}
                className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3.5 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-indigo-500 transition"
              >
                <option value="High">High Priority</option>
                <option value="Medium">Medium Priority</option>
                <option value="Low">Low Priority</option>
              </select>
            </div>
          </div>

          {/* Due Date & Status Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="task-due-date" className="block text-xs font-semibold text-slate-300 mb-1">
                Due Date <span className="text-rose-400">*</span>
              </label>
              <input
                id="task-due-date"
                name="due_date"
                type="date"
                required
                value={formData.due_date}
                onChange={handleChange}
                aria-invalid={!!errors.due_date}
                aria-describedby={errors.due_date ? 'task-date-error' : undefined}
                className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3.5 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-indigo-500 transition"
              />
              {errors.due_date && (
                <p id="task-date-error" className="mt-1 text-xs text-rose-400">{errors.due_date}</p>
              )}
              {isAfterEvent && (
                <p className="mt-1 flex items-center gap-1 text-[11px] text-amber-400">
                  <AlertCircle className="h-3 w-3" />
                  <span>Scheduled after the event date ({eventDate})</span>
                </p>
              )}
            </div>

            <div>
              <label htmlFor="task-status" className="block text-xs font-semibold text-slate-300 mb-1">
                Status
              </label>
              <select
                id="task-status"
                name="status"
                value={formData.status}
                onChange={handleChange}
                className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3.5 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-indigo-500 transition"
              >
                <option value="Pending">Pending</option>
                <option value="In Progress">In Progress</option>
                <option value="Completed">Completed</option>
              </select>
            </div>
          </div>

          {/* Description */}
          <div>
            <label htmlFor="task-description" className="block text-xs font-semibold text-slate-300 mb-1">
              Description & Notes
            </label>
            <textarea
              id="task-description"
              name="description"
              rows={3}
              value={formData.description}
              onChange={handleChange}
              placeholder="e.g. Contact lead vendor representative at 555-0192"
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
              <span>{task ? 'Save Changes' : 'Create Task'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
