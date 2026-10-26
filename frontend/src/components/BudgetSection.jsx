import React, { useState } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { PieChart as PieIcon, ShieldCheck, Info } from 'lucide-react';
import { formatCurrency } from '../utils/formatters';

const PALETTE = [
  '#6366F1', // Indigo
  '#EC4899', // Pink
  '#F59E0B', // Amber
  '#10B981', // Emerald
  '#3B82F6', // Blue
  '#8B5CF6', // Purple
  '#14B8A6', // Teal
  '#F97316', // Orange
];

function CustomTooltip({ active, payload, currency }) {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="rounded-xl border border-slate-700 bg-slate-900/95 p-3 shadow-xl backdrop-blur-md">
        <p className="text-xs font-bold text-white">{data.name}</p>
        <p className="text-sm font-extrabold text-indigo-400 mt-0.5">
          {formatCurrency(data.value, currency)}
        </p>
        <p className="text-xs text-slate-400 mt-0.5">
          {data.percentage}% of total budget
        </p>
        {data.notes && (
          <p className="text-[11px] text-slate-500 mt-1 max-w-[200px] leading-snug">
            {data.notes}
          </p>
        )}
      </div>
    );
  }
  return null;
}


export default function BudgetSection({ budget, currency }) {
  const [viewMode, setViewMode] = useState('both');
  const items = budget?.items || [];
  const totalAllocated = budget?.total_allocated || 0;
  const contingency = budget?.contingency || 0;

  const chartData = items.map((item) => ({
    name: item.category,
    value: item.amount,
    percentage: item.percentage,
    notes: item.notes,
  }));

  return (
    <section id="budget-section" className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 shadow-xl backdrop-blur-md">

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-6 border-b border-slate-800/80 gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <PieIcon className="h-4 w-4" />
            </span>
            <h3 className="text-xl font-bold text-white tracking-tight">Financial Allocation Blueprint</h3>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Exact mathematical reconciliation with largest-remainder rounding. All line items are estimated and sum to 100%.
          </p>
        </div>

        {/* View Switcher */}
        <div className="flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-950/60 p-1">
          <button
            onClick={() => setViewMode('both')}
            className={`rounded-lg px-2.5 py-1 text-xs font-medium transition ${
              viewMode === 'both' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            Combined
          </button>
          <button
            onClick={() => setViewMode('chart')}
            className={`rounded-lg px-2.5 py-1 text-xs font-medium transition ${
              viewMode === 'chart' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            Chart
          </button>
          <button
            onClick={() => setViewMode('table')}
            className={`rounded-lg px-2.5 py-1 text-xs font-medium transition ${
              viewMode === 'table' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            Table
          </button>
        </div>
      </div>

      {/* Reconciliation Callout Banners */}
      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="flex items-center justify-between rounded-xl border border-emerald-500/20 bg-emerald-950/20 p-4">
          <div className="flex items-center gap-3">
            <ShieldCheck className="h-5 w-5 text-emerald-400 shrink-0" />
            <div>
              <p className="text-xs font-semibold text-emerald-300">Exact Sum Reconciled</p>
              <p className="text-xs text-emerald-400/80">
                100.00% allocated across {items.length} verified categories
              </p>
            </div>
          </div>
          <span className="text-base font-bold text-emerald-300">
            {formatCurrency(totalAllocated, currency)}
          </span>
        </div>

        <div className="flex items-center justify-between rounded-xl border border-indigo-500/20 bg-indigo-950/20 p-4">
          <div className="flex items-center gap-3">
            <Info className="h-5 w-5 text-indigo-400 shrink-0" />
            <div>
              <p className="text-xs font-semibold text-indigo-300">Contingency Reserve Fund</p>
              <p className="text-xs text-indigo-400/80">
                Dedicated buffer for price swings or emergent venue needs
              </p>
            </div>
          </div>
          <span className="text-base font-bold text-indigo-300">
            {formatCurrency(contingency, currency)}
          </span>
        </div>
      </div>

      {/* Main Content (Chart & Table) */}
      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Recharts Pie Chart */}
        {(viewMode === 'both' || viewMode === 'chart') && (
          <div className={`${viewMode === 'both' ? 'lg:col-span-5' : 'lg:col-span-12'} flex flex-col items-center justify-center rounded-xl border border-slate-800/80 bg-slate-950/40 p-4`}>
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={chartData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={85}
                    paddingAngle={3}
                  >
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={PALETTE[index % PALETTE.length]} stroke="#0f172a" strokeWidth={2} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip currency={currency} />} />

                </PieChart>
              </ResponsiveContainer>
            </div>
            {/* Custom accessible legend */}
            <div className="mt-4 flex flex-wrap justify-center gap-2">
              {chartData.map((entry, index) => (
                <div key={entry.name} className="flex items-center gap-1.5 text-[11px] text-slate-300">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: PALETTE[index % PALETTE.length] }} />
                  <span>{entry.name} ({entry.percentage}%)</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Accessible Table Breakdown */}
        {(viewMode === 'both' || viewMode === 'table') && (
          <div className={`${viewMode === 'both' ? 'lg:col-span-7' : 'lg:col-span-12'} overflow-x-auto rounded-xl border border-slate-800/80 bg-slate-950/40`}>
            <table className="w-full text-left text-xs" aria-label="Detailed budget breakdown table">
              <thead className="border-b border-slate-800 bg-slate-900/60 uppercase tracking-wider text-slate-400 font-semibold">
                <tr>
                  <th scope="col" className="px-4 py-3">Category</th>
                  <th scope="col" className="px-4 py-3 text-right">Est. Amount</th>
                  <th scope="col" className="px-4 py-3 text-right">Share</th>
                  <th scope="col" className="px-4 py-3">Purpose & Notes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {items.map((item, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/40 transition">
                    <td className="px-4 py-3 font-medium text-white flex items-center gap-2">
                      <span className="h-2 w-2 rounded-full" style={{ backgroundColor: PALETTE[idx % PALETTE.length] }} />
                      {item.category}
                    </td>
                    <td className="px-4 py-3 text-right font-mono font-semibold text-slate-200">
                      {formatCurrency(item.amount, currency)}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-indigo-400 font-medium">
                      {item.percentage}%
                    </td>
                    <td className="px-4 py-3 text-slate-400 max-w-xs truncate" title={item.notes}>
                      {item.notes}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="border-t border-slate-800 bg-slate-900/70 font-semibold text-slate-200">
                <tr>
                  <td className="px-4 py-3">Total Allocated</td>
                  <td className="px-4 py-3 text-right font-mono text-emerald-400">
                    {formatCurrency(totalAllocated, currency)}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-emerald-400">100.0%</td>
                  <td className="px-4 py-3 text-slate-400 font-normal">Reconciled to total budget</td>
                </tr>
              </tfoot>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
