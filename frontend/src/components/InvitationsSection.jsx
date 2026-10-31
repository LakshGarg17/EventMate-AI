import React, { useState, useEffect, useRef } from 'react';
import { Mail, Copy, Check, Sparkles, RefreshCw, AlertCircle } from 'lucide-react';
import { generateInvitation } from '../services/api';

export default function InvitationsSection({ event }) {
  const [formData, setFormData] = useState({
    event_type: event?.event_type || 'Wedding',
    host_name: '',
    event_date: event?.event_date || '',
    event_time: '18:30',
    location: event?.location || '',
    language: 'English',
    tone: 'Elegant',
    additional_instructions: '',
  });

  const [invitationText, setInvitationText] = useState('');
  const [isEdited, setIsEdited] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [copyStatus, setCopyStatus] = useState(null); // 'copied' | 'failed' | null

  const textareaRef = useRef(null);

  useEffect(() => {
    if (event) {
      setFormData((prev) => ({
        ...prev,
        event_type: event.event_type || 'Wedding',
        event_date: event.event_date || '',
        location: event.location || '',
      }));
    }
  }, [event]);

  const handleGenerate = async (e) => {
    if (e) e.preventDefault();

    if (isEdited && invitationText) {
      const confirmOverwrite = window.confirm(
        'You have edited the invitation text. Generating a new invitation will overwrite your changes. Continue?'
      );
      if (!confirmOverwrite) return;
    }

    setIsLoading(true);
    setError(null);
    setCopyStatus(null);

    try {
      const payload = {
        event_type: formData.event_type,
        host_name: formData.host_name.trim(),
        event_date: formData.event_date,
        event_time: formData.event_time.trim(),
        location: formData.location.trim(),
        language: formData.language,
        tone: formData.tone,
        additional_instructions: formData.additional_instructions.trim() || null,
      };

      const res = await generateInvitation(payload);
      setInvitationText(res.invitation_text);
      setIsEdited(false);
    } catch (err) {
      console.error('Failed to generate invitation:', err);
      setError(err.message || 'Failed to generate invitation copy.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopy = async () => {
    if (!invitationText) return;

    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(invitationText);
      } else {
        // Fallback for environments where clipboard API is restricted
        if (textareaRef.current) {
          textareaRef.current.select();
          document.execCommand('copy');
        }
      }
      setCopyStatus('copied');
      setTimeout(() => setCopyStatus(null), 3000);
    } catch (err) {
      console.warn('Clipboard write failed, using fallback:', err);
      try {
        if (textareaRef.current) {
          textareaRef.current.select();
          document.execCommand('copy');
          setCopyStatus('copied');
          setTimeout(() => setCopyStatus(null), 3000);
        }
      } catch (fallbackErr) {
        setCopyStatus('failed');
        setTimeout(() => setCopyStatus(null), 3000);
      }
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="pb-4 border-b border-slate-800">
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <Mail className="h-5 w-5 text-indigo-400" />
          <span>Celebration Invitation Copywriter</span>
        </h2>
        <p className="text-xs text-slate-400 mt-0.5">
          Generate polished invitation messages in English or authentic Devanagari Hindi with tailored celebration tones.
        </p>
      </div>

      {/* Generator Form & Live Preview Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Form Settings */}
        <form onSubmit={handleGenerate} className="lg:col-span-5 rounded-2xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
          <h3 className="text-sm font-bold text-white pb-2 border-b border-slate-800">
            Invitation Details
          </h3>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Host Name(s) <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Rajesh & Sunita Sharma"
              value={formData.host_name}
              onChange={(e) => setFormData({ ...formData, host_name: e.target.value })}
              className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-white"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Event Date <span className="text-rose-400">*</span>
              </label>
              <input
                type="date"
                required
                value={formData.event_date}
                onChange={(e) => setFormData({ ...formData, event_date: e.target.value })}
                className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-white"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Event Time (24h) <span className="text-rose-400">*</span>
              </label>
              <input
                type="text"
                required
                pattern="^([01]\d|2[0-3]):([0-5]\d)$"
                placeholder="18:30"
                value={formData.event_time}
                onChange={(e) => setFormData({ ...formData, event_time: e.target.value })}
                className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-white"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Location / Venue <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Grand Ballroom, Taj Palace, New Delhi"
              value={formData.location}
              onChange={(e) => setFormData({ ...formData, location: e.target.value })}
              className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-white"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Language
              </label>
              <select
                value={formData.language}
                onChange={(e) => setFormData({ ...formData, language: e.target.value })}
                className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-white"
              >
                <option value="English">English</option>
                <option value="Hindi">Hindi (हिंदी)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Tone
              </label>
              <select
                value={formData.tone}
                onChange={(e) => setFormData({ ...formData, tone: e.target.value })}
                className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-white"
              >
                <option value="Formal">Formal</option>
                <option value="Elegant">Elegant</option>
                <option value="Friendly">Friendly</option>
                <option value="Traditional">Traditional</option>
                <option value="Fun">Fun</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Custom Instructions (Optional)
            </label>
            <textarea
              rows={2}
              maxLength={500}
              placeholder="e.g. Mention cocktail dress code, or add RSVP to Aunt Neeta"
              value={formData.additional_instructions}
              onChange={(e) => setFormData({ ...formData, additional_instructions: e.target.value })}
              className="w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-white resize-none"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading || !formData.host_name.trim() || !formData.location.trim()}
            className="w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold text-xs transition flex items-center justify-center gap-2 shadow-md shadow-indigo-600/20 cursor-pointer"
          >
            {isLoading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            <span>{isLoading ? 'Writing Invitation...' : 'Generate Invitation'}</span>
          </button>
        </form>

        {/* Right Column: Editable Output & Preview Card */}
        <div className="lg:col-span-7 space-y-4">
          {error && (
            <div className="rounded-xl border border-rose-500/30 bg-rose-950/20 p-4 text-xs text-rose-300 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-rose-400 shrink-0" />
                <span>{error}</span>
              </div>
              <button
                type="button"
                onClick={handleGenerate}
                className="px-3 py-1 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 font-semibold text-rose-200"
              >
                Retry
              </button>
            </div>
          )}

          {invitationText ? (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-white">Generated Invitation</span>
                  {isEdited && (
                    <span className="text-[10px] text-amber-400 font-semibold px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/20">
                      Edited locally
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  {/* Copy status live region */}
                  <span aria-live="polite" className="text-xs font-semibold">
                    {copyStatus === 'copied' && (
                      <span className="text-emerald-400 flex items-center gap-1">
                        <Check className="h-3.5 w-3.5" />
                        Copied!
                      </span>
                    )}
                    {copyStatus === 'failed' && (
                      <span className="text-rose-400">Copy failed</span>
                    )}
                  </span>

                  <button
                    type="button"
                    onClick={handleCopy}
                    className="px-3 py-1.5 rounded-xl border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white text-xs font-semibold transition flex items-center gap-1.5 cursor-pointer"
                    aria-label="Copy invitation text to clipboard"
                  >
                    <Copy className="h-3.5 w-3.5" />
                    <span>Copy Text</span>
                  </button>
                </div>
              </div>

              {/* Editable Textarea */}
              <div>
                <label htmlFor="invitation-editor" className="sr-only">Edit Invitation Text</label>
                <textarea
                  id="invitation-editor"
                  ref={textareaRef}
                  rows={8}
                  value={invitationText}
                  onChange={(e) => {
                    setInvitationText(e.target.value);
                    setIsEdited(true);
                  }}
                  lang={formData.language === 'Hindi' ? 'hi' : 'en'}
                  style={{
                    fontFamily:
                      formData.language === 'Hindi'
                        ? "'Noto Sans Devanagari', 'Mangal', 'Segoe UI', system-ui, sans-serif"
                        : 'inherit',
                  }}
                  className="w-full rounded-xl border border-slate-800 bg-slate-950 p-3.5 text-xs sm:text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500/80 transition leading-relaxed"
                />
                <span className="text-[10px] text-slate-500 block pt-1">
                  You can edit the wording above. Edits are local to this session.
                </span>
              </div>

              {/* Rendered Preview Card with Devanagari support */}
              <div className="space-y-2 pt-2 border-t border-slate-800">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                  Invitation Preview
                </span>
                <div
                  lang={formData.language === 'Hindi' ? 'hi' : 'en'}
                  style={{
                    fontFamily:
                      formData.language === 'Hindi'
                        ? "'Noto Sans Devanagari', 'Mangal', 'Segoe UI', system-ui, sans-serif"
                        : 'inherit',
                  }}
                  className="rounded-xl border border-indigo-500/20 bg-slate-950/90 p-6 text-xs sm:text-sm text-slate-100 whitespace-pre-wrap leading-relaxed shadow-inner"
                >
                  {invitationText}
                </div>
              </div>
            </div>
          ) : (
            <div className="h-full min-h-[300px] flex flex-col items-center justify-center text-center p-8 rounded-2xl border border-dashed border-slate-800 bg-slate-900/30 space-y-3">
              <Mail className="h-8 w-8 text-slate-600" />
              <div className="space-y-1">
                <h4 className="text-sm font-semibold text-white">No invitation generated yet</h4>
                <p className="text-xs text-slate-400 max-w-sm">
                  Fill in your host details and click "Generate Invitation" to produce personalized celebration invitation text.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

