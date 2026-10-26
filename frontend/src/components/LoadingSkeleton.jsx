import { Loader2 } from 'lucide-react';


const LOADING_STEPS = [
  'Connecting to EventMate AI synthesis engine...',
  'Analyzing celebration venue, attendance, and constraints...',
  'Calculating verified budget allocations with largest-remainder math...',
  'Synthesizing chronological timeline and overdue safeguards...',
  'Harmonizing aesthetic color palettes and sensory experiences...',
  'Compiling final execution blueprint...',
];

export default function LoadingSkeleton() {
  const [stepIndex, setStepIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setStepIndex((prev) => (prev < LOADING_STEPS.length - 1 ? prev + 1 : prev));
    }, 2800);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6 animate-pulse">
      {/* Header Banner */}
      <div className="rounded-2xl border border-indigo-500/30 bg-indigo-950/20 p-6 text-center">
        <div className="flex items-center justify-center gap-3">
          <Loader2 className="h-6 w-6 animate-spin text-indigo-400" />
          <h3 className="text-lg font-bold text-white tracking-tight">
            Synthesizing Celebration Plan
          </h3>
        </div>
        <p className="mt-2 text-xs font-mono text-indigo-300">
          {LOADING_STEPS[stepIndex]}
        </p>
      </div>

      {/* Metric Cards Skeleton */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-24 rounded-xl border border-slate-800 bg-slate-900/60 p-4">
            <div className="h-3 w-16 rounded bg-slate-800" />
            <div className="mt-3 h-6 w-24 rounded bg-slate-800" />
          </div>
        ))}
      </div>

      {/* Main Blocks Skeleton */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <div className="lg:col-span-7 h-80 rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
          <div className="h-4 w-48 rounded bg-slate-800" />
          <div className="h-24 rounded-xl bg-slate-800/60" />
          <div className="h-24 rounded-xl bg-slate-800/60" />
        </div>
        <div className="lg:col-span-5 h-80 rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
          <div className="h-4 w-36 rounded bg-slate-800" />
          <div className="h-48 rounded-full border border-slate-800 mx-auto w-48" />
        </div>
      </div>
    </div>
  );
}
