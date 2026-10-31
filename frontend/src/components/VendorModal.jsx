import React, { useState, useEffect } from 'react';
import { X, Building2, Star } from 'lucide-react';

const VENDOR_CATEGORIES = [
  'Venue',
  'Catering',
  'Decoration',
  'Photography',
  'Entertainment',
  'Makeup',
  'Transportation',
  'Other',
];

const VENDOR_STATUSES = ['Considering', 'Contacted', 'Shortlisted', 'Selected', 'Rejected'];

export default function VendorModal({
  isOpen,
  onClose,
  onSubmit,
  vendor = null,
  currency = 'INR',
  isLoading = false,
}) {
  const isZeroDecimal = ['JPY', 'KRW'].includes(String(currency).toUpperCase());

  const [formData, setFormData] = useState({
    name: '',
    category: 'Venue',
    status: 'Considering',
    contact_info: '',
    quoted_amount: '',
    rating: '',
    notes: '',
  });

  const [errors, setErrors] = useState({});

  useEffect(() => {
    if (vendor) {
      // Parse rating if stored in notes like "[★ 5]"
      let parsedRating = '';
      let cleanNotes = vendor.notes || '';
      const ratingMatch = cleanNotes.match(/^\[★\s*([1-5])\]\s*/);
      if (ratingMatch) {
        parsedRating = ratingMatch[1];
        cleanNotes = cleanNotes.replace(/^\[★\s*[1-5]\]\s*/, '');
      }

      setFormData({
        name: vendor.name || '',
        category: VENDOR_CATEGORIES.includes(vendor.category) ? vendor.category : 'Other',
        status: vendor.status || 'Considering',
        contact_info: vendor.contact_info || '',
        quoted_amount: vendor.quoted_amount !== null && vendor.quoted_amount !== undefined ? vendor.quoted_amount : '',
        rating: parsedRating,
        notes: cleanNotes,
      });
    } else {
      setFormData({
        name: '',
        category: 'Venue',
        status: 'Considering',
        contact_info: '',
        quoted_amount: '',
        rating: '',
        notes: '',
      });
    }
    setErrors({});
  }, [vendor, isOpen]);

  if (!isOpen) return null;

  const validate = () => {
    const newErrors = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Vendor name is required';
    }

    if (!formData.category) {
      newErrors.category = 'Category is required';
    }

    if (formData.quoted_amount !== '' && formData.quoted_amount !== null) {
      const num = Number(formData.quoted_amount);
      if (isNaN(num) || num < 0) {
        newErrors.quoted_amount = 'Quote amount must be a non-negative number';
      } else {
        const parts = String(formData.quoted_amount).split('.');
        const maxDec = isZeroDecimal ? 0 : 2;
        if (parts.length > 1 && parts[1].length > maxDec) {
          newErrors.quoted_amount = `Amount cannot have more than ${maxDec} decimal places for ${currency}`;
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
    if (!validate()) return;

    let finalNotes = formData.notes.trim();
    if (formData.rating) {
      finalNotes = `[★ ${formData.rating}] ${finalNotes}`.trim();
    }

    const payload = {
      name: formData.name.trim(),
      category: formData.category,
      status: formData.status,
      contact_info: formData.contact_info.trim() || null,
      quoted_amount: formData.quoted_amount !== '' && formData.quoted_amount !== null ? formData.quoted_amount : null,
      notes: finalNotes || null,
    };

    onSubmit(payload);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200"
      role="dialog"
      aria-modal="true"
      aria-labelledby="vendor-modal-title"
    >
      <div className="relative w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl space-y-6 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2.5 text-white">
            <Building2 className="h-5 w-5 text-indigo-400" />
            <h2 id="vendor-modal-title" className="text-lg font-bold">
              {vendor ? 'Edit Vendor' : 'Add New Vendor'}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
            aria-label="Close modal"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Vendor Name */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Vendor / Business Name <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              name="name"
              required
              value={formData.name}
              onChange={handleChange}
              placeholder="e.g. Royal Caterers & Events"
              className={`w-full rounded-xl border bg-slate-950/70 px-3.5 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition ${
                errors.name ? 'border-rose-500/50 focus:ring-rose-500' : 'border-slate-800'
              }`}
            />
            {errors.name && <p className="mt-1 text-xs text-rose-400">{errors.name}</p>}
          </div>

          {/* Category & Status */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Category <span className="text-rose-400">*</span>
              </label>
              <select
                name="category"
                value={formData.category}
                onChange={handleChange}
                className="w-full rounded-xl border border-slate-800 bg-slate-950/70 px-3.5 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
              >
                {VENDOR_CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
              {errors.category && <p className="mt-1 text-xs text-rose-400">{errors.category}</p>}
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Status</label>
              <select
                name="status"
                value={formData.status}
                onChange={handleChange}
                className="w-full rounded-xl border border-slate-800 bg-slate-950/70 px-3.5 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
              >
                {VENDOR_STATUSES.map((st) => (
                  <option key={st} value={st}>
                    {st}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Quote Amount & Rating */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Quotation Amount ({currency})
              </label>
              <input
                type="text"
                name="quoted_amount"
                inputMode="decimal"
                value={formData.quoted_amount}
                onChange={handleChange}
                placeholder="Leave empty if no quote"
                className={`w-full rounded-xl border bg-slate-950/70 px-3.5 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition ${
                  errors.quoted_amount ? 'border-rose-500/50 focus:ring-rose-500' : 'border-slate-800'
                }`}
              />
              {errors.quoted_amount && (
                <p className="mt-1 text-xs text-rose-400">{errors.quoted_amount}</p>
              )}
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Rating (1 to 5 Stars)
              </label>
              <select
                name="rating"
                value={formData.rating}
                onChange={handleChange}
                className="w-full rounded-xl border border-slate-800 bg-slate-950/70 px-3.5 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
              >
                <option value="">No rating</option>
                <option value="5">⭐⭐⭐⭐⭐ (5 Stars)</option>
                <option value="4">⭐⭐⭐⭐ (4 Stars)</option>
                <option value="3">⭐⭐⭐ (3 Stars)</option>
                <option value="2">⭐⭐ (2 Stars)</option>
                <option value="1">⭐ (1 Star)</option>
              </select>
            </div>
          </div>

          {/* Contact Info */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Contact Info (Phone, Email, Website)
            </label>
            <input
              type="text"
              name="contact_info"
              value={formData.contact_info}
              onChange={handleChange}
              placeholder="e.g. +91 9876543210 / contact@vendor.com"
              className="w-full rounded-xl border border-slate-800 bg-slate-950/70 px-3.5 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
            />
          </div>

          {/* Notes */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Notes</label>
            <textarea
              name="notes"
              rows={3}
              value={formData.notes}
              onChange={handleChange}
              placeholder="e.g. Quote includes sound system and lighting. Inquiries pending for setup time."
              className="w-full rounded-xl border border-slate-800 bg-slate-950/70 px-3.5 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition resize-none"
            />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              disabled={isLoading}
              className="px-4 py-2 rounded-xl border border-slate-800 bg-slate-800/50 text-xs font-semibold text-slate-300 hover:bg-slate-800 hover:text-white transition disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white shadow-lg shadow-indigo-600/30 transition disabled:opacity-50 flex items-center gap-2"
            >
              {isLoading && (
                <div className="h-3.5 w-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              )}
              <span>{vendor ? 'Save Changes' : 'Add Vendor'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
