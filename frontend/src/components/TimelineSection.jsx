import {
  CalendarCheck,
  CheckCircle2,
  Circle,
  AlertCircle,
  Calendar,
} from 'lucide-react';
import { formatDate } from '../utils/formatters';


export default function TimelineSection({ timeline, checklist }) {
  const tasks = timeline || [];
  const initialChecklist = checklist || [];

  // Local state for interactive checklist
  const [checkedItems, setCheckedItems] = useState({});

  const toggleCheck = (idx) => {
    setCheckedItems((prev) => ({
      ...prev,
      [idx]: !prev[idx],
    }));
  };

  const completedCount = Object.values(checkedItems).filter(Boolean).length;
  const progressPercent = initialChecklist.length
    ? Math.round((completedCount / initialChecklist.length) * 100)
    : 0;

  return (
    <section id="timeline-section" className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 shadow-xl backdrop-blur-md">
      {/* Header */}
      <div className="pb-6 border-b border-slate-800/80">
        <div className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <CalendarCheck className="h-4 w-4" />
          </span>
          <h3 className="text-xl font-bold text-white tracking-tight">Milestone Timeline & Action Checklist</h3>
        </div>
        <p className="text-xs text-slate-400 mt-1">
          Chronologically sorted execution schedule with automated overdue detection and preparation checkpoints.
        </p>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-8 lg:grid-cols-12">
        {/* Left Column: Chronological Timeline Tasks */}
        <div className="lg:col-span-7 space-y-4">
          <h4 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center justify-between">
            <span>Execution Milestones ({tasks.length})</span>
            <span className="text-xs text-slate-500 font-normal">Sorted by due date</span>
          </h4>

          <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
            {tasks.map((task, idx) => {
              const isOverdue = task.is_overdue;
              const isUnrealistic = task.is_unrealistic;
              const priority = task.priority || 'Medium';

              const priorityBadge = {
                High: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
                Medium: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
                Low: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
              }[priority];

              return (
                <div key={idx} className="relative group">
                  {/* Timeline Marker Node */}
                  <span
                    className={`absolute -left-[27px] top-1.5 h-3.5 w-3.5 rounded-full border-2 transition ${
                      isOverdue
                        ? 'border-rose-500 bg-rose-950 animate-pulse'
                        : 'border-indigo-500 bg-slate-900 group-hover:scale-125'
                    }`}
                  />

                  {/* Task Card */}
                  <div
                    className={`rounded-xl border p-4 transition ${
                      isOverdue
                        ? 'border-rose-500/40 bg-rose-950/10'
                        : 'border-slate-800/80 bg-slate-950/50 hover:border-slate-700 hover:bg-slate-950/80'
                    }`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2 pb-2">
                      <div className="flex items-center gap-2">
                        <span className={`rounded-md px-2 py-0.5 text-[10px] font-bold uppercase border ${priorityBadge}`}>
                          {priority} Priority
                        </span>
                        <span className="rounded-md bg-slate-800 px-2 py-0.5 text-[10px] font-medium text-slate-400 border border-slate-700/60">
                          {task.category}
                        </span>
                        {isOverdue && (
                          <span className="rounded-md bg-rose-500/20 text-rose-300 px-2 py-0.5 text-[10px] font-bold uppercase border border-rose-500/30 animate-pulse">
                            Overdue
                          </span>
                        )}
                        {isUnrealistic && !isOverdue && (
                          <span className="rounded-md bg-amber-500/20 text-amber-300 px-2 py-0.5 text-[10px] font-bold uppercase border border-amber-500/30">
                            Urgent
                          </span>
                        )}
                      </div>


                      <div className="flex items-center gap-2 text-xs font-mono font-medium">
                        <Calendar className="h-3.5 w-3.5 text-slate-500" />
                        <span className={isOverdue ? 'text-rose-400 font-bold' : 'text-slate-300'}>
                          {formatDate(task.due_date)}
                        </span>
                        <span className="text-[10px] text-slate-500 font-sans">
                          ({task.days_before}d before)
                        </span>
                      </div>
                    </div>

                    <h5 className="text-sm font-semibold text-white mt-1">
                      {task.task}
                    </h5>
                    <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                      {task.description}
                    </p>

                    {/* Overdue Warning Callout */}
                    {task.warning && (
                      <div className="mt-2.5 flex items-start gap-1.5 rounded-lg bg-rose-500/10 border border-rose-500/20 px-2.5 py-1.5 text-[11px] text-rose-300">
                        <AlertCircle className="h-3.5 w-3.5 text-rose-400 shrink-0 mt-0.5" />
                        <span>{task.warning}</span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Action Checklist with Progress */}
        <div className="lg:col-span-5 space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
              Readiness Checklist ({initialChecklist.length})
            </h4>
            <span className="text-xs font-bold text-indigo-400 font-mono">
              {progressPercent}% Complete
            </span>
          </div>

          {/* Progress bar */}
          <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-indigo-500 to-emerald-400 transition-all duration-300"
              style={{ width: `${progressPercent}%` }}
            />
          </div>

          {/* Checklist Items */}
          <div className="rounded-xl border border-slate-800/80 bg-slate-950/40 p-4 space-y-2.5">
            {initialChecklist.map((item, idx) => {
              const isDone = !!checkedItems[idx];
              return (
                <button
                  key={idx}
                  type="button"
                  onClick={() => toggleCheck(idx)}
                  className={`flex w-full items-start gap-3 rounded-lg p-2.5 text-left text-xs transition ${
                    isDone
                      ? 'bg-emerald-950/20 text-slate-400 line-through border border-emerald-500/20'
                      : 'hover:bg-slate-800/40 text-slate-200'
                  }`}
                >
                  {isDone ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                  ) : (
                    <Circle className="h-4 w-4 text-slate-500 shrink-0 mt-0.5" />
                  )}
                  <span className="leading-snug">{item}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
