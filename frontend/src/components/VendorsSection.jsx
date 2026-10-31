import React, { useState, useEffect, useCallback } from 'react';
import {
  Building2,
  Plus,
  Trash2,
  Edit,
  Filter,
  CheckCircle2,
  AlertCircle,
  Star,
  DollarSign,
  Phone,
  Info,
  AlertTriangle,
} from 'lucide-react';
import VendorModal from './VendorModal';
import ConfirmDialog from './ConfirmDialog';
import {
  listVendors,
  createVendor,
  updateVendor,
  deleteVendor,
  getVendorComparison,
} from '../services/api';
import { formatCurrency } from '../utils/formatters';

const VENDOR_STATUSES = ['Considering', 'Contacted', 'Shortlisted', 'Selected', 'Rejected'];

const VENDOR_CATEGORIES = [
  'Venue',
  'Catering',
  'Decoration',
  'Photography',
  'Entertainment',
  'Makeup',
  'Transportation',
  'Other',
];

const STATUS_BADGE_STYLES = {
  Considering: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
  Contacted: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  Shortlisted: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  Selected: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  Rejected: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
};

export default function VendorsSection({ event, onEventUpdated }) {
  const [vendors, setVendors] = useState([]);
  const [comparison, setComparison] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [categoryFilter, setCategoryFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [activeSubTab, setActiveSubTab] = useState('list'); // 'list' or 'comparison'

  // Modals & Dialogs
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingVendor, setEditingVendor] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusUpdatingId, setStatusUpdatingId] = useState(null);

  const [confirmDelete, setConfirmDelete] = useState({
    isOpen: false,
    vendorId: null,
    vendorName: '',
    isLoading: false,
  });

  const currency = event?.currency || 'INR';

  const loadData = useCallback(async () => {
    if (!event?.id) return;
    setIsLoading(true);
    setError(null);
    try {
      const [vendorList, compData] = await Promise.all([
        listVendors(event.id),
        getVendorComparison(event.id).catch(() => null),
      ]);
      setVendors(vendorList || []);
      setComparison(compData);
    } catch (err) {
      console.error('Failed to load vendors:', err);
      setError(err.message || 'Failed to load vendors.');
    } finally {
      setIsLoading(false);
    }
  }, [event?.id]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Create or Update
  const handleSubmitVendor = async (payload) => {
    setIsSubmitting(true);
    try {
      if (editingVendor) {
        await updateVendor(editingVendor.id, payload);
      } else {
        await createVendor(event.id, payload);
      }
      setIsModalOpen(false);
      setEditingVendor(null);
      await loadData();
      if (onEventUpdated) onEventUpdated();
    } catch (err) {
      alert(err.message || 'Failed to save vendor');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Quick Status Change directly from dropdown
  const handleQuickStatusChange = async (vendorId, newStatus) => {
    setStatusUpdatingId(vendorId);
    try {
      await updateVendor(vendorId, { status: newStatus });
      await loadData();
      if (onEventUpdated) onEventUpdated();
    } catch (err) {
      alert(err.message || 'Failed to update vendor status');
    } finally {
      setStatusUpdatingId(null);
    }
  };

  // Delete Vendor
  const handleDeleteClick = (vendor) => {
    setConfirmDelete({
      isOpen: true,
      vendorId: vendor.id,
      vendorName: vendor.name,
      isLoading: false,
    });
  };

  const handleConfirmDelete = async () => {
    if (!confirmDelete.vendorId) return;
    setConfirmDelete((prev) => ({ ...prev, isLoading: true }));
    try {
      await deleteVendor(confirmDelete.vendorId);
      setConfirmDelete({ isOpen: false, vendorId: null, vendorName: '', isLoading: false });
      await loadData();
      if (onEventUpdated) onEventUpdated();
    } catch (err) {
      alert(err.message || 'Failed to delete vendor');
      setConfirmDelete((prev) => ({ ...prev, isLoading: false }));
    }
  };

  // Filtered vendor list
  const filteredVendors = vendors.filter((v) => {
    if (categoryFilter !== 'ALL' && v.category !== categoryFilter) return false;
    if (statusFilter !== 'ALL' && v.status !== statusFilter) return false;
    return true;
  });

  // Unique categories in vendors list
  const activeCategories = Array.from(new Set(vendors.map((v) => v.category))).filter(Boolean);

  // Helper to extract rating from notes like "[★ 5] Notes..."
  const parseRating = (notes) => {
    if (!notes) return null;
    const m = notes.match(/^\[★\s*([1-5])\]/);
    return m ? parseInt(m[1], 10) : null;
  };

  // Helper to clean rating prefix from notes display
  const cleanNotes = (notes) => {
    if (!notes) return '';
    return notes.replace(/^\[★\s*[1-5]\]\s*/, '');
  };

  const categoriesMissingSelected = comparison?.categories?.filter(
    (c) => c.selected_vendors.length === 0
  ).length || 0;

  const isSelectedOverBudget =
    comparison &&
    Number(comparison.selected_total) > Number(comparison.event_total_budget);

  return (
    <div className="space-y-6">
      {/* Disclaimer Banner */}
      <div className="rounded-2xl border border-amber-500/20 bg-amber-950/15 p-4 text-xs text-amber-300/90 flex items-start gap-3">
        <Info className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="font-semibold text-amber-300">Self-Managed Quotations & Bookings</p>
          <p className="leading-relaxed">
            Quotes are entered by you. EventMate does not verify vendor quotes, availability, or identities, and does not make bookings.
          </p>
        </div>
      </div>

      {/* Global Summary Cards (when comparison data exists) */}
      {comparison && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 space-y-1">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Selected Vendors Total
            </span>
            <div className="text-xl font-bold text-emerald-400">
              {formatCurrency(comparison.selected_total, currency)}
            </div>
            <p className="text-[11px] text-slate-500">
              Sum of quotes for selected vendors
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 space-y-1">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Total Event Budget
            </span>
            <div className="text-xl font-bold text-white">
              {formatCurrency(comparison.event_total_budget, currency)}
            </div>
            <p className="text-[11px] text-slate-500">
              {isSelectedOverBudget ? (
                <span className="text-rose-400 font-semibold">Exceeds total event budget!</span>
              ) : (
                <span className="text-emerald-400 font-semibold">Within event budget</span>
              )}
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 space-y-1">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Categories Missing Selected
            </span>
            <div className="text-xl font-bold text-amber-400">
              {categoriesMissingSelected}
            </div>
            <p className="text-[11px] text-slate-500">
              Categories needing a final decision
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 space-y-1">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Missing Quotes
            </span>
            <div className="text-xl font-bold text-indigo-400">
              {comparison.missing_quotes?.length ?? 0}
            </div>
            <p className="text-[11px] text-slate-500">
              Selected vendors without quote
            </p>
          </div>
        </div>
      )}

      {/* Sub-Tab Navigation & Add Action */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveSubTab('list')}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition ${
              activeSubTab === 'list'
                ? 'bg-indigo-600 text-white shadow'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            All Vendors ({vendors.length})
          </button>
          <button
            onClick={() => setActiveSubTab('comparison')}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition ${
              activeSubTab === 'comparison'
                ? 'bg-indigo-600 text-white shadow'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            Quotation Comparison
          </button>
        </div>

        <button
          onClick={() => {
            setEditingVendor(null);
            setIsModalOpen(true);
          }}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white shadow-lg shadow-indigo-600/30 transition self-start sm:self-auto"
        >
          <Plus className="h-4 w-4" />
          <span>Add Vendor</span>
        </button>
      </div>

      {/* SUB-VIEW 1: VENDOR LIST */}
      {activeSubTab === 'list' && (
        <div className="space-y-4">
          {/* Filters Bar */}
          <div className="flex flex-wrap items-center gap-3 p-3 rounded-2xl border border-slate-800 bg-slate-900/40">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <Filter className="h-3.5 w-3.5" />
              <span>Filter:</span>
            </div>

            {/* Category Filter */}
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-1.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value="ALL">All Categories ({vendors.length})</option>
              {VENDOR_CATEGORIES.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>

            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-1.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value="ALL">All Statuses</option>
              {VENDOR_STATUSES.map((st) => (
                <option key={st} value={st}>
                  {st}
                </option>
              ))}
            </select>

            {(categoryFilter !== 'ALL' || statusFilter !== 'ALL') && (
              <button
                onClick={() => {
                  setCategoryFilter('ALL');
                  setStatusFilter('ALL');
                }}
                className="text-xs text-indigo-400 hover:underline ml-auto"
              >
                Clear filters
              </button>
            )}
          </div>

          {/* Vendors Table */}
          {isLoading ? (
            <div className="p-12 text-center text-slate-400 text-sm">
              <div className="h-6 w-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
              <span>Loading vendors...</span>
            </div>
          ) : filteredVendors.length === 0 ? (
            <div className="p-12 text-center rounded-2xl border border-slate-800 bg-slate-900/40 space-y-3">
              <Building2 className="h-8 w-8 text-slate-500 mx-auto" />
              <h3 className="text-sm font-bold text-white">No Vendors Found</h3>
              <p className="text-xs text-slate-400 max-w-sm mx-auto">
                {vendors.length === 0
                  ? 'No vendors added yet. Click "Add Vendor" to start tracking quotes and comparisons.'
                  : 'No vendors match your active filter criteria.'}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900/60 shadow-xl">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-950/80 uppercase tracking-wider text-[10px] text-slate-400 border-b border-slate-800">
                  <tr>
                    <th scope="col" className="px-4 py-3 font-semibold">Vendor & Contact</th>
                    <th scope="col" className="px-4 py-3 font-semibold">Category</th>
                    <th scope="col" className="px-4 py-3 font-semibold">Status</th>
                    <th scope="col" className="px-4 py-3 font-semibold">Quotation</th>
                    <th scope="col" className="px-4 py-3 font-semibold">Rating</th>
                    <th scope="col" className="px-4 py-3 font-semibold">Notes</th>
                    <th scope="col" className="px-4 py-3 font-semibold text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {filteredVendors.map((vendor) => {
                    const rating = parseRating(vendor.notes);
                    const noteText = cleanNotes(vendor.notes);

                    return (
                      <tr key={vendor.id} className="hover:bg-slate-800/30 transition">
                        {/* Name & Contact */}
                        <td className="px-4 py-3 font-medium text-white max-w-[200px]">
                          <div className="truncate font-semibold">{vendor.name}</div>
                          {vendor.contact_info && (
                            <div className="text-[11px] text-slate-400 truncate flex items-center gap-1 mt-0.5">
                              <Phone className="h-3 w-3 shrink-0" />
                              <span className="truncate">{vendor.contact_info}</span>
                            </div>
                          )}
                        </td>

                        {/* Category */}
                        <td className="px-4 py-3">
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-800 text-[11px] text-slate-300 border border-slate-700/50">
                            {vendor.category}
                          </span>
                        </td>

                        {/* Status & Quick Change */}
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-1.5">
                            <select
                              value={vendor.status}
                              disabled={statusUpdatingId === vendor.id}
                              onChange={(e) => handleQuickStatusChange(vendor.id, e.target.value)}
                              className={`rounded-lg px-2 py-1 text-[11px] font-semibold border transition ${
                                STATUS_BADGE_STYLES[vendor.status] || 'bg-slate-800 text-slate-300'
                              }`}
                            >
                              {VENDOR_STATUSES.map((st) => (
                                <option key={st} value={st} className="bg-slate-900 text-white">
                                  {st}
                                </option>
                              ))}
                            </select>
                            {statusUpdatingId === vendor.id && (
                              <div className="h-3 w-3 border border-indigo-400 border-t-transparent rounded-full animate-spin" />
                            )}
                          </div>
                        </td>

                        {/* Quote */}
                        <td className="px-4 py-3 font-medium">
                          {vendor.quoted_amount !== null && vendor.quoted_amount !== undefined ? (
                            <span className="text-emerald-400 font-bold">
                              {formatCurrency(vendor.quoted_amount, currency)}
                            </span>
                          ) : (
                            <span className="text-slate-500 italic">No quote</span>
                          )}
                        </td>

                        {/* Rating */}
                        <td className="px-4 py-3">
                          {rating ? (
                            <span className="inline-flex items-center gap-0.5 text-amber-400 text-[11px]">
                              {Array.from({ length: rating }).map((_, i) => (
                                <Star key={i} className="h-3 w-3 fill-amber-400 text-amber-400" />
                              ))}
                            </span>
                          ) : (
                            <span className="text-slate-500">—</span>
                          )}
                        </td>

                        {/* Notes */}
                        <td className="px-4 py-3 max-w-[220px]">
                          <p className="text-[11px] text-slate-400 line-clamp-2">
                            {noteText || '—'}
                          </p>
                        </td>

                        {/* Actions */}
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <button
                              onClick={() => {
                                setEditingVendor(vendor);
                                setIsModalOpen(true);
                              }}
                              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
                              title="Edit Vendor"
                            >
                              <Edit className="h-3.5 w-3.5" />
                            </button>
                            <button
                              onClick={() => handleDeleteClick(vendor)}
                              className="p-1.5 rounded-lg text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 transition"
                              title="Delete Vendor"
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
      )}

      {/* SUB-VIEW 2: QUOTATION COMPARISON */}
      {activeSubTab === 'comparison' && (
        <div className="space-y-6">
          {(!comparison || comparison.categories?.length === 0) ? (
            <div className="p-12 text-center rounded-2xl border border-slate-800 bg-slate-900/40 space-y-3">
              <DollarSign className="h-8 w-8 text-slate-500 mx-auto" />
              <h3 className="text-sm font-bold text-white">No Quotation Data Available</h3>
              <p className="text-xs text-slate-400 max-w-sm mx-auto">
                Add vendors with quotation amounts to see category comparisons, lowest quotes, and price differences.
              </p>
            </div>
          ) : (
            <div className="space-y-5">
              {comparison.categories.map((catComp) => {
                const selectedVendorNames = catComp.selected_vendors || [];
                const lowestQuote = catComp.lowest_quote;

                return (
                  <div
                    key={catComp.category}
                    className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 shadow-lg space-y-4"
                  >
                    {/* Category Header */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-white text-base">{catComp.category}</span>
                          <span className="text-[11px] text-slate-400">
                            ({catComp.vendors.length} vendor{catComp.vendors.length !== 1 ? 's' : ''})
                          </span>
                          {catComp.multiple_selected && (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[10px] font-bold">
                              <AlertTriangle className="h-3 w-3" /> Multiple Selected
                            </span>
                          )}
                        </div>
                        <div className="flex flex-wrap items-center gap-3 mt-1 text-xs text-slate-400">
                          {lowestQuote ? (
                            <span>
                              Lowest Quote: <strong className="text-emerald-400">{formatCurrency(lowestQuote, currency)}</strong>
                            </span>
                          ) : (
                            <span className="text-slate-500 italic">No quotes in this category</span>
                          )}
                          {selectedVendorNames.length > 0 ? (
                            <span>
                              Selected: <strong className="text-white">{selectedVendorNames.join(', ')}</strong>
                            </span>
                          ) : (
                            <span className="text-amber-400 font-semibold flex items-center gap-1">
                              <AlertCircle className="h-3 w-3" /> No vendor selected
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Quotation Table for this Category */}
                    <div className="overflow-x-auto rounded-xl border border-slate-800/80">
                      <table className="w-full text-left text-xs text-slate-300">
                        <thead className="bg-slate-950/60 uppercase tracking-wider text-[10px] text-slate-400 border-b border-slate-800">
                          <tr>
                            <th className="px-3 py-2 font-semibold">Vendor</th>
                            <th className="px-3 py-2 font-semibold">Status</th>
                            <th className="px-3 py-2 font-semibold">Quote</th>
                            <th className="px-3 py-2 font-semibold">Comparison Highlights</th>
                            <th className="px-3 py-2 font-semibold text-right">Quick Action</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/50">
                          {catComp.vendors.map((v) => {
                            const isLowest = v.is_lowest;
                            const isSelected = v.is_selected;

                            return (
                              <tr
                                key={v.id}
                                className={`transition ${
                                  isSelected
                                    ? 'bg-emerald-950/20'
                                    : isLowest
                                    ? 'bg-indigo-950/20'
                                    : 'hover:bg-slate-800/20'
                                }`}
                              >
                                <td className="px-3 py-2.5 font-medium text-white">
                                  <span>{v.name}</span>
                                </td>
                                <td className="px-3 py-2.5">
                                  <span
                                    className={`inline-block px-2 py-0.5 rounded text-[10px] font-semibold border ${
                                      STATUS_BADGE_STYLES[v.status] || 'bg-slate-800 text-slate-400'
                                    }`}
                                  >
                                    {v.status}
                                  </span>
                                </td>
                                <td className="px-3 py-2.5 font-bold">
                                  {v.quoted_amount !== null && v.quoted_amount !== undefined ? (
                                    <span className={isLowest ? 'text-emerald-400' : 'text-slate-200'}>
                                      {formatCurrency(v.quoted_amount, currency)}
                                    </span>
                                  ) : (
                                    <span className="text-slate-500 italic font-normal">No quote</span>
                                  )}
                                </td>
                                <td className="px-3 py-2.5">
                                  <div className="flex items-center gap-1.5 flex-wrap">
                                    {isLowest && (
                                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[10px] font-bold">
                                        <CheckCircle2 className="h-3 w-3" />
                                        <span>Lowest Quote</span>
                                      </span>
                                    )}
                                    {isSelected && (
                                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-[10px] font-bold">
                                        Selected
                                      </span>
                                    )}
                                    {v.difference_from_lowest && v.difference_from_lowest !== '0.00' && v.difference_from_lowest !== '0' && (
                                      <span className="text-[11px] text-amber-300">
                                        +{formatCurrency(v.difference_from_lowest, currency)} vs lowest
                                      </span>
                                    )}
                                  </div>
                                </td>
                                <td className="px-3 py-2.5 text-right">
                                  {v.status !== 'Selected' && (
                                    <button
                                      disabled={statusUpdatingId === v.id}
                                      onClick={() => handleQuickStatusChange(v.id, 'Selected')}
                                      className="px-2.5 py-1 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 border border-emerald-500/30 text-[11px] font-semibold transition disabled:opacity-50"
                                    >
                                      Select Vendor
                                    </button>
                                  )}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Vendor Add / Edit Modal */}
      <VendorModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setEditingVendor(null);
        }}
        onSubmit={handleSubmitVendor}
        vendor={editingVendor}
        currency={currency}
        isLoading={isSubmitting}
      />

      {/* Confirm Delete Dialog */}
      <ConfirmDialog
        isOpen={confirmDelete.isOpen}
        title="Delete Vendor"
        message={`Are you sure you want to delete "${confirmDelete.vendorName}"? This action cannot be undone.`}
        confirmLabel="Delete Vendor"
        isLoading={confirmDelete.isLoading}
        onConfirm={handleConfirmDelete}
        onCancel={() =>
          setConfirmDelete({ isOpen: false, vendorId: null, vendorName: '', isLoading: false })
        }
      />
    </div>
  );
}
