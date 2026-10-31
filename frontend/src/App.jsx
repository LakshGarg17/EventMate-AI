import React, { useState, useEffect, lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import ErrorBoundary from './components/ErrorBoundary';
import SlowStartBanner from './components/SlowStartBanner';
import ConfigErrorScreen from './components/ConfigErrorScreen';
import { IS_MISSING_PROD_API_URL } from './services/config';
import { checkHealth } from './services/api';
import { Menu, Loader2 } from 'lucide-react';

// Route-level code splitting
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const NewEventPage = lazy(() => import('./pages/NewEventPage'));
const EventDetailPage = lazy(() => import('./pages/EventDetailPage'));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'));

function PageFallback() {
  return (
    <div className="flex min-h-[50vh] items-center justify-center">
      <div className="flex items-center gap-3 text-slate-400 text-sm">
        <Loader2 className="h-5 w-5 animate-spin text-indigo-400" />
        <span>Loading page...</span>
      </div>
    </div>
  );
}

export default function App() {
  if (IS_MISSING_PROD_API_URL) {
    return <ConfigErrorScreen />;
  }

  const [health, setHealth] = useState(null);
  const [isMobileOpen, setIsMobileOpen] = useState(false);

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
          setHealth({ status: 'offline', ai_configured: false, model: 'demo' });
        }
      }
    }

    fetchHealth();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <ErrorBoundary>
      <BrowserRouter>
        <div className="min-h-screen bg-[#0b0f19] text-slate-100 flex flex-col font-sans">
          <SlowStartBanner />

          {/* Top Navbar */}
          <Navbar health={health} />

          {/* Main Workspace Layout */}
          <div className="mx-auto flex w-full max-w-7xl flex-1 px-4 sm:px-6 lg:px-8 py-6 gap-6">
            {/* Dynamic Sidebar */}
            <Sidebar
              isMobileOpen={isMobileOpen}
              setIsMobileOpen={setIsMobileOpen}
            />

            {/* Main Content Area */}
            <main className="flex-1 min-w-0">
              {/* Mobile Nav Toggle */}
              <div className="flex items-center justify-between lg:hidden pb-3 mb-4 border-b border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsMobileOpen(true)}
                  className="inline-flex items-center gap-2 rounded-xl bg-slate-800/80 px-3.5 py-2 text-xs font-semibold text-slate-200 border border-slate-700 hover:bg-slate-700 transition"
                  id="mobile-nav-toggle-btn"
                >
                  <Menu className="h-4 w-4" />
                  <span>Navigation Menu</span>
                </button>
              </div>

              <Suspense fallback={<PageFallback />}>
                <Routes>
                  <Route path="/" element={<DashboardPage />} />
                  <Route path="/events/new" element={<NewEventPage />} />
                  <Route path="/events/:id" element={<EventDetailPage />} />
                  <Route path="*" element={<NotFoundPage />} />
                </Routes>
              </Suspense>
            </main>
          </div>
        </div>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
