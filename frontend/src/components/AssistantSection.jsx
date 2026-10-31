import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  RotateCcw,
  Sparkles,
  Bot,
  User,
  AlertCircle,
  CheckCircle2,
  Clock,
  Check,
  X,
  AlertTriangle,
  ArrowRight,
  SlidersHorizontal,
  MessageSquare,
} from 'lucide-react';
import { askAssistant, proposeChanges, applyChanges, discardProposal } from '../services/api';
import { formatCurrency } from '../utils/formatters';
import ConfirmDialog from './ConfirmDialog';

export default function AssistantSection({ event, onEventUpdated }) {
  const [mode, setMode] = useState('ask'); // 'ask' | 'modify'
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorState, setErrorState] = useState(null); // { message, lastInput, lastMode }
  const [confirmDialog, setConfirmDialog] = useState({
    isOpen: false,
    title: '',
    message: '',
    confirmLabel: 'Apply',
    action: null,
    isLoading: false,
  });

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const currency = event?.currency || 'INR';

  // Static suggested prompt chips
  const askSuggestedChips = [
    'How can I save money on catering?',
    'What tasks are overdue or urgent?',
    'Are my budget allocations balanced?',
  ];

  const modifySuggestedChips = [
    'Move 20000 from Venue to Catering',
    'Increase total budget to 650000 and allocate 50000 to Decor',
    'Add task to finalize guest seating 5 days before event',
  ];

  const handleChipClick = (promptText, targetMode = mode) => {
    if (targetMode !== mode) {
      setMode(targetMode);
    }
    setInputValue(promptText);
    textareaRef.current?.focus();
  };

  const handleClearChat = () => {
    setMessages([]);
    setErrorState(null);
  };

  const handleSendMessage = async (textToSend = inputValue, currentMode = mode) => {
    const trimmed = textToSend.trim();
    if (!trimmed || isLoading) return;

    setErrorState(null);

    // Append user message
    const userMsg = {
      id: `usr-${Date.now()}`,
      role: 'user',
      content: trimmed,
      mode: currentMode,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputValue('');
    setIsLoading(true);

    try {
      if (currentMode === 'ask') {
        // Send last 10 messages as history
        const history = messages
          .filter((m) => m.role === 'user' || m.role === 'assistant')
          .slice(-10)
          .map((m) => ({
            role: m.role,
            content: m.content || '',
          }));

        const res = await askAssistant(event.id, {
          message: trimmed,
          history,
        });

        const assistantMsg = {
          id: `ast-${Date.now()}`,
          role: 'assistant',
          content: res.reply,
          recommendations: res.recommendations || [],
          suggested_modification_prompts: res.suggested_modification_prompts || [],
          source: res.source,
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, assistantMsg]);
      } else {
        // Modify mode -> propose-changes
        const res = await proposeChanges(event.id, { message: trimmed });

        if (res.clarification) {
          const clarMsg = {
            id: `clr-${Date.now()}`,
            role: 'assistant',
            content: res.clarification,
            isClarification: true,
            timestamp: new Date(),
          };
          setMessages((prev) => [...prev, clarMsg]);
        } else if (res.proposal) {
          const propMsg = {
            id: `prp-${Date.now()}`,
            role: 'proposal',
            proposal: res.proposal,
            originalMessage: trimmed,
            proposalState: 'pending', // 'pending' | 'applied' | 'discarded' | 'stale'
            timestamp: new Date(),
          };
          setMessages((prev) => [...prev, propMsg]);
        }
      }
    } catch (err) {
      console.error('Assistant error:', err);
      setErrorState({
        message: err.message || 'Failed to communicate with assistant. Please try again.',
        lastInput: trimmed,
        lastMode: currentMode,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleApplyProposalClick = (msgId, proposal) => {
    setConfirmDialog({
      isOpen: true,
      title: 'Apply Plan Modifications?',
      message: `You are about to apply changes: "${proposal.summary}". Budget category allocations and tasks will be updated in the database. Existing expenses and original plans will remain untouched.`,
      confirmLabel: 'Confirm & Apply Changes',
      isLoading: false,
      action: async () => {
        setConfirmDialog((prev) => ({ ...prev, isLoading: true }));
        try {
          const res = await applyChanges(event.id, {
            proposal_id: proposal.proposal_id,
            confirm: true,
          });

          // Mark proposal message as applied
          setMessages((prev) =>
            prev.map((m) => (m.id === msgId ? { ...m, proposalState: 'applied' } : m))
          );

          // Add UI confirmation message
          const appliedMsg = {
            id: `applied-${Date.now()}`,
            role: 'system',
            content: `Changes applied successfully! ${res.message || ''}`,
            timestamp: new Date(),
          };
          setMessages((prev) => [...prev, appliedMsg]);

          // Refresh event in parent
          if (onEventUpdated) {
            await onEventUpdated();
          }

          setConfirmDialog((prev) => ({ ...prev, isOpen: false, isLoading: false }));
        } catch (err) {
          console.error('Apply failed:', err);
          const isStale = err.status === 409 || err.message?.toLowerCase().includes('stale') || err.message?.toLowerCase().includes('expired');
          if (isStale) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === msgId
                  ? {
                      ...m,
                      proposalState: 'stale',
                      staleReason: err.message || 'Proposal is stale or expired.',
                    }
                  : m
              )
            );
          }
          alert(`Could not apply proposal: ${err.message}`);
          setConfirmDialog((prev) => ({ ...prev, isOpen: false, isLoading: false }));
        }
      },
    });
  };

  const handleDiscardProposalClick = async (msgId, proposalId) => {
    try {
      await discardProposal(event.id, proposalId);
      setMessages((prev) =>
        prev.map((m) => (m.id === msgId ? { ...m, proposalState: 'discarded' } : m))
      );
    } catch (err) {
      alert(`Could not discard proposal: ${err.message}`);
    }
  };

  const handleRequestNewProposal = (originalText) => {
    setMode('modify');
    handleSendMessage(originalText, 'modify');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="space-y-6">
      {/* Mode Control & Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Bot className="h-5 w-5 text-indigo-400" />
            <span>AI Event Co-Planner</span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Ask questions about current plans or request safe, deterministic modifications.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Segmented Radio Group */}
          <div
            role="radiogroup"
            aria-label="Assistant Interaction Mode"
            className="flex items-center rounded-xl bg-slate-900 border border-slate-800 p-1 text-xs"
          >
            <button
              type="button"
              role="radio"
              aria-checked={mode === 'ask'}
              onClick={() => setMode('ask')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-semibold transition cursor-pointer ${
                mode === 'ask'
                  ? 'bg-indigo-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <MessageSquare className="h-3.5 w-3.5" />
              <span>Ask Advice</span>
            </button>
            <button
              type="button"
              role="radio"
              aria-checked={mode === 'modify'}
              onClick={() => setMode('modify')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-semibold transition cursor-pointer ${
                mode === 'modify'
                  ? 'bg-indigo-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <SlidersHorizontal className="h-3.5 w-3.5" />
              <span>Modify Plan</span>
            </button>
          </div>

          {messages.length > 0 && (
            <button
              type="button"
              onClick={handleClearChat}
              className="px-2.5 py-1.5 text-xs text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
              title="Clear current chat view"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Chat Thread Panel */}
      <div
        role="log"
        aria-live="polite"
        className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 sm:p-6 min-h-[420px] max-h-[600px] overflow-y-auto space-y-4"
      >
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center space-y-4">
            <div className="h-12 w-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              <Bot className="h-6 w-6" />
            </div>
            <div className="space-y-1 max-w-md">
              <h3 className="text-sm font-bold text-white">
                {mode === 'ask' ? 'Ask questions about your event' : 'Safely modify budgets & timeline'}
              </h3>
              <p className="text-xs text-slate-400">
                {mode === 'ask'
                  ? 'In Ask mode, the assistant provides tailored guidance without touching your database records.'
                  : 'In Modify mode, the AI proposes structured deltas. You can preview, confirm, or discard changes before they are applied.'}
              </p>
            </div>

            {/* Suggested prompt chips */}
            <div className="pt-2 flex flex-wrap justify-center gap-2 max-w-lg">
              {(mode === 'ask' ? askSuggestedChips : modifySuggestedChips).map((chip, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleChipClick(chip)}
                  className="px-3 py-1.5 rounded-full border border-slate-800 bg-slate-900/80 hover:bg-slate-800 hover:border-indigo-500/40 text-xs text-slate-300 transition text-left cursor-pointer"
                >
                  {chip}
                </button>
              ))}
            </div>

            <p className="text-[11px] text-slate-500 pt-4">
              Chat history is stored locally in this session.
            </p>
          </div>
        ) : (
          messages.map((msg) => (
            <div key={msg.id} className="space-y-2">
              {/* User Message */}
              {msg.role === 'user' && (
                <div className="flex justify-end gap-2.5">
                  <div className="max-w-[85%] sm:max-w-[70%] rounded-2xl bg-indigo-600 px-4 py-2.5 text-xs sm:text-sm text-white shadow-md">
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                    <div className="flex items-center justify-end gap-1.5 mt-1 text-[10px] text-indigo-200">
                      <span>{msg.mode === 'modify' ? 'Modify' : 'Ask'}</span>
                    </div>
                  </div>
                  <div className="h-7 w-7 rounded-full bg-indigo-500/20 text-indigo-300 flex items-center justify-center shrink-0">
                    <User className="h-4 w-4" />
                  </div>
                </div>
              )}

              {/* Assistant Message (Ask mode or Clarification) */}
              {msg.role === 'assistant' && (
                <div className="flex justify-start gap-2.5">
                  <div className="h-7 w-7 rounded-full bg-slate-800 text-indigo-400 flex items-center justify-center shrink-0 border border-slate-700">
                    <Bot className="h-4 w-4" />
                  </div>
                  <div className="max-w-[85%] sm:max-w-[75%] space-y-3">
                    <div className="rounded-2xl bg-slate-800/80 border border-slate-700/60 p-4 text-xs sm:text-sm text-slate-100 shadow-md space-y-3">
                      {msg.source === 'demo' && (
                        <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-amber-500/10 border border-amber-500/20 text-[10px] font-semibold text-amber-300 uppercase">
                          <span>Demo Mode</span>
                        </div>
                      )}

                      <p className="whitespace-pre-wrap">{msg.content}</p>

                      {/* Recommendations */}
                      {msg.recommendations && msg.recommendations.length > 0 && (
                        <div className="space-y-2 pt-2 border-t border-slate-700/50">
                          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                            Recommendations
                          </h4>
                          <div className="space-y-1.5">
                            {msg.recommendations.map((rec, i) => (
                              <div key={i} className="rounded-lg bg-slate-900/60 p-2.5 border border-slate-800 text-xs">
                                <span className="font-semibold text-white block">{rec.title}</span>
                                <span className="text-slate-300 mt-0.5 block">{rec.detail}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Disclaimer footer */}
                      <p className="text-[10px] text-slate-400 italic pt-1">
                        Recommendation only. No changes were made.
                      </p>
                    </div>

                    {/* Suggested modification chips */}
                    {msg.suggested_modification_prompts && msg.suggested_modification_prompts.length > 0 && (
                      <div className="space-y-1 pl-1">
                        <span className="text-[10px] font-semibold text-slate-400">
                          Suggested plan modifications:
                        </span>
                        <div className="flex flex-wrap gap-1.5">
                          {msg.suggested_modification_prompts.map((chip, idx) => (
                            <button
                              key={idx}
                              type="button"
                              onClick={() => handleChipClick(chip, 'modify')}
                              className="px-2.5 py-1 rounded-lg bg-indigo-950/30 border border-indigo-500/30 hover:bg-indigo-900/40 text-xs text-indigo-300 transition flex items-center gap-1 cursor-pointer"
                            >
                              <span>{chip}</span>
                              <ArrowRight className="h-3 w-3" />
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Proposal Card (Modify mode) */}
              {msg.role === 'proposal' && (
                <div className="flex justify-start gap-2.5">
                  <div className="h-7 w-7 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center shrink-0 border border-indigo-500/30">
                    <SlidersHorizontal className="h-4 w-4" />
                  </div>
                  <div className="w-full max-w-[95%] sm:max-w-[85%] rounded-2xl bg-slate-800/90 border border-indigo-500/30 p-5 text-xs text-slate-100 shadow-xl space-y-4">
                    {/* Header with status badge */}
                    <div className="flex items-center justify-between pb-3 border-b border-slate-700">
                      <div>
                        <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400 block">
                          Plan Modification Proposal
                        </span>
                        <h4 className="text-sm font-bold text-white mt-0.5">{msg.proposal.summary}</h4>
                      </div>

                      <div>
                        {msg.proposalState === 'applied' && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-xs font-semibold">
                            <Check className="h-3 w-3" />
                            <span>Applied</span>
                          </span>
                        )}
                        {msg.proposalState === 'discarded' && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-slate-700 text-slate-300 text-xs font-semibold">
                            <X className="h-3 w-3" />
                            <span>Discarded</span>
                          </span>
                        )}
                        {msg.proposalState === 'stale' && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-rose-500/20 border border-rose-500/30 text-rose-300 text-xs font-semibold">
                            <AlertTriangle className="h-3 w-3" />
                            <span>Stale or Expired</span>
                          </span>
                        )}
                        {msg.proposalState === 'pending' && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-amber-500/20 border border-amber-500/30 text-amber-300 text-xs font-semibold">
                            <Clock className="h-3 w-3" />
                            <span>Pending Confirmation</span>
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Budget Adjustments Table */}
                    {msg.proposal.preview?.budget?.categories?.length > 0 && (
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-slate-200">Budget Adjustments</span>
                          <span className="text-[11px] text-slate-400">
                            {msg.proposal.preview.budget.balanced ? (
                              <span className="text-emerald-400 font-semibold">Balanced Total</span>
                            ) : (
                              <span className="text-amber-400 font-semibold">Unbalanced Delta</span>
                            )}
                          </span>
                        </div>
                        <div className="overflow-x-auto rounded-xl border border-slate-700 bg-slate-900/60">
                          <table className="w-full text-left text-xs">
                            <thead className="bg-slate-800/80 text-slate-400 font-medium">
                              <tr>
                                <th className="p-2.5">Category</th>
                                <th className="p-2.5">Before</th>
                                <th className="p-2.5">Delta</th>
                                <th className="p-2.5">After</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-800 text-slate-200">
                              {msg.proposal.preview.budget.categories.map((c, i) => (
                                <tr key={i}>
                                  <td className="p-2.5 font-semibold text-white">{c.name}</td>
                                  <td className="p-2.5">{formatCurrency(c.before, currency)}</td>
                                  <td className={`p-2.5 font-bold ${c.delta.startsWith('+') ? 'text-emerald-400' : 'text-rose-400'}`}>
                                    {c.delta} {currency}
                                  </td>
                                  <td className="p-2.5 font-semibold text-white">{formatCurrency(c.after, currency)}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}

                    {/* Tasks to Add */}
                    {msg.proposal.preview?.tasks_to_add?.length > 0 && (
                      <div className="space-y-2">
                        <span className="text-xs font-bold text-slate-200 block">Tasks to Add</span>
                        <div className="space-y-1.5">
                          {msg.proposal.preview.tasks_to_add.map((t, idx) => (
                            <div key={idx} className="rounded-xl border border-slate-700 bg-slate-900/60 p-2.5 flex items-center justify-between">
                              <div>
                                <span className="font-semibold text-white block">{t.title}</span>
                                <span className="text-[11px] text-slate-400">{t.category} • Due: {t.due_date}</span>
                              </div>
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-500/20 text-indigo-300">
                                {t.priority}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Tasks to Update */}
                    {msg.proposal.preview?.tasks_to_update?.length > 0 && (
                      <div className="space-y-2">
                        <span className="text-xs font-bold text-slate-200 block">Tasks to Update</span>
                        <div className="space-y-1.5">
                          {msg.proposal.preview.tasks_to_update.map((t, idx) => (
                            <div key={idx} className="rounded-xl border border-slate-700 bg-slate-900/60 p-2.5 flex items-center justify-between">
                              <div>
                                <span className="font-semibold text-white block">{t.title}</span>
                                <span className="text-[11px] text-slate-400">
                                  Due: {t.old_due_date} → <strong className="text-white">{t.new_due_date}</strong>
                                </span>
                              </div>
                              <span className="text-[11px] text-slate-300">
                                Priority: {t.old_priority} → <strong className="text-white">{t.new_priority}</strong>
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Warnings */}
                    {msg.proposal.warnings && msg.proposal.warnings.length > 0 && (
                      <div className="rounded-xl bg-amber-950/20 border border-amber-500/30 p-2.5 text-xs text-amber-300 space-y-1">
                        {msg.proposal.warnings.map((w, i) => (
                          <div key={i} className="flex items-center gap-1.5">
                            <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                            <span>{w}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Unchanged note & expiry */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-[11px] text-slate-400 pt-1 border-t border-slate-700/60">
                      <span>{msg.proposal.preview?.unchanged || 'Expenses and the original AI plan are not modified.'}</span>
                      {msg.proposal.expires_at && msg.proposalState === 'pending' && (
                        <span>Valid for 30 minutes</span>
                      )}
                    </div>

                    {/* Action Buttons for Proposal */}
                    {msg.proposalState === 'pending' && (
                      <div className="flex items-center gap-2 pt-2">
                        <button
                          type="button"
                          onClick={() => handleApplyProposalClick(msg.id, msg.proposal)}
                          className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs transition flex items-center gap-1.5 shadow-md shadow-emerald-600/20 cursor-pointer"
                        >
                          <Check className="h-3.5 w-3.5" />
                          <span>Apply changes</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDiscardProposalClick(msg.id, msg.proposal.proposal_id)}
                          className="px-3 py-2 rounded-xl border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white font-medium text-xs transition cursor-pointer"
                        >
                          Discard
                        </button>
                      </div>
                    )}

                    {/* Stale recovery button */}
                    {msg.proposalState === 'stale' && (
                      <div className="pt-2">
                        <button
                          type="button"
                          onClick={() => handleRequestNewProposal(msg.originalMessage)}
                          className="px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition flex items-center gap-1.5 cursor-pointer"
                        >
                          <RotateCcw className="h-3.5 w-3.5" />
                          <span>Request a new proposal</span>
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* System message */}
              {msg.role === 'system' && (
                <div className="flex justify-center">
                  <div className="rounded-xl bg-emerald-950/30 border border-emerald-500/30 px-3.5 py-1.5 text-xs text-emerald-300 font-medium flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4" />
                    <span>{msg.content}</span>
                  </div>
                </div>
              )}
            </div>
          ))
        )}

        {/* Loading Indicator */}
        {isLoading && (
          <div className="flex items-center gap-2 text-indigo-400 text-xs py-2 pl-2">
            <div className="h-2 w-2 rounded-full bg-indigo-400 animate-ping" />
            <span>AI is reviewing event context...</span>
          </div>
        )}

        {/* Error Bubble with Retry */}
        {errorState && (
          <div className="rounded-xl border border-rose-500/40 bg-rose-950/20 p-3 text-xs text-rose-300 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
              <span>{errorState.message}</span>
            </div>
            <button
              type="button"
              onClick={() => handleSendMessage(errorState.lastInput, errorState.lastMode)}
              className="px-2.5 py-1 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 font-semibold transition shrink-0 cursor-pointer"
            >
              Retry
            </button>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Composer */}
      <div className="space-y-2">
        <div className="relative rounded-2xl border border-slate-800 bg-slate-900/80 p-2 focus-within:border-indigo-500/80 transition">
          <textarea
            ref={textareaRef}
            id="assistant-input-textarea"
            rows={2}
            value={inputValue}
            maxLength={2000}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              mode === 'ask'
                ? "Ask about budgeting, vendor negotiation, schedule... (Press Enter to send, Shift+Enter for newline)"
                : "Describe changes to propose (e.g. 'Move 20000 from venue to catering')..."
            }
            className="w-full bg-transparent px-3 py-1.5 text-xs sm:text-sm text-slate-100 placeholder-slate-500 focus:outline-none resize-none"
            disabled={isLoading}
          />

          <div className="flex items-center justify-between pt-1 border-t border-slate-800/60 px-2">
            <span className="text-[10px] text-slate-500">
              {inputValue.length}/2000 chars
            </span>

            <button
              type="button"
              id="assistant-send-btn"
              onClick={() => handleSendMessage()}
              disabled={!inputValue.trim() || isLoading}
              className="px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-semibold transition flex items-center gap-1.5 cursor-pointer shadow-md shadow-indigo-600/20"
            >
              <Send className="h-3 w-3" />
              <span>Send</span>
            </button>
          </div>
        </div>
      </div>

      {/* Reusable ConfirmDialog */}
      <ConfirmDialog
        isOpen={confirmDialog.isOpen}
        title={confirmDialog.title}
        message={confirmDialog.message}
        confirmLabel={confirmDialog.confirmLabel}
        onConfirm={confirmDialog.action}
        onCancel={() => setConfirmDialog((prev) => ({ ...prev, isOpen: false }))}
        isLoading={confirmDialog.isLoading}
      />
    </div>
  );
}

