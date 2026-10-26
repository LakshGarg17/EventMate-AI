import React, { useState, useEffect, useRef } from 'react';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import EventForm from './components/EventForm';
import PlanOverview from './components/PlanOverview';
import BudgetSection from './components/BudgetSection';
import TimelineSection from './components/TimelineSection';
import CreativeSection from './components/CreativeSection';
import LogisticsAndRisks from './components/LogisticsAndRisks';
import LoadingSkeleton from './components/LoadingSkeleton';
import ErrorBanner from './components/ErrorBanner';
import EmptyState from './components/EmptyState';
import { checkHealth, generateEventPlan } from './services/api';
import { Menu } from 'lucide-react';

export default function App() {
  const [health, setHealth] = useState(null);
  const [plan, setPlan] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeSection, setActiveSection] = useState('planner-form');
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  // Keep reference of last payload for retry action
  const lastPayloadRef = useRef(null);

  // Check backend health on initial load
  useEffect(() => {
    let mounted = true;

    async function fetchHealth() {
      try {
        const data = await checkHealth();
        if (mounted) {
          setHealth(data);
        }
      } catch (err) {
        if (mounted) {
          console.warn('Backend health check error:', err.message);
          setHealth({ status: 'offline', ai_configured: false, model: 'demo' });
        }
      }
    }

    fetchHealth();
    return () => {
      mounted = false;
    };
  }, []);

  const handleGeneratePlan = async (payload) => {
    lastPayloadRef.current = payload;
    setIsLoading(true);
    setError(null);

    try {
      const generatedPlan = await generateEventPlan(payload);
      setPlan(generatedPlan);
      setActiveSection('plan-overview');

      // Scroll to plan overview smoothly
      setTimeout(() => {
        const el = document.getElementById('plan-overview');
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 100);
    } catch (err) {
      console.error('Plan generation failed:', err);
      setError(err.message || 'An unexpected error occurred while generating the plan.');
    } finally {
      // Guaranteed to always terminate loading state
      setIsLoading(false);
    }
  };

  const handleRetry = () => {
    if (lastPayloadRef.current) {
      handleGeneratePlan(lastPayloadRef.current);
    }
  };

  const handleReset = () => {
    setPlan(null);
    setError(null);
    setActiveSection('planner-form');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen bg-[#0b0f19] text-slate-100 flex flex-col font-sans">
      {/* Top Navbar */}
      <Navbar health={health} onReset={handleReset} hasPlan={!!plan} />

      {/* Main Container */}
      <div className="mx-auto flex w-full max-w-7xl flex-1 px-4 sm:px-6 lg:px-8 py-6 gap-6">
        {/* Sidebar Nav */}
        <Sidebar
          hasPlan={!!plan}
          activeSection={activeSection}
          onSelectSection={setActiveSection}
          isMobileOpen={isMobileOpen}
          setIsMobileOpen={setIsMobileOpen}
        />

        {/* Content Body */}
        <main className="flex-1 space-y-8 min-w-0">
          {/* Mobile menu toggle bar */}
          <div className="flex items-center justify-between lg:hidden pb-2 border-b border-slate-800">
            <button
              onClick={() => setIsMobileOpen(true)}
              className="inline-flex items-center gap-2 rounded-xl bg-slate-800/80 px-3.5 py-2 text-xs font-semibold text-slate-200 border border-slate-700 hover:bg-slate-700 transition"
              id="mobile-menu-toggle-btn"
            >
              <Menu className="h-4 w-4" />
              <span>Section Navigation</span>
            </button>
            {plan && (
              <span className="text-xs font-mono text-slate-400">
                {plan.event_details?.event_name?.slice(0, 24)}...
              </span>
            )}
          </div>

          {/* Error Banner */}
          {error && (
            <ErrorBanner
              message={error}
              onRetry={handleRetry}
              onDismiss={() => setError(null)}
            />
          )}

          {/* Event Input Form */}
          <EventForm onSubmit={handleGeneratePlan} isLoading={isLoading} />

          {/* Plan Display Area */}
          {isLoading ? (
            <LoadingSkeleton />
          ) : plan ? (
            <div className="space-y-8">
              {/* Executive Overview & Key Metrics */}
              <PlanOverview plan={plan} />

              {/* Verified Budget Breakdown */}
              <BudgetSection
                budget={plan.budget}
                currency={plan.event_details?.currency || 'INR'}
              />

              {/* Milestones Timeline & Checklist */}
              <TimelineSection
                timeline={plan.timeline}
                checklist={plan.checklist}
              />

              {/* Aesthetic Themes & Directives */}
              <CreativeSection
                theme={plan.recommended_theme}
                decorations={plan.decoration_suggestions}
                catering={plan.catering_suggestions}
                entertainment={plan.entertainment_suggestions}
              />

              {/* Logistics & Risk Playbook */}
              <LogisticsAndRisks
                vendors={plan.vendor_requirements}
                risks={plan.risks}
              />
            </div>
          ) : (
            <EmptyState />
          )}
        </main>
      </div>
    </div>
  );
}
