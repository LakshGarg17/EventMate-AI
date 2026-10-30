import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import DashboardPage from './pages/DashboardPage';
import NewEventPage from './pages/NewEventPage';
import EventDetailPage from './pages/EventDetailPage';
import { checkHealth } from './services/api';
import { Menu } from 'lucide-react';

export default function App() {
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

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-[#0b0f19] text-slate-100 flex flex-col font-sans">
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
                onClick={() => setIsMobileOpen(true)}
                className="inline-flex items-center gap-2 rounded-xl bg-slate-800/80 px-3.5 py-2 text-xs font-semibold text-slate-200 border border-slate-700 hover:bg-slate-700 transition"
                id="mobile-nav-toggle-btn"
              >
                <Menu className="h-4 w-4" />
                <span>Navigation Menu</span>
              </button>
            </div>

            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/events/new" element={<NewEventPage />} />
              <Route path="/events/:id" element={<EventDetailPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
}
