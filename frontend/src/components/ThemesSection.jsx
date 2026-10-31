import React, { useState, useEffect } from 'react';
import { Sparkles, Palette, Check, RefreshCw, AlertCircle } from 'lucide-react';
import { recommendThemes, updateEvent } from '../services/api';
import { formatCurrency } from '../utils/formatters';

export default function ThemesSection({ event, onEventUpdated }) {
  const [formData, setFormData] = useState({
    event_type: event?.event_type || 'Wedding',
    total_budget: event?.total_budget || '500000',
    currency: event?.currency || 'INR',
    guest_count: event?.guest_count || 100,
    location: event?.location || '',
    venue_type: '',
    preferred_style: event?.preferred_theme || '',
    additional_preferences: event?.additional_preferences || '',
  });

  const [themes, setThemes] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedThemeName, setSelectedThemeName] = useState(event?.preferred_theme || null);
  const [applyingTheme, setApplyingTheme] = useState(null);
  const [appliedSuccess, setAppliedSuccess] = useState(null);

  useEffect(() => {
    if (event) {
      setFormData((prev) => ({
        ...prev,
        event_type: event.event_type || 'Wedding',
        total_budget: event.total_budget || '500000',
        currency: event.currency || 'INR',
        guest_count: event.guest_count || 100,
        location: event.location || '',
        preferred_style: event.preferred_theme || '',
      }));
      setSelectedThemeName(event.preferred_theme || null);
    }
  }, [event]);

  const handleGenerateThemes = async (e) => {
    if (e) e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const payload = {
        event_type: formData.event_type,
        total_budget: String(formData.total_budget),
        currency: formData.currency,
        guest_count: Number(formData.guest_count),
        location: formData.location.trim(),
        venue_type: formData.venue_type?.trim() || null,
        preferred_style: formData.preferred_style?.trim() || null,
        additional_preferences: formData.additional_preferences?.trim() || null,
        event_id: event?.id || null,
      };

      const res = await recommendThemes(payload);
      setThemes(res.themes || []);
    } catch (err) {
      console.error('Failed to recommend themes:', err);
      setError(err.message || 'Failed to generate theme recommendations.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleUseTheme = async (theme) => {
    if (!event?.id) return;
    setApplyingTheme(theme.name);
    setAppliedSuccess(null);

    try {
      await updateEvent(event.id, {
        preferred_theme: theme.name,
      });
      setSelectedThemeName(theme.name);
      setAppliedSuccess(theme.name);
      setTimeout(() => setAppliedSuccess(null), 3500);

      if (onEventUpdated) {
        await onEventUpdated();
      }
    } catch (err) {
      alert(`Could not save theme preference: ${err.message}`);
    } finally {
      setApplyingTheme(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="pb-4 border-b border-slate-800">
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <Palette className="h-5 w-5 text-indigo-400" />
          <span>Themes & Decoration Styling</span>
        </h2>
        <p className="text-xs text-slate-400 mt-0.5">
          Curate unique design concepts, color swatches, lighting ambiances, and decoration budget shares.
        </p>
      </div>

      {/* Generator Form */}
      <form onSubmit={handleGenerateThemes} className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Event Type <span className="text-rose-400">*</span>
            </label>
            <select
              value={formData.event_type}
              onChange={(e) => setFormData({ ...formData, event_type: e.target.value })}
              className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-white"
            >
              <option value="Wedding">Wedding</option>
              <option value="Birthday">Birthday</option>
              <option value="Community Event">Community Event</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Location <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              required
              value={formData.location}
              onChange={(e) => setFormData({ ...formData, location: e.target.value })}
              placeholder="e.g. Udaipur, Goa, Bengaluru"
              className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-white"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Total Budget ({formData.currency})
            </label>
            <input
              type="text"
              inputMode="decimal"
              value={formData.total_budget}
              onChange={(e) => setFormData({ ...formData, total_budget: e.target.value })}
              className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-white"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Venue Setting
            </label>
            <input
              type="text"
              value={formData.venue_type}
              onChange={(e) => setFormData({ ...formData, venue_type: e.target.value })}
              placeholder="e.g. Beach lawn, Heritage palace"
              className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-white"
            />
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
          <span className="text-[11px] text-slate-400">
            Current Preferred Theme: <strong className="text-indigo-300">{selectedThemeName || 'None selected'}</strong>
          </span>

          <button
            type="submit"
            disabled={isLoading || !formData.location.trim()}
            className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold transition flex items-center justify-center gap-2 shadow-md shadow-indigo-600/20 cursor-pointer"
          >
            {isLoading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            <span>{isLoading ? 'Curating Themes...' : 'Generate Theme Concepts'}</span>
          </button>
        </div>
      </form>

      {/* Success Notification */}
      {appliedSuccess && (
        <div className="flex items-center gap-2 rounded-xl bg-emerald-950/30 border border-emerald-500/30 p-3 text-xs text-emerald-300">
          <Check className="h-4 w-4 shrink-0" />
          <span>Theme "{appliedSuccess}" has been set as your preferred event theme!</span>
        </div>
      )}

      {/* Error View */}
      {error && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-950/20 p-4 text-xs text-rose-300 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-rose-400 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            type="button"
            onClick={handleGenerateThemes}
            className="px-3 py-1.5 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 font-semibold text-rose-200"
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading Skeleton */}
      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-pulse">
          {[1, 2, 3].map((n) => (
            <div key={n} className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 space-y-4">
              <div className="h-5 bg-slate-800 rounded w-2/3" />
              <div className="h-16 bg-slate-800/60 rounded" />
              <div className="flex gap-2">
                {[1, 2, 3, 4].map((c) => (
                  <div key={c} className="h-8 w-12 bg-slate-800 rounded" />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Theme Cards Grid */}
      {!isLoading && themes.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {themes.map((theme, idx) => {
            const isCurrent = selectedThemeName === theme.name;
            const isApplying = applyingTheme === theme.name;

            return (
              <div
                key={idx}
                className={`rounded-2xl border p-5 flex flex-col justify-between space-y-4 transition backdrop-blur-sm ${
                  isCurrent
                    ? 'border-indigo-500/60 bg-indigo-950/10 shadow-lg shadow-indigo-500/10'
                    : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'
                }`}
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="text-base font-bold text-white">{theme.name}</h3>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-500/10 border border-indigo-500/20 text-indigo-300">
                      {theme.budget_share_percent}% Decor
                    </span>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed">{theme.description}</p>

                  {/* Color Palette Swatches with Visible Hex Labels */}
                  <div className="space-y-1.5 pt-1">
                    <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">
                      Color Palette
                    </span>
                    <div className="flex flex-wrap gap-2">
                      {theme.color_palette?.map((col, cIdx) => (
                        <div key={cIdx} className="flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-950/80 px-2 py-1">
                          <span
                            className="h-3.5 w-3.5 rounded-full shrink-0 border border-white/20 shadow-sm"
                            style={{ backgroundColor: col.hex }}
                            title={col.name}
                          />
                          <span className="text-[10px] font-mono font-medium text-slate-300">
                            {col.hex}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Decoration Ideas */}
                  {theme.decoration_ideas?.length > 0 && (
                    <div className="space-y-1 text-xs">
                      <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">
                        Decor Highlights
                      </span>
                      <ul className="list-disc list-inside text-slate-300 space-y-0.5 text-[11px]">
                        {theme.decoration_ideas.slice(0, 3).map((idea, iIdx) => (
                          <li key={iIdx} className="truncate">{idea}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Lighting & Venue */}
                  <div className="space-y-1 text-[11px] text-slate-400 pt-1 border-t border-slate-800/80">
                    <div>
                      <span className="font-semibold text-slate-300">Lighting: </span>
                      <span>{theme.lighting}</span>
                    </div>
                    <div>
                      <span className="font-semibold text-slate-300">Venue Ambiance: </span>
                      <span>{theme.venue_style}</span>
                    </div>
                  </div>

                  {/* Estimated Decoration Budget */}
                  <div className="rounded-xl bg-slate-950/80 border border-slate-800/80 p-2.5 flex items-center justify-between text-xs">
                    <span className="text-slate-400">Estimated Decor Budget:</span>
                    <span className="font-bold text-white">
                      {formatCurrency(theme.estimated_decoration_budget, formData.currency)}
                      <span className="text-[10px] text-slate-500 ml-1 font-normal">(estimate)</span>
                    </span>
                  </div>
                </div>

                {/* Use this theme button */}
                <div className="pt-2">
                  <button
                    type="button"
                    disabled={isCurrent || isApplying}
                    onClick={() => handleUseTheme(theme)}
                    className={`w-full py-2 px-3 rounded-xl text-xs font-semibold transition flex items-center justify-center gap-1.5 cursor-pointer ${
                      isCurrent
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 cursor-default'
                        : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/20'
                    }`}
                  >
                    {isCurrent ? (
                      <>
                        <Check className="h-3.5 w-3.5" />
                        <span>Active Theme</span>
                      </>
                    ) : isApplying ? (
                      <span>Saving...</span>
                    ) : (
                      <span>Use this theme</span>
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && themes.length === 0 && !error && (
        <div className="text-center py-12 rounded-2xl border border-slate-800 bg-slate-900/30 p-8 space-y-3">
          <Palette className="h-8 w-8 text-slate-600 mx-auto" />
          <h3 className="text-sm font-semibold text-white">No theme recommendations generated yet</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            Click "Generate Theme Concepts" above to curate 3 to 5 tailored celebration aesthetics with matching hex palettes.
          </p>
        </div>
      )}
    </div>
  );
}

