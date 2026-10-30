import React, { useState, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  Bookmark,
  CheckCircle,
  AlertCircle,
  ArrowLeft,
  Sparkles,
  RefreshCw,
  AlertTriangle,
} from 'lucide-react';
import EventForm from '../components/EventForm';
import PlanOverview from '../components/PlanOverview';
import BudgetSection from '../components/BudgetSection';
import TimelineSection from '../components/TimelineSection';
import CreativeSection from '../components/CreativeSection';
import LogisticsAndRisks from '../components/LogisticsAndRisks';
import LoadingSkeleton from '../components/LoadingSkeleton';
import ErrorBanner from '../components/ErrorBanner';
import { generateEventPlan, createEvent } from '../services/api';

export default function NewEventPage() {
  const navigate = useNavigate();

  const [plan, setPlan] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationError, setGenerationError] = useState(null);

  const [isSaving, setIsSaving] = useState(false);
  const [isSaved, setIsSaved] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [saveWarnings, setSaveWarnings] = useState([]);

  // Guards against double clicks on save
  const isSavingRef = useRef(false);
  const lastGenerationPayloadRef = useRef(null);

  const handleGeneratePlan = async (payload) => {
    lastGenerationPayloadRef.current = payload;
    setIsGenerating(true);
    setGenerationError(null);
    setSaveError(null);
    setIsSaved(false);
    setSaveWarnings([]);

    try {
      const generatedPlan = await generateEventPlan(payload);
      setPlan(generatedPlan);

      setTimeout(() => {
        const el = document.getElementById('generated-plan-preview');
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 100);
    } catch (err) {
      console.error('Plan generation failed:', err);
      setGenerationError(err.message || 'An error occurred during plan generation.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSaveEvent = async () => {
    if (!plan || isSavingRef.current || isSaved) return;

    isSavingRef.current = true;
    setIsSaving(true);
    setSaveError(null);

    const eventDetails = plan.event_details || {};
    const savePayload = {
      name: eventDetails.event_name || 'My Event',
      event_type: eventDetails.event_type || 'Community Event',
      event_date: eventDetails.event_date,
      location: eventDetails.location || 'Main Venue',
      guest_count: Number(eventDetails.guest_count) || 50,
      total_budget: String(eventDetails.total_budget || 10000),
      currency: eventDetails.currency || 'INR',
      preferred_theme: eventDetails.theme || null,
      additional_preferences: eventDetails.additional_preferences || null,
      generated_plan: plan,
    };

    try {
      const savedEvent = await createEvent(savePayload);
      setIsSaved(true);

      if (savedEvent.warnings && savedEvent.warnings.length > 0) {
        setSaveWarnings(savedEvent.warnings);
      }

      // Navigate to the saved event details page
      setTimeout(() => {
        navigate(`/events/${savedEvent.id}`);
      }, 600);
    } catch (err) {
      console.error('Save event failed:', err);
      setSaveError(err.message || 'Failed to save event to database. Please retry.');
    } finally {
      setIsSaving(false);
      isSavingRef.current = false;
    }
  };

  const handleReset = () => {
    setPlan(null);
    setGenerationError(null);
    setSaveError(null);
    setIsSaved(false);
    setSaveWarnings([]);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Breadcrumb Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <Link
            to="/"
            className="p-2 rounded-xl border border-slate-800 bg-slate-900 text-slate-400 hover:text-white hover:bg-slate-800 transition"
            title="Back to Dashboard"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <h1 className="text-2xl font-extrabold tracking-tight text-white">
              AI Event Designer
            </h1>
            <p className="text-xs text-slate-400">
              Generate an end-to-end event plan with Gemini AI, review budget and timeline, and persist it to SQLite.
            </p>
          </div>
        </div>

        {plan && (
          <button
            onClick={handleReset}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-800/80 px-3.5 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700 transition"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Generate Another Plan</span>
          </button>
        )}
      </div>

      {/* Generation Error Banner */}
      {generationError && (
        <ErrorBanner
          message={generationError}
          onRetry={() => {
            if (lastGenerationPayloadRef.current) {
              handleGeneratePlan(lastGenerationPayloadRef.current);
            }
          }}
          onDismiss={() => setGenerationError(null)}
        />
      )}

      {/* Input Form */}
      <EventForm onSubmit={handleGeneratePlan} isLoading={isGenerating} />

      {/* Loading Skeleton */}
      {isGenerating && <LoadingSkeleton />}

      {/* Plan Preview & Save Flow */}
      {plan && !isGenerating && (
        <div id="generated-plan-preview" className="space-y-8">
          {/* Sticky/Prominent Save Action Bar */}
          <div className="sticky top-20 z-30 flex flex-col sm:flex-row items-center justify-between gap-4 rounded-2xl border border-indigo-500/30 bg-indigo-950/80 p-4 sm:p-5 shadow-2xl backdrop-blur-md">
            <div className="flex items-center gap-3 text-left">
              <div className="p-3 rounded-xl bg-indigo-600/30 text-indigo-300 border border-indigo-400/30 shrink-0">
                <Sparkles className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">
                  Event Plan Ready to Save
                </h3>
                <p className="text-xs text-indigo-200/80">
                  Save this plan to your portfolio to manage real expenses, track task deadlines, and edit details anytime.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3 w-full sm:w-auto shrink-0">
              <button
                type="button"
                id="save-event-btn"
                disabled={isSaving || isSaved}
                onClick={handleSaveEvent}
                className={`flex-1 sm:flex-none inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-xs font-bold transition shadow-lg ${
                  isSaved
                    ? 'bg-emerald-600 text-white cursor-default'
                    : isSaving
                    ? 'bg-indigo-700 text-indigo-200 cursor-not-allowed opacity-80'
                    : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-600/40 hover:scale-[1.02] active:scale-[0.98]'
                }`}
              >
                {isSaved ? (
                  <>
                    <CheckCircle className="h-4 w-4" />
                    <span>Saved! Redirecting...</span>
                  </>
                ) : isSaving ? (
                  <>
                    <span className="h-4 w-4 rounded-full border-2 border-white/20 border-t-white animate-spin" />
                    <span>Saving Event...</span>
                  </>
                ) : (
                  <>
                    <Bookmark className="h-4 w-4" />
                    <span>Save Event to Database</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Save Error Banner */}
          {saveError && (
            <div className="rounded-2xl border border-rose-500/30 bg-rose-950/20 p-4 flex items-center justify-between gap-4">
              <div className="flex items-center gap-3 text-rose-200 text-xs">
                <AlertCircle className="h-5 w-5 text-rose-400 shrink-0" />
                <span>{saveError}</span>
              </div>
              <button
                onClick={handleSaveEvent}
                className="px-3.5 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-xs font-semibold text-white shrink-0"
              >
                Retry Save
              </button>
            </div>
          )}

          {/* Save Warnings Banner */}
          {saveWarnings.length > 0 && (
            <div className="rounded-2xl border border-amber-500/30 bg-amber-950/20 p-4 space-y-2">
              <div className="flex items-center gap-2 text-amber-300 text-xs font-semibold uppercase">
                <AlertTriangle className="h-4 w-4" />
                <span>Save Notices ({saveWarnings.length})</span>
              </div>
              <ul className="list-disc list-inside space-y-1 text-xs text-amber-200/90">
                {saveWarnings.map((warn, idx) => (
                  <li key={idx}>{warn}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Generated Plan Breakdown */}
          <PlanOverview plan={plan} />
          <BudgetSection
            budget={plan.budget}
            currency={plan.event_details?.currency || 'INR'}
          />
          <TimelineSection
            timeline={plan.timeline}
            checklist={plan.checklist}
          />
          <CreativeSection
            theme={plan.recommended_theme}
            decorations={plan.decoration_suggestions}
            catering={plan.catering_suggestions}
            entertainment={plan.entertainment_suggestions}
          />
          <LogisticsAndRisks
            vendors={plan.vendor_requirements}
            risks={plan.risks}
          />
        </div>
      )}
    </div>
  );
}
