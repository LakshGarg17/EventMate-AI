import React, { useState, useEffect } from 'react';
import { Loader2 } from 'lucide-react';

export default function SlowStartBanner() {
  const [isSlow, setIsSlow] = useState(false);

  useEffect(() => {
    function handleSlow(e) {
      setIsSlow(Boolean(e.detail?.active));
    }

    window.addEventListener('api-slow-start', handleSlow);
    return () => {
      window.removeEventListener('api-slow-start', handleSlow);
    };
  }, []);

  if (!isSlow) return null;

  return (
    <div
      role="status"
      id="slow-start-banner"
      className="bg-gradient-to-r from-amber-900/90 via-amber-800/90 to-amber-900/90 border-b border-amber-600/40 text-amber-100 text-xs px-4 py-2.5 flex items-center justify-center gap-2.5 shadow-md backdrop-blur-md sticky top-0 z-50 animate-fadeIn"
    >
      <Loader2 className="h-4 w-4 animate-spin text-amber-300 shrink-0" />
      <span className="font-medium text-center">
        Backend is waking up, thanks for your patience... (Free-tier cold starts may take up to 45s)
      </span>
    </div>
  );
}

