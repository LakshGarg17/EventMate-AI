import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams, Link } from 'react-router-dom';
import {
  Calendar,
  Clock,
  ArrowLeft,
  Trash2,
  Edit,
  Plus,
  Circle,
  AlertTriangle,
  AlertCircle,
  FileText,
  PieChart,
  ListTodo,
  Sparkles,
  Check,
  RefreshCw,
  Table as TableIcon,
  BarChart3,
  Cpu,
  Building2,
  Bot,
  Palette,
  Mail,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from 'recharts';
import ConfirmDialog from '../components/ConfirmDialog';
import ExpenseModal from '../components/ExpenseModal';
import TaskModal from '../components/TaskModal';
import CreativeSection from '../components/CreativeSection';
import LogisticsAndRisks from '../components/LogisticsAndRisks';
import AssistantSection from '../components/AssistantSection';
import ThemesSection from '../components/ThemesSection';
import InvitationsSection from '../components/InvitationsSection';
import VendorsSection from '../components/VendorsSection';
import {
  getEvent,
  updateEvent,
  deleteEvent,
  createExpense,
  updateExpense,
  deleteExpense,
  createTask,
  updateTask,
  deleteTask,
} from '../services/api';
import { formatCurrency, formatDate } from '../utils/formatters';

const SUPPORTED_CURRENCIES = ['INR', 'USD', 'EUR', 'GBP', 'CAD', 'AUD', 'AED', 'SGD', 'JPY'];
const EVENT_TYPES = ['Wedding', 'Birthday', 'Community Event'];

export default function EventDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const activeTab = searchParams.get('tab') || 'overview';
  const setActiveTab = (tab) => {
    setSearchParams({ tab });
  };

  const [event, setEvent] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Edit Event state
  const [editFormData, setEditFormData] = useState({});
  const [editErrors, setEditErrors] = useState({});
  const [isUpdatingEvent, setIsUpdatingEvent] = useState(false);
  const [eventUpdateSuccess, setEventUpdateSuccess] = useState(false);

  // Modals state
  const [isExpenseModalOpen, setIsExpenseModalOpen] = useState(false);
  const [editingExpense, setEditingExpense] = useState(null);
  const [isExpenseSubmitting, setIsExpenseSubmitting] = useState(false);

  const [isTaskModalOpen, setIsTaskModalOpen] = useState(false);
  const [editingTask, setEditingTask] = useState(null);
  const [isTaskSubmitting, setIsTaskSubmitting] = useState(false);

  // Accessible ConfirmDialog state
  const [confirmState, setConfirmState] = useState({
    isOpen: false,
    title: '',
    message: '',
    confirmLabel: 'Delete',
    action: null,
    isLoading: false,
  });

  // Task filter state
  const [taskFilter, setTaskFilter] = useState('ALL');

  // Chart view vs accessible table view toggle
  const [showTableView, setShowTableView] = useState(false);

  // Fetch full event data from API
  const fetchEventData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getEvent(id);
      setEvent(data);
      setEditFormData({
        name: data.name || '',
        event_type: data.event_type || 'Wedding',
        event_date: data.event_date || '',
        location: data.location || '',
        guest_count: data.guest_count || 50,
        total_budget: data.total_budget || '0.00',
        currency: data.currency || 'INR',
        preferred_theme: data.preferred_theme || '',
        additional_preferences: data.additional_preferences || '',
      });
    } catch (err) {
      console.error('Failed to load event:', err);
      setError(err.message || 'Event not found or failed to load.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchEventData();
  }, [id]);

  // Handle Event Edit Submit
  const handleUpdateEvent = async (e) => {
    e.preventDefault();
    const newErrors = {};

    if (!editFormData.name.trim()) newErrors.name = 'Event name is required';
    if (!editFormData.location.trim()) newErrors.location = 'Location is required';
    if (!editFormData.event_date) newErrors.event_date = 'Event date is required';
    if (!Number(editFormData.guest_count) || Number(editFormData.guest_count) < 1) {
      newErrors.guest_count = 'Guest count must be at least 1';
    }
    if (Number(editFormData.total_budget) <= 0) {
      newErrors.total_budget = 'Total budget must be greater than zero';
    }

    if (Object.keys(newErrors).length > 0) {
      setEditErrors(newErrors);
      return;
    }

    setIsUpdatingEvent(true);
    setEditErrors({});
    try {
      const payload = {
        name: editFormData.name.trim(),
        event_type: editFormData.event_type,
        event_date: editFormData.event_date,
        location: editFormData.location.trim(),
        guest_count: Number(editFormData.guest_count),
        total_budget: String(editFormData.total_budget),
        preferred_theme: editFormData.preferred_theme?.trim() || null,
        additional_preferences: editFormData.additional_preferences?.trim() || null,
      };

      // Only pass currency if it actually changed
      if (editFormData.currency !== event.currency) {
        payload.currency = editFormData.currency;
      }

      await updateEvent(id, payload);
      setEventUpdateSuccess(true);
      setTimeout(() => setEventUpdateSuccess(false), 3000);
      await fetchEventData();
    } catch (err) {
      setEditErrors({ form: err.message || 'Failed to update event' });
    } finally {
      setIsUpdatingEvent(false);
    }
  };

  // Handle Event Delete
  const handleDeleteEventClick = () => {
    setConfirmState({
      isOpen: true,
      title: 'Delete Event & All Records?',
      message: `Are you sure you want to permanently delete "${event?.name}"? All associated budget categories, expenses, and tasks will be deleted. This cannot be undone.`,
      confirmLabel: 'Permanently Delete Event',
      action: async () => {
        setConfirmState((prev) => ({ ...prev, isLoading: true }));
        try {
          await deleteEvent(id);
          navigate('/');
        } catch (err) {
          alert(`Delete failed: ${err.message}`);
          setConfirmState((prev) => ({ ...prev, isOpen: false, isLoading: false }));
        }
      },
      isLoading: false,
    });
  };

  // Handle Expense Add / Edit
  const handleExpenseSubmit = async (payload) => {
    setIsExpenseSubmitting(true);
    try {
      if (editingExpense) {
        await updateExpense(editingExpense.id, payload);
      } else {
        await createExpense(id, payload);
      }
      setIsExpenseModalOpen(false);
      setEditingExpense(null);
      await fetchEventData();
    } catch (err) {
      alert(`Expense save failed: ${err.message}`);
    } finally {
      setIsExpenseSubmitting(false);
    }
  };

  const handleDeleteExpenseClick = (exp) => {
    setConfirmState({
      isOpen: true,
      title: 'Delete Expense Item?',
      message: `Are you sure you want to delete "${exp.description}" (${formatCurrency(exp.estimated_amount, event?.currency)})?`,
      confirmLabel: 'Delete Expense',
      action: async () => {
        setConfirmState((prev) => ({ ...prev, isLoading: true }));
        try {
          await deleteExpense(exp.id);
          setConfirmState((prev) => ({ ...prev, isOpen: false, isLoading: false }));
          await fetchEventData();
        } catch (err) {
          alert(`Delete expense failed: ${err.message}`);
          setConfirmState((prev) => ({ ...prev, isLoading: false }));
        }
      },
      isLoading: false,
    });
  };

  // Handle Task Add / Edit
  const handleTaskSubmit = async (payload) => {
    setIsTaskSubmitting(true);
    try {
      if (editingTask) {
        await updateTask(editingTask.id, payload);
      } else {
        await createTask(id, payload);
      }
      setIsTaskModalOpen(false);
      setEditingTask(null);
      await fetchEventData();
    } catch (err) {
      alert(`Task save failed: ${err.message}`);
    } finally {
      setIsTaskSubmitting(false);
    }
  };

  const handleToggleTaskComplete = async (t) => {
    const newStatus = t.status === 'Completed' ? 'Pending' : 'Completed';
    try {
      await updateTask(t.id, { status: newStatus });
      await fetchEventData();
    } catch (err) {
      alert(`Status update failed: ${err.message}`);
    }
  };

  const handleDeleteTaskClick = (t) => {
    setConfirmState({
      isOpen: true,
      title: 'Delete Task?',
      message: `Are you sure you want to delete task "${t.title}"?`,
      confirmLabel: 'Delete Task',
      action: async () => {
        setConfirmState((prev) => ({ ...prev, isLoading: true }));
        try {
          await deleteTask(t.id);
          setConfirmState((prev) => ({ ...prev, isOpen: false, isLoading: false }));
          await fetchEventData();
        } catch (err) {
          alert(`Delete task failed: ${err.message}`);
          setConfirmState((prev) => ({ ...prev, isLoading: false }));
        }
      },
      isLoading: false,
    });
  };

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 bg-slate-800 rounded w-1/3" />
        <div className="h-64 bg-slate-900 rounded-2xl" />
        <div className="grid grid-cols-4 gap-4">
          <div className="h-24 bg-slate-900 rounded-xl" />
          <div className="h-24 bg-slate-900 rounded-xl" />
          <div className="h-24 bg-slate-900 rounded-xl" />
          <div className="h-24 bg-slate-900 rounded-xl" />
        </div>
      </div>
    );
  }

  if (error || !event) {
    return (
      <div className="p-12 text-center rounded-3xl border border-slate-800 bg-slate-900/60 max-w-lg mx-auto space-y-5">
        <div className="p-4 rounded-2xl bg-rose-500/10 text-rose-400 border border-rose-500/20 inline-block">
          <AlertCircle className="h-10 w-10" />
        </div>
        <div className="space-y-2">
          <h2 className="text-xl font-bold text-white">Event Not Found</h2>
          <p className="text-sm text-slate-400">
            {error || 'This event may have been deleted or the requested ID does not exist.'}
          </p>
        </div>
        <Link
          to="/"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white shadow-lg transition"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Return to Dashboard</span>
        </Link>
      </div>
    );
  }

  const budgetSummary = event.budget_summary || {};
  const taskSummary = event.task_summary || {};
  const categories = event.budget_categories || [];
  const expenses = event.expenses || [];
  const tasks = event.tasks || [];

  const hasRecords = categories.length > 0 || expenses.length > 0;
  const isOverBudget = budgetSummary.over_budget;
  const unallocatedAmount = Number(budgetSummary.unallocated) || 0;

  // Filter tasks based on selected status
  const filteredTasks = tasks.filter((t) => {
    if (taskFilter === 'ALL') return true;
    return t.status === taskFilter;
  });

  const overdueTasks = tasks.filter((t) => t.is_overdue);
  const upcomingTasks = tasks.filter((t) => t.is_upcoming);

  // Prepare chart data for Allocated vs Actual
  const chartData = (budgetSummary.category_breakdown || []).map((cb) => ({
    name: cb.category_name,
    Allocated: Number(cb.allocated_estimate) || 0,
    Actual: Number(cb.expense_actual_total) || 0,
    Estimated: Number(cb.expense_estimated_total) || 0,
  }));

  const tabsList = [
    { id: 'overview', label: 'Overview & Settings', icon: FileText },
    {
      id: 'budget',
      label: 'Budget & Expenses',
      icon: PieChart,
      badge: isOverBudget ? (
        <span className="h-2 w-2 rounded-full bg-rose-400 animate-pulse" />
      ) : null,
    },
    {
      id: 'tasks',
      label: 'Timeline & Tasks',
      icon: ListTodo,
      badge: overdueTasks.length > 0 ? (
        <span className="rounded-full bg-rose-500/20 text-rose-400 px-1.5 py-0.2 text-[10px] font-bold">
          {overdueTasks.length}
        </span>
      ) : null,
    },
    { id: 'vendors', label: 'Vendors', icon: Building2 },
    { id: 'assistant', label: 'AI Assistant', icon: Bot },
    { id: 'themes', label: 'Themes & Decor', icon: Palette },
    { id: 'invitations', label: 'Invitations', icon: Mail },
    { id: 'plan', label: 'AI Master Plan', icon: Sparkles },
  ];

  const handleTabKeyDown = (e, currentIndex) => {
    if (e.key === 'ArrowRight') {
      e.preventDefault();
      const nextIndex = (currentIndex + 1) % tabsList.length;
      const nextTab = tabsList[nextIndex].id;
      setActiveTab(nextTab);
      document.getElementById(`tab-${nextTab}`)?.focus();
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      const prevIndex = (currentIndex - 1 + tabsList.length) % tabsList.length;
      const prevTab = tabsList[prevIndex].id;
      setActiveTab(prevTab);
      document.getElementById(`tab-${prevTab}`)?.focus();
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Top Banner & Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <Link
            to="/"
            className="p-2.5 rounded-xl border border-slate-800 bg-slate-900 text-slate-400 hover:text-white hover:bg-slate-800 transition"
            title="Back to Dashboard"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div className="space-y-1">
            <div className="flex items-center gap-2.5 flex-wrap">
              <span className="rounded-md bg-indigo-500/10 px-2 py-0.5 text-xs font-bold uppercase tracking-wider text-indigo-400 border border-indigo-500/20">
                {event.event_type}
              </span>
              <h1 className="text-2xl font-extrabold tracking-tight text-white">
                {event.name}
              </h1>
            </div>
            <div className="flex items-center gap-4 text-xs text-slate-400">
              <span>{formatDate(event.event_date)}</span>
              <span>•</span>
              <span>{event.location}</span>
              <span>•</span>
              <span>{(event.guest_count || 0).toLocaleString()} Guests</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 self-start lg:self-auto">
          <button
            onClick={fetchEventData}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-slate-800 bg-slate-900 text-xs font-medium text-slate-300 hover:bg-slate-800 transition"
            title="Reload from API"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Refresh</span>
          </button>
          <button
            onClick={handleDeleteEventClick}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-rose-500/30 bg-rose-500/10 text-xs font-semibold text-rose-300 hover:bg-rose-500/20 transition"
            id="delete-event-btn"
          >
            <Trash2 className="h-3.5 w-3.5" />
            <span>Delete Event</span>
          </button>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div
        role="tablist"
        aria-label="Event management tabs"
        className="flex items-center gap-2 border-b border-slate-800 overflow-x-auto pb-px"
      >
        {tabsList.map((t, idx) => {
          const Icon = t.icon;
          const isSelected = activeTab === t.id;
          return (
            <button
              key={t.id}
              role="tab"
              id={`tab-${t.id}`}
              aria-selected={isSelected}
              aria-controls={`panel-${t.id}`}
              tabIndex={isSelected ? 0 : -1}
              onClick={() => setActiveTab(t.id)}
              onKeyDown={(e) => handleTabKeyDown(e, idx)}
              className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold rounded-t-xl transition border-b-2 whitespace-nowrap focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 ${
                isSelected
                  ? 'border-indigo-500 text-white bg-slate-900/60'
                  : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/30'
              }`}
            >
              <Icon className="h-4 w-4" />
              <span>{t.label}</span>
              {t.badge}
            </button>
          );
        })}
      </div>

      {/* TAB 1: OVERVIEW & SETTINGS */}
      {activeTab === 'overview' && (
        <div
          role="tabpanel"
          id="panel-overview"
          aria-labelledby="tab-overview"
          tabIndex={0}
          className="space-y-6 focus:outline-none"
        >
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 shadow-xl space-y-6">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div>
                <h2 className="text-lg font-bold text-white">Event Parameters & Core Details</h2>
                <p className="text-xs text-slate-400">
                  Update event particulars. Budget categories and task assignments remain intact.
                </p>
              </div>
              {eventUpdateSuccess && (
                <div className="flex items-center gap-2 text-emerald-400 text-xs font-semibold bg-emerald-950/40 border border-emerald-500/30 px-3 py-1.5 rounded-lg animate-in fade-in">
                  <Check className="h-4 w-4" />
                  <span>Changes saved to database</span>
                </div>
              )}
            </div>

            {editErrors.form && (
              <div className="rounded-xl border border-rose-500/30 bg-rose-950/20 p-3 text-xs text-rose-300">
                {editErrors.form}
              </div>
            )}

            <form onSubmit={handleUpdateEvent} className="space-y-5">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Event Name <span className="text-rose-400">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={editFormData.name || ''}
                    onChange={(e) => setEditFormData({ ...editFormData, name: e.target.value })}
                    className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3.5 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                  {editErrors.name && <p className="mt-1 text-xs text-rose-400">{editErrors.name}</p>}
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Event Type
                  </label>
                  <select
                    value={editFormData.event_type || 'Wedding'}
                    onChange={(e) => setEditFormData({ ...editFormData, event_type: e.target.value })}
                    className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3.5 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  >
                    {EVENT_TYPES.map((t) => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Event Date <span className="text-rose-400">*</span>
                  </label>
                  <input
                    type="date"
                    required
                    value={editFormData.event_date || ''}
                    onChange={(e) => setEditFormData({ ...editFormData, event_date: e.target.value })}
                    className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3.5 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                  {editErrors.event_date && (
                    <p className="mt-1 text-xs text-rose-400">{editErrors.event_date}</p>
                  )}
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Location <span className="text-rose-400">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={editFormData.location || ''}
                    onChange={(e) => setEditFormData({ ...editFormData, location: e.target.value })}
                    className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3.5 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                  {editErrors.location && (
                    <p className="mt-1 text-xs text-rose-400">{editErrors.location}</p>
                  )}
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Guest Count <span className="text-rose-400">*</span>
                  </label>
                  <input
                    type="number"
                    min="1"
                    required
                    value={editFormData.guest_count || ''}
                    onChange={(e) => setEditFormData({ ...editFormData, guest_count: e.target.value })}
                    className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3.5 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                  {editErrors.guest_count && (
                    <p className="mt-1 text-xs text-rose-400">{editErrors.guest_count}</p>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Total Budget ({event.currency}) <span className="text-rose-400">*</span>
                  </label>
                  <input
                    type="text"
                    inputMode="decimal"
                    required
                    value={editFormData.total_budget || ''}
                    onChange={(e) => setEditFormData({ ...editFormData, total_budget: e.target.value })}
                    className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3.5 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                  {editErrors.total_budget && (
                    <p className="mt-1 text-xs text-rose-400">{editErrors.total_budget}</p>
                  )}
                  <p className="mt-1 text-[11px] text-slate-500">
                    Modifying total budget does not rescale categories; any unallocated amount shows in Budget tab.
                  </p>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Currency
                  </label>
                  <select
                    disabled={hasRecords}
                    value={editFormData.currency || 'INR'}
                    onChange={(e) => setEditFormData({ ...editFormData, currency: e.target.value })}
                    className={`w-full rounded-xl bg-slate-950 border border-slate-800 px-3.5 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-indigo-500 ${
                      hasRecords ? 'opacity-60 cursor-not-allowed' : ''
                    }`}
                  >
                    {SUPPORTED_CURRENCIES.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                  {hasRecords && (
                    <p className="mt-1 text-[11px] text-slate-500">
                      Locked because categories/expenses already exist.
                    </p>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Preferred Theme
                  </label>
                  <input
                    type="text"
                    value={editFormData.preferred_theme || ''}
                    onChange={(e) => setEditFormData({ ...editFormData, preferred_theme: e.target.value })}
                    placeholder="e.g. Royal Vintage"
                    className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3.5 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Special Preferences / Constraints
                  </label>
                  <input
                    type="text"
                    value={editFormData.additional_preferences || ''}
                    onChange={(e) => setEditFormData({ ...editFormData, additional_preferences: e.target.value })}
                    placeholder="e.g. Pure veg catering, acoustic sound"
                    className="w-full rounded-xl bg-slate-950 border border-slate-800 px-3.5 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="flex justify-end pt-3">
                <button
                  type="submit"
                  disabled={isUpdatingEvent}
                  className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white shadow-lg shadow-indigo-600/30 transition disabled:opacity-50 flex items-center gap-2"
                  id="save-event-changes-btn"
                >
                  {isUpdatingEvent && (
                    <span className="h-4 w-4 rounded-full border-2 border-white/20 border-t-white animate-spin" />
                  )}
                  <span>Save Event Changes</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* TAB 2: BUDGET & EXPENSES */}
      {activeTab === 'budget' && (
        <div
          role="tabpanel"
          id="panel-budget"
          aria-labelledby="tab-budget"
          tabIndex={0}
          className="space-y-6 focus:outline-none"
        >
          {/* Over-Budget Warning Banner */}
          {isOverBudget && (
            <div className="rounded-2xl border border-rose-500/40 bg-rose-950/30 p-4 flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <h3 className="text-sm font-bold text-rose-200">
                  Budget Warning: Over Budget
                </h3>
                <p className="text-xs text-rose-300/80 mt-0.5">
                  Total actual spending ({formatCurrency(budgetSummary.total_actual, event.currency)}) exceeds the total event budget ({formatCurrency(budgetSummary.total_budget, event.currency)}) by {formatCurrency(Math.abs(Number(budgetSummary.remaining) || 0), event.currency)}.
                </p>
              </div>
            </div>
          )}

          {/* Unallocated Notice Banner */}
          {unallocatedAmount !== 0 && (
            <div className={`rounded-2xl border p-4 flex items-start gap-3 ${
              unallocatedAmount > 0
                ? 'border-amber-500/30 bg-amber-950/20 text-amber-300'
                : 'border-rose-500/30 bg-rose-950/20 text-rose-300'
            }`}>
              <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
              <div>
                <h3 className="text-sm font-bold">
                  {unallocatedAmount > 0 ? 'Unallocated Funds' : 'Category Over-Allocation'}
                </h3>
                <p className="text-xs opacity-90 mt-0.5">
                  {unallocatedAmount > 0
                    ? `${formatCurrency(unallocatedAmount, event.currency)} of the total budget has not been allocated to any category.`
                    : `Category estimates exceed the total event budget by ${formatCurrency(Math.abs(unallocatedAmount), event.currency)}.`}
                </p>
              </div>
            </div>
          )}

          {/* 5-Metric Summary Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Total Budget</span>
              <p className="text-lg font-black text-white mt-1">
                {formatCurrency(budgetSummary.total_budget, event.currency)}
              </p>
              <span className="text-[10px] text-slate-500">Planned Ceiling</span>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Expense Estimates</span>
              <p className="text-lg font-black text-slate-300 mt-1">
                {formatCurrency(budgetSummary.total_estimated, event.currency)}
              </p>
              <span className="text-[10px] text-slate-500">Total Projected</span>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Actual Spent</span>
              <p className={`text-lg font-black mt-1 ${isOverBudget ? 'text-rose-400' : 'text-emerald-400'}`}>
                {formatCurrency(budgetSummary.total_actual, event.currency)}
              </p>
              <span className="text-[10px] text-slate-500">Verified Paid Out</span>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Remaining</span>
              <p className={`text-lg font-black mt-1 ${isOverBudget ? 'text-rose-400' : 'text-cyan-400'}`}>
                {formatCurrency(budgetSummary.remaining, event.currency)}
              </p>
              <span className="text-[10px] text-slate-500">Available Balance</span>
            </div>

            <div className="col-span-2 sm:col-span-1 rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Utilization</span>
              <p className={`text-lg font-black mt-1 ${isOverBudget ? 'text-rose-400' : 'text-indigo-400'}`}>
                {budgetSummary.utilization_percent}%
              </p>
              <span className="text-[10px] text-slate-500">Of Total Budget</span>
            </div>
          </div>

          {/* Recharts Category Chart: Allocated vs Actual */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 shadow-xl space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
              <div>
                <h3 className="text-base font-bold text-white">Category Allocation vs Actual Spending</h3>
                <p className="text-xs text-slate-400">Deterministic comparison across budget categories.</p>
              </div>
              <button
                onClick={() => setShowTableView(!showTableView)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800/80 text-xs font-medium text-slate-300 hover:text-white transition"
              >
                {showTableView ? <BarChart3 className="h-3.5 w-3.5" /> : <TableIcon className="h-3.5 w-3.5" />}
                <span>{showTableView ? 'View Bar Chart' : 'View Accessible Table'}</span>
              </button>
            </div>

            {showTableView ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-slate-950/80 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                    <tr>
                      <th className="py-2.5 px-3">Category</th>
                      <th className="py-2.5 px-3">Allocated ({event.currency})</th>
                      <th className="py-2.5 px-3">Expense Estimated</th>
                      <th className="py-2.5 px-3">Actual Spent</th>
                      <th className="py-2.5 px-3">Variance</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {(budgetSummary.category_breakdown || []).map((cb, idx) => {
                      const alloc = Number(cb.allocated_estimate) || 0;
                      const act = Number(cb.expense_actual_total) || 0;
                      const variance = alloc - act;
                      return (
                        <tr key={idx} className="hover:bg-slate-800/30">
                          <td className="py-2.5 px-3 font-semibold text-white">{cb.category_name}</td>
                          <td className="py-2.5 px-3">{formatCurrency(cb.allocated_estimate, event.currency)}</td>
                          <td className="py-2.5 px-3">{formatCurrency(cb.expense_estimated_total, event.currency)}</td>
                          <td className="py-2.5 px-3">{formatCurrency(cb.expense_actual_total, event.currency)}</td>
                          <td className={`py-2.5 px-3 font-semibold ${variance < 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                            {formatCurrency(variance, event.currency)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : chartData.length > 0 ? (
              <div className="h-72 w-full pt-4">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis
                      dataKey="name"
                      stroke="#94a3b8"
                      fontSize={11}
                      tickLine={false}
                      interval={0}
                      angle={-15}
                      textAnchor="end"
                    />
                    <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem', fontSize: '12px' }}
                      itemStyle={{ color: '#f8fafc' }}
                      formatter={(val) => formatCurrency(val, event.currency)}
                    />
                    <Legend wrapperStyle={{ paddingTop: '10px', fontSize: '12px' }} />
                    <Bar dataKey="Allocated" fill="#6366f1" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="Actual" fill="#10b981" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="text-xs text-slate-500 py-6 text-center italic">No category data available to chart.</p>
            )}
          </div>

          {/* Pending Payments Section */}
          {(budgetSummary.pending_payments || []).length > 0 && (
            <div className="rounded-2xl border border-amber-500/30 bg-amber-950/10 p-5 space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-amber-500/20">
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-amber-400" />
                  <h3 className="text-sm font-bold text-amber-200">
                    Pending Payments & Outstanding Obligations ({budgetSummary.pending_payments.length})
                  </h3>
                </div>
                <span className="text-xs font-bold text-amber-400">
                  Total Outstanding: {formatCurrency(budgetSummary.pending_total, event.currency)}
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {budgetSummary.pending_payments.map((p) => (
                  <div
                    key={p.expense_id}
                    className="flex items-center justify-between p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-xs"
                  >
                    <div>
                      <p className="font-semibold text-white">{p.description}</p>
                      <span className="text-[10px] text-amber-300 font-mono uppercase">
                        Status: {p.payment_status}
                      </span>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-amber-400">
                        {formatCurrency(p.outstanding, event.currency)}
                      </p>
                      <span className="text-[10px] text-slate-400">
                        Paid: {formatCurrency(p.actual_amount, event.currency)} of {formatCurrency(p.estimated_amount, event.currency)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Expense Item List with Add Button */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 shadow-xl space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
              <div>
                <h3 className="text-base font-bold text-white">Expense Registry</h3>
                <p className="text-xs text-slate-400">Track and update vendor invoices, deposits, and payouts.</p>
              </div>
              <button
                type="button"
                onClick={() => {
                  setEditingExpense(null);
                  setIsExpenseModalOpen(true);
                }}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white shadow-md shadow-indigo-600/30 transition self-start sm:self-auto"
                id="add-expense-btn"
              >
                <Plus className="h-4 w-4" />
                <span>Add Expense</span>
              </button>
            </div>

            {expenses.length === 0 ? (
              <div className="py-8 text-center text-slate-500 text-xs space-y-2">
                <p>No expenses recorded for this event yet.</p>
                <button
                  onClick={() => {
                    setEditingExpense(null);
                    setIsExpenseModalOpen(true);
                  }}
                  className="text-indigo-400 font-semibold hover:underline"
                >
                  Add the first expense item
                </button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-slate-950/80 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                    <tr>
                      <th className="py-2.5 px-3">Description</th>
                      <th className="py-2.5 px-3">Category</th>
                      <th className="py-2.5 px-3">Estimated</th>
                      <th className="py-2.5 px-3">Actual Paid</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3">Date</th>
                      <th className="py-2.5 px-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {expenses.map((exp) => {
                      const catName = categories.find((c) => c.id === exp.budget_category_id)?.category_name || 'Uncategorized';
                      const statusColor =
                        exp.payment_status === 'Paid'
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                          : exp.payment_status === 'Partial'
                          ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                          : 'bg-slate-800 text-slate-300 border-slate-700';

                      return (
                        <tr key={exp.id} className="hover:bg-slate-800/30 transition">
                          <td className="py-3 px-3">
                            <p className="font-semibold text-white">{exp.description}</p>
                            {exp.notes && <p className="text-[11px] text-slate-400 mt-0.5">{exp.notes}</p>}
                          </td>
                          <td className="py-3 px-3">
                            <span className="rounded-md bg-slate-800/80 border border-slate-700/80 px-2 py-0.5 text-[11px] font-medium text-slate-300">
                              {catName}
                            </span>
                          </td>
                          <td className="py-3 px-3 font-medium">
                            {formatCurrency(exp.estimated_amount, event.currency)}
                          </td>
                          <td className="py-3 px-3 font-semibold text-slate-100">
                            {exp.actual_amount !== null
                              ? formatCurrency(exp.actual_amount, event.currency)
                              : <span className="text-slate-500 font-normal">--</span>}
                          </td>
                          <td className="py-3 px-3">
                            <span className={`inline-block rounded-md border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${statusColor}`}>
                              {exp.payment_status}
                            </span>
                          </td>
                          <td className="py-3 px-3 text-slate-400">
                            {exp.expense_date ? formatDate(exp.expense_date) : '--'}
                          </td>
                          <td className="py-3 px-3 text-right">
                            <div className="flex items-center justify-end gap-1.5">
                              <button
                                onClick={() => {
                                  setEditingExpense(exp);
                                  setIsExpenseModalOpen(true);
                                }}
                                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
                                title="Edit Expense"
                              >
                                <Edit className="h-3.5 w-3.5" />
                              </button>
                              <button
                                onClick={() => handleDeleteExpenseClick(exp)}
                                className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition"
                                title="Delete Expense"
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: TIMELINE & TASKS */}
      {activeTab === 'tasks' && (
        <div
          role="tabpanel"
          id="panel-tasks"
          aria-labelledby="tab-tasks"
          tabIndex={0}
          className="space-y-6 focus:outline-none"
        >
          {/* Progress Bar & Header */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 shadow-xl space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h3 className="text-base font-bold text-white">Event Task Progress & Milestones</h3>
                <p className="text-xs text-slate-400">
                  {taskSummary.completed} of {taskSummary.total} tasks completed ({taskSummary.progress_percent}%)
                </p>
              </div>
              <button
                type="button"
                onClick={() => {
                  setEditingTask(null);
                  setIsTaskModalOpen(true);
                }}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white shadow-md shadow-indigo-600/30 transition self-start sm:self-auto"
                id="add-task-btn"
              >
                <Plus className="h-4 w-4" />
                <span>Add Task</span>
              </button>
            </div>

            {/* Big Progress Bar */}
            <div className="h-3 w-full rounded-full bg-slate-950 border border-slate-800 overflow-hidden">
              <div
                className="h-full rounded-full bg-indigo-500 transition-all duration-500 shadow-lg shadow-indigo-500/50"
                style={{ width: `${Math.min(Number(taskSummary.progress_percent) || 0, 100)}%` }}
              />
            </div>

            {/* Status Filter Tabs */}
            <div className="flex items-center gap-2 pt-2 overflow-x-auto">
              {[
                { id: 'ALL', label: `All Tasks (${tasks.length})` },
                { id: 'Pending', label: `Pending (${taskSummary.pending || 0})` },
                { id: 'In Progress', label: `In Progress (${taskSummary.in_progress || 0})` },
                { id: 'Completed', label: `Completed (${taskSummary.completed || 0})` },
              ].map((f) => (
                <button
                  key={f.id}
                  onClick={() => setTaskFilter(f.id)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition ${
                    taskFilter === f.id
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'bg-slate-800/80 text-slate-400 hover:text-white hover:bg-slate-800'
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>

          {/* Overdue Section (Highlight) */}
          {overdueTasks.length > 0 && (
            <div className="rounded-2xl border border-rose-500/40 bg-rose-950/20 p-5 space-y-3">
              <div className="flex items-center gap-2 text-rose-300 font-bold text-sm">
                <AlertCircle className="h-4 w-4 text-rose-400" />
                <span>Overdue Milestones ({overdueTasks.length})</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {overdueTasks.map((t) => (
                  <div
                    key={t.id}
                    className="flex items-start justify-between p-3 rounded-xl bg-slate-900 border border-rose-500/30 text-xs"
                  >
                    <div className="flex items-start gap-2.5">
                      <button
                        onClick={() => handleToggleTaskComplete(t)}
                        className="mt-0.5 rounded text-slate-500 hover:text-emerald-400 transition"
                        title="Mark Complete"
                      >
                        <Circle className="h-4 w-4" />
                      </button>
                      <div>
                        <p className="font-bold text-white">{t.title}</p>
                        <span className="text-[10px] text-rose-400 font-medium">
                          Due {formatDate(t.due_date)} (Overdue!)
                        </span>
                      </div>
                    </div>
                    <span className="rounded bg-rose-500/20 text-rose-300 px-2 py-0.5 text-[10px] font-bold">
                      {t.priority}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Upcoming Section (within 7 days) */}
          {upcomingTasks.length > 0 && (
            <div className="rounded-2xl border border-amber-500/30 bg-amber-950/15 p-5 space-y-3">
              <div className="flex items-center gap-2 text-amber-300 font-bold text-sm">
                <Clock className="h-4 w-4 text-amber-400" />
                <span>Upcoming Milestones This Week ({upcomingTasks.length})</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {upcomingTasks.map((t) => (
                  <div
                    key={t.id}
                    className="flex items-start justify-between p-3 rounded-xl bg-slate-900 border border-amber-500/20 text-xs"
                  >
                    <div className="flex items-start gap-2.5">
                      <button
                        onClick={() => handleToggleTaskComplete(t)}
                        className="mt-0.5 rounded text-slate-500 hover:text-emerald-400 transition"
                        title="Mark Complete"
                      >
                        <Circle className="h-4 w-4" />
                      </button>
                      <div>
                        <p className="font-bold text-white">{t.title}</p>
                        <span className="text-[10px] text-amber-400 font-medium">
                          Due {formatDate(t.due_date)}
                        </span>
                      </div>
                    </div>
                    <span className="rounded bg-amber-500/20 text-amber-300 px-2 py-0.5 text-[10px] font-bold">
                      {t.priority}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Filtered Tasks List */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 shadow-xl space-y-4">
            <h3 className="text-base font-bold text-white">Chronological Checklist</h3>

            {filteredTasks.length === 0 ? (
              <p className="text-xs text-slate-500 py-6 text-center italic">
                No tasks match the selected status filter.
              </p>
            ) : (
              <div className="space-y-3">
                {filteredTasks.map((t) => {
                  const isCompleted = t.status === 'Completed';
                  const priorityColor =
                    t.priority === 'High'
                      ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                      : t.priority === 'Medium'
                      ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                      : 'bg-blue-500/10 text-blue-400 border-blue-500/20';

                  return (
                    <div
                      key={t.id}
                      className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-xl border transition ${
                        isCompleted
                          ? 'bg-slate-950/40 border-slate-800/60 opacity-70'
                          : t.is_overdue
                          ? 'bg-slate-900/90 border-rose-500/30'
                          : 'bg-slate-900/90 border-slate-800'
                      }`}
                    >
                      <div className="flex items-start gap-3 min-w-0">
                        {/* Quick complete toggle */}
                        <button
                          onClick={() => handleToggleTaskComplete(t)}
                          className={`mt-0.5 rounded-lg p-1 transition shrink-0 ${
                            isCompleted
                              ? 'text-emerald-400 bg-emerald-500/10 border border-emerald-500/30'
                              : 'text-slate-500 hover:text-white bg-slate-800 border border-slate-700'
                          }`}
                          title={isCompleted ? 'Mark Pending' : 'Mark Completed'}
                        >
                          {isCompleted ? <Check className="h-4 w-4" /> : <Circle className="h-4 w-4" />}
                        </button>

                        <div className="space-y-1 min-w-0">
                          <p
                            className={`text-sm font-semibold truncate ${
                              isCompleted ? 'line-through text-slate-400' : 'text-white'
                            }`}
                          >
                            {t.title}
                          </p>

                          {t.description && (
                            <p className="text-xs text-slate-400 line-clamp-2">{t.description}</p>
                          )}

                          {/* Chips & Badges */}
                          <div className="flex items-center gap-2 flex-wrap pt-1">
                            <span className="rounded bg-slate-800 text-slate-300 px-2 py-0.5 text-[10px] font-medium border border-slate-700">
                              {t.category}
                            </span>
                            <span className={`rounded border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${priorityColor}`}>
                              {t.priority}
                            </span>
                            <span className="flex items-center gap-1 text-[11px] text-slate-400">
                              <Calendar className="h-3 w-3" />
                              <span>{formatDate(t.due_date)}</span>
                            </span>

                            {t.is_overdue && (
                              <span className="rounded bg-rose-500/20 text-rose-300 border border-rose-500/30 px-2 py-0.5 text-[10px] font-bold">
                                Overdue
                              </span>
                            )}

                            {t.is_upcoming && (
                              <span className="rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 px-2 py-0.5 text-[10px] font-bold">
                                Upcoming
                              </span>
                            )}

                            {t.after_event_date && (
                              <span className="rounded bg-purple-500/20 text-purple-300 border border-purple-500/30 px-2 py-0.5 text-[10px] font-bold">
                                Post Event
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Action buttons */}
                      <div className="flex items-center gap-1.5 self-end sm:self-center shrink-0">
                        <button
                          onClick={() => {
                            setEditingTask(t);
                            setIsTaskModalOpen(true);
                          }}
                          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
                          title="Edit Task"
                        >
                          <Edit className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => handleDeleteTaskClick(t)}
                          className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition"
                          title="Delete Task"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 4: VENDORS */}
      {activeTab === 'vendors' && (
        <div
          role="tabpanel"
          id="panel-vendors"
          aria-labelledby="tab-vendors"
          tabIndex={0}
          className="space-y-6 focus:outline-none"
        >
          <VendorsSection event={event} onEventUpdated={fetchEventData} />
        </div>
      )}

      {/* TAB 5: AI ASSISTANT */}
      {activeTab === 'assistant' && (
        <div
          role="tabpanel"
          id="panel-assistant"
          aria-labelledby="tab-assistant"
          tabIndex={0}
          className="space-y-6 focus:outline-none"
        >
          <AssistantSection event={event} onEventUpdated={fetchEventData} />
        </div>
      )}

      {/* TAB 6: THEMES & DECOR */}
      {activeTab === 'themes' && (
        <div
          role="tabpanel"
          id="panel-themes"
          aria-labelledby="tab-themes"
          tabIndex={0}
          className="space-y-6 focus:outline-none"
        >
          <ThemesSection event={event} onEventUpdated={fetchEventData} />
        </div>
      )}

      {/* TAB 7: INVITATIONS */}
      {activeTab === 'invitations' && (
        <div
          role="tabpanel"
          id="panel-invitations"
          aria-labelledby="tab-invitations"
          tabIndex={0}
          className="space-y-6 focus:outline-none"
        >
          <InvitationsSection event={event} />
        </div>
      )}

      {/* TAB 8: AI MASTER PLAN */}
      {activeTab === 'plan' && (
        <div
          role="tabpanel"
          id="panel-plan"
          aria-labelledby="tab-plan"
          tabIndex={0}
          className="space-y-8 focus:outline-none"
        >
          {event.generated_plan ? (
            <div className="space-y-8">
              {/* Plan Header Card */}
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 shadow-xl space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                      <Sparkles className="h-6 w-6" />
                    </div>
                    <div>
                      <h2 className="text-lg font-bold text-white">Stored Plan Directives</h2>
                      <p className="text-xs text-slate-400">
                        Curated by {event.generated_plan.model || 'Gemini'} on {formatDate(event.generated_plan.generated_at || event.created_at)}
                      </p>
                    </div>
                  </div>

                  {event.generated_plan.source === 'demo' ? (
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-500/10 px-3 py-1 text-xs font-semibold text-amber-400 border border-amber-500/30">
                      <Cpu className="h-3.5 w-3.5" />
                      <span>Demo Mode</span>
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-400 border border-emerald-500/30">
                      <Sparkles className="h-3.5 w-3.5" />
                      <span>AI Generated</span>
                    </span>
                  )}
                </div>

                <p className="text-sm text-slate-300 leading-relaxed">
                  {event.generated_plan.overview || 'Comprehensive celebration blueprint.'}
                </p>
              </div>

              {/* Creative Section */}
              <CreativeSection
                theme={event.generated_plan.recommended_theme}
                decorations={event.generated_plan.decoration_suggestions || []}
                catering={event.generated_plan.catering_suggestions || []}
                entertainment={event.generated_plan.entertainment_suggestions || []}
              />

              {/* Logistics & Risks */}
              <LogisticsAndRisks
                vendors={event.generated_plan.vendor_requirements || []}
                risks={event.generated_plan.risks || []}
              />
            </div>
          ) : (
            <div className="p-12 text-center rounded-2xl border border-slate-800 bg-slate-900/40 space-y-3">
              <Sparkles className="h-8 w-8 text-slate-500 mx-auto" />
              <h3 className="text-base font-bold text-white">No AI Plan Attached</h3>
              <p className="text-xs text-slate-400 max-w-sm mx-auto">
                This event was created directly without initial AI generation. You can manage custom budget categories and tasks using the Budget and Timeline tabs.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Reusable Accessible Confirm Dialog */}
      <ConfirmDialog
        isOpen={confirmState.isOpen}
        title={confirmState.title}
        message={confirmState.message}
        confirmLabel={confirmState.confirmLabel}
        isLoading={confirmState.isLoading}
        onConfirm={confirmState.action}
        onCancel={() => setConfirmState((prev) => ({ ...prev, isOpen: false }))}
      />

      {/* Expense Modal (Add / Edit) */}
      <ExpenseModal
        isOpen={isExpenseModalOpen}
        onClose={() => {
          setIsExpenseModalOpen(false);
          setEditingExpense(null);
        }}
        onSubmit={handleExpenseSubmit}
        expense={editingExpense}
        categories={categories}
        currency={event.currency}
        isLoading={isExpenseSubmitting}
      />

      {/* Task Modal (Add / Edit) */}
      <TaskModal
        isOpen={isTaskModalOpen}
        onClose={() => {
          setIsTaskModalOpen(false);
          setEditingTask(null);
        }}
        onSubmit={handleTaskSubmit}
        task={editingTask}
        eventDate={event.event_date}
        isLoading={isTaskSubmitting}
      />
    </div>
  );
}
