import React, { useState, useRef } from 'react';
import { ArrowRight, Wand2, Sparkles } from 'lucide-react';

const SUPPORTED_CURRENCIES = ['INR', 'USD', 'EUR', 'GBP', 'CAD', 'AUD', 'AED', 'SGD', 'JPY'];
const EVENT_TYPES = ['Wedding', 'Birthday', 'Community Event'];

function getTodayIsoString() {
  return new Date().toISOString().split('T')[0];
}

function getDefaultDateIsoString() {
  const d = new Date();
  d.setDate(d.getDate() + 30);
  return d.toISOString().split('T')[0];
}

export default function EventForm({ onSubmit, isLoading }) {
  const isSubmittingRef = useRef(false);
  const minDate = getTodayIsoString();


  const [formData, setFormData] = useState({
    event_name: 'Ananya & Kabir Sangeet & Wedding',
    event_type: 'Wedding',
    event_date: getDefaultDateIsoString(),
    location: 'Udaipur, Rajasthan',

    guest_count: 250,
    total_budget: 1200000,
    currency: 'INR',
    theme: 'Royal Rajasthani Heritage',
    additional_preferences: 'Pure vegetarian regional feast, acoustic folk welcome, and eco-friendly floral decor',
  });

  const [errors, setErrors] = useState({});

  const validate = () => {
    const newErrors = {};
    const todayStr = new Date().toISOString().split('T')[0];

    if (!formData.event_name.trim()) {
      newErrors.event_name = 'Event name is required (1-100 characters)';
    } else if (formData.event_name.trim().length > 100) {
      newErrors.event_name = 'Event name must not exceed 100 characters';
    }

    if (!formData.location.trim()) {
      newErrors.location = 'Event location is required';
    }

    if (!formData.event_date) {
      newErrors.event_date = 'Event date is required';
    } else if (formData.event_date < todayStr) {
      newErrors.event_date = 'Event date cannot be in the past';
    }

    const guests = Number(formData.guest_count);
    if (!guests || guests < 1) {
      newErrors.guest_count = 'Guest count must be at least 1';
    } else if (guests > 100000) {
      newErrors.guest_count = 'Guest count must not exceed 100,000';
    }

    const budget = Number(formData.total_budget);
    if (!budget || budget <= 0) {
      newErrors.total_budget = 'Total budget must be greater than zero';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    // Clear field-specific error as user types
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
    if (isLoading || isSubmittingRef.current) return;

    if (!validate()) return;

    isSubmittingRef.current = true;
    try {
      onSubmit({
        ...formData,
        guest_count: Number(formData.guest_count),
        total_budget: Number(formData.total_budget),
      });
    } finally {
      // Release ref lock after submission completes in next tick
      setTimeout(() => {
        isSubmittingRef.current = false;
      }, 500);
    }
  };

  const handlePreFill = (type) => {
    const d = new Date();
    if (type === 'Wedding') {
      d.setDate(d.getDate() + 45);
      setFormData({
        event_name: 'Ananya & Kabir Sangeet & Wedding',
        event_type: 'Wedding',
        event_date: d.toISOString().split('T')[0],
        location: 'Udaipur, Rajasthan',
        guest_count: 250,
        total_budget: 1200000,
        currency: 'INR',
        theme: 'Royal Rajasthani Heritage',
        additional_preferences: 'Pure vegetarian regional feast, acoustic folk welcome, and eco-friendly floral decor',
      });
    } else if (type === 'Birthday') {
      d.setDate(d.getDate() + 14);
      setFormData({
        event_name: "Maya's 30th Neon Glow Birthday Bash",
        event_type: 'Birthday',
        event_date: d.toISOString().split('T')[0],
        location: 'Bangalore Rooftop Lounge',
        guest_count: 50,
        total_budget: 150000,
        currency: 'INR',
        theme: 'Cyberpunk Neon Glow',
        additional_preferences: 'Custom mixology bar, retro arcade games, and dairy-free cake',
      });
    } else if (type === 'Community') {
      d.setDate(d.getDate() + 25);
      setFormData({
        event_name: 'Green Earth Community Fair & Festival',
        event_type: 'Community Event',
        event_date: d.toISOString().split('T')[0],
        location: 'Koramangala Community Park',
        guest_count: 500,
        total_budget: 350000,
        currency: 'INR',
        theme: 'Eco Sustainability & Local Crafts',
        additional_preferences: 'Zero single-use plastic, wheelchair ramp access, live acoustic stage',
      });
    }
    setErrors({});
  };

  return (
    <section id="planner-form" className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 shadow-xl backdrop-blur-md">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-6 border-b border-slate-800/80 gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <Wand2 className="h-4 w-4" />
            </span>
            <h2 className="text-xl font-bold text-white tracking-tight">Event Planning Blueprint</h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Specify celebration requirements. Our engine calculates verified budgets, timeline milestones, and creative aesthetics.
          </p>
        </div>

        {/* Sample presets */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-slate-500 font-medium mr-1">Sample Presets:</span>
          <button
            type="button"
            onClick={() => handlePreFill('Wedding')}
            className="rounded-lg bg-slate-800/80 px-2.5 py-1 text-xs font-medium text-slate-300 hover:bg-slate-700 border border-slate-700/80 transition"
          >
            Wedding
          </button>
          <button
            type="button"
            onClick={() => handlePreFill('Birthday')}
            className="rounded-lg bg-slate-800/80 px-2.5 py-1 text-xs font-medium text-slate-300 hover:bg-slate-700 border border-slate-700/80 transition"
          >
            Birthday
          </button>
          <button
            type="button"
            onClick={() => handlePreFill('Community')}
            className="rounded-lg bg-slate-800/80 px-2.5 py-1 text-xs font-medium text-slate-300 hover:bg-slate-700 border border-slate-700/80 transition"
          >
            Community
          </button>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="mt-6 space-y-6" noValidate>
        {/* Row 1: Event Name & Event Type */}
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          <div className="md:col-span-2">
            <label htmlFor="event_name" className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Event Name <span className="text-rose-400">*</span>
            </label>
            <div className="relative">
              <input
                type="text"
                id="event_name"
                name="event_name"
                value={formData.event_name}
                onChange={handleChange}
                maxLength={100}
                required
                disabled={isLoading}
                aria-invalid={errors.event_name ? 'true' : 'false'}
                aria-describedby={errors.event_name ? 'event_name_error' : undefined}
                placeholder="e.g. Maya & Arjun Wedding Reception"
                className={`w-full rounded-xl border bg-slate-950/60 px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 transition focus:outline-none focus:ring-2 ${
                  errors.event_name
                    ? 'border-rose-500/80 focus:ring-rose-500/30'
                    : 'border-slate-800 focus:border-indigo-500 focus:ring-indigo-500/20'
                }`}
              />
            </div>
            {errors.event_name && (
              <p id="event_name_error" className="mt-1.5 text-xs text-rose-400 font-medium">
                {errors.event_name}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="event_type" className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Event Category <span className="text-rose-400">*</span>
            </label>
            <select
              id="event_type"
              name="event_type"
              value={formData.event_type}
              onChange={handleChange}
              disabled={isLoading}
              className="w-full rounded-xl border border-slate-800 bg-slate-950/60 px-4 py-2.5 text-sm text-slate-100 transition focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
            >
              {EVENT_TYPES.map((type) => (
                <option key={type} value={type} className="bg-slate-900 text-slate-200">
                  {type}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Row 2: Date, Location, Guest Count */}
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
          <div>
            <label htmlFor="event_date" className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Event Date <span className="text-rose-400">*</span>
            </label>
            <div className="relative">
              <input
                type="date"
                id="event_date"
                name="event_date"
                value={formData.event_date}
                onChange={handleChange}
                min={minDate}
                required

                disabled={isLoading}
                aria-invalid={errors.event_date ? 'true' : 'false'}
                aria-describedby={errors.event_date ? 'event_date_error' : undefined}
                className={`w-full rounded-xl border bg-slate-950/60 px-4 py-2.5 text-sm text-slate-100 transition focus:outline-none focus:ring-2 ${
                  errors.event_date
                    ? 'border-rose-500/80 focus:ring-rose-500/30'
                    : 'border-slate-800 focus:border-indigo-500 focus:ring-indigo-500/20'
                }`}
              />
            </div>
            {errors.event_date && (
              <p id="event_date_error" className="mt-1.5 text-xs text-rose-400 font-medium">
                {errors.event_date}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="location" className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Location / City <span className="text-rose-400">*</span>
            </label>
            <div className="relative">
              <input
                type="text"
                id="location"
                name="location"
                value={formData.location}
                onChange={handleChange}
                maxLength={200}
                required
                disabled={isLoading}
                aria-invalid={errors.location ? 'true' : 'false'}
                aria-describedby={errors.location ? 'location_error' : undefined}
                placeholder="e.g. Udaipur, Rajasthan"
                className={`w-full rounded-xl border bg-slate-950/60 px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 transition focus:outline-none focus:ring-2 ${
                  errors.location
                    ? 'border-rose-500/80 focus:ring-rose-500/30'
                    : 'border-slate-800 focus:border-indigo-500 focus:ring-indigo-500/20'
                }`}
              />
            </div>
            {errors.location && (
              <p id="location_error" className="mt-1.5 text-xs text-rose-400 font-medium">
                {errors.location}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="guest_count" className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Guest Count <span className="text-rose-400">*</span>
            </label>
            <div className="relative">
              <input
                type="number"
                id="guest_count"
                name="guest_count"
                value={formData.guest_count}
                onChange={handleChange}
                min={1}
                max={100000}
                required
                disabled={isLoading}
                aria-invalid={errors.guest_count ? 'true' : 'false'}
                aria-describedby={errors.guest_count ? 'guest_count_error' : undefined}
                className={`w-full rounded-xl border bg-slate-950/60 px-4 py-2.5 text-sm text-slate-100 transition focus:outline-none focus:ring-2 ${
                  errors.guest_count
                    ? 'border-rose-500/80 focus:ring-rose-500/30'
                    : 'border-slate-800 focus:border-indigo-500 focus:ring-indigo-500/20'
                }`}
              />
            </div>
            {errors.guest_count && (
              <p id="guest_count_error" className="mt-1.5 text-xs text-rose-400 font-medium">
                {errors.guest_count}
              </p>
            )}
          </div>
        </div>

        {/* Row 3: Budget and Currency */}
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
          <div className="sm:col-span-2">
            <label htmlFor="total_budget" className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Total Budget <span className="text-rose-400">*</span>
            </label>
            <div className="relative">
              <input
                type="number"
                id="total_budget"
                name="total_budget"
                value={formData.total_budget}
                onChange={handleChange}
                min={1}
                step={1}
                required
                disabled={isLoading}
                aria-invalid={errors.total_budget ? 'true' : 'false'}
                aria-describedby={errors.total_budget ? 'total_budget_error' : undefined}
                placeholder="1000000"
                className={`w-full rounded-xl border bg-slate-950/60 px-4 py-2.5 text-sm text-slate-100 transition focus:outline-none focus:ring-2 ${
                  errors.total_budget
                    ? 'border-rose-500/80 focus:ring-rose-500/30'
                    : 'border-slate-800 focus:border-indigo-500 focus:ring-indigo-500/20'
                }`}
              />
            </div>
            {errors.total_budget && (
              <p id="total_budget_error" className="mt-1.5 text-xs text-rose-400 font-medium">
                {errors.total_budget}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="currency" className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Currency
            </label>
            <select
              id="currency"
              name="currency"
              value={formData.currency}
              onChange={handleChange}
              disabled={isLoading}
              className="w-full rounded-xl border border-slate-800 bg-slate-950/60 px-4 py-2.5 text-sm text-slate-100 transition focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
            >
              {SUPPORTED_CURRENCIES.map((cur) => (
                <option key={cur} value={cur} className="bg-slate-900 text-slate-200">
                  {cur}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Row 4: Theme & Additional Preferences */}
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div>
            <label htmlFor="theme" className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Theme / Aesthetic Preference <span className="text-slate-500">(Optional)</span>
            </label>
            <input
              type="text"
              id="theme"
              name="theme"
              value={formData.theme}
              onChange={handleChange}
              maxLength={100}
              disabled={isLoading}
              placeholder="e.g. Royal Rajasthani, Bohemian Garden, Cyberpunk"
              className="w-full rounded-xl border border-slate-800 bg-slate-950/60 px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 transition focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
            />
          </div>

          <div>
            <label htmlFor="additional_preferences" className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Special Preferences & Constraints <span className="text-slate-500">(Optional)</span>
            </label>
            <textarea
              id="additional_preferences"
              name="additional_preferences"
              value={formData.additional_preferences}
              onChange={handleChange}
              maxLength={500}
              rows={1}
              disabled={isLoading}
              placeholder="e.g. Vegetarian catering, disability access, acoustic music"
              className="w-full rounded-xl border border-slate-800 bg-slate-950/60 px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 transition focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 resize-none"
            />
          </div>
        </div>

        {/* Submit Button */}
        <div className="flex items-center justify-end pt-4 border-t border-slate-800/80">
          <button
            type="submit"
            disabled={isLoading}
            id="generate-plan-submit-btn"
            className={`inline-flex items-center gap-2 rounded-xl px-6 py-3 text-sm font-semibold text-white shadow-lg transition ${
              isLoading
                ? 'cursor-not-allowed bg-indigo-500/50'
                : 'bg-indigo-600 hover:bg-indigo-500 shadow-indigo-600/25 hover:shadow-indigo-500/35 active:scale-[0.98]'
            }`}
          >
            {isLoading ? (
              <>
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/20 border-t-white" />
                <span>Synthesizing Celebration Plan...</span>
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                <span>Generate AI Celebration Plan</span>
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </button>
        </div>
      </form>
    </section>
  );
}
