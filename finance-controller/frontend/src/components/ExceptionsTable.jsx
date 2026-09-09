import { useState, useMemo } from 'react';

const STATUS_LABELS = {
  MISSING_FROM_GATEWAY: 'Missing gateway',
  MISSING_FROM_BANK: 'Missing bank',
  AMOUNT_MISMATCH: 'Amount mismatch',
  DUPLICATE_UTR: 'Duplicate UTR',
  STATUS_MISMATCH: 'Status mismatch',
};

function formatAmount(value) {
  if (value === null || value === undefined) return '—';
  return `₹${Number(value).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function ExceptionsTable({ exceptions }) {
  const [filter, setFilter] = useState('ALL');

  const statusesPresent = useMemo(
    () => Array.from(new Set(exceptions.map((e) => e.reconciliation_status))),
    [exceptions]
  );

  const filtered = filter === 'ALL' ? exceptions : exceptions.filter((e) => e.reconciliation_status === filter);

  return (
    <div className="border border-line rounded-sm bg-white flex flex-col h-full">
      <div className="px-5 pt-4 pb-3 border-b border-line">
        <h2 className="font-serif text-lg text-ink mb-3">Exceptions ({exceptions.length})</h2>
        <div className="flex flex-wrap gap-1.5">
          <FilterTab label="All" active={filter === 'ALL'} onClick={() => setFilter('ALL')} />
          {statusesPresent.map((s) => (
            <FilterTab
              key={s}
              label={STATUS_LABELS[s] || s}
              active={filter === s}
              onClick={() => setFilter(s)}
            />
          ))}
        </div>
      </div>

      <div className="overflow-auto flex-1">
        {filtered.length === 0 ? (
          <p className="text-sm text-steel p-5">No records in this view.</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="sticky top-0 bg-white border-b border-line">
              <tr>
                <th className="px-5 py-2 font-medium text-steel text-xs">Order</th>
                <th className="px-5 py-2 font-medium text-steel text-xs">Reason</th>
                <th className="px-5 py-2 font-medium text-steel text-xs text-right">Expected</th>
                <th className="px-5 py-2 font-medium text-steel text-xs text-right">Delta</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {filtered.map((exc) => (
                <tr key={exc.order_id} className="hover:bg-paper">
                  <td className="px-5 py-3 align-top">
                    <p className="font-mono text-xs text-ink">{exc.order_id}</p>
                    <p className="font-mono text-[11px] text-steel">{exc.utr || '—'}</p>
                  </td>
                  <td className="px-5 py-3 align-top max-w-xs">
                    <span className="inline-block text-xs text-amber bg-amber-soft px-1.5 py-0.5 rounded-sm mb-1">
                      {STATUS_LABELS[exc.reconciliation_status] || exc.reconciliation_status}
                    </span>
                    <p className="text-xs text-steel">{exc.exception_reason}</p>
                  </td>
                  <td className="px-5 py-3 align-top text-right font-mono text-xs tabular-nums">
                    {formatAmount(exc.expected_settlement)}
                  </td>
                  <td className="px-5 py-3 align-top text-right font-mono text-xs tabular-nums text-amber">
                    {exc.discrepancy ? formatAmount(Math.abs(exc.discrepancy)) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function FilterTab({ label, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`text-xs px-2.5 py-1 rounded-sm border ${
        active ? 'bg-ink text-white border-ink' : 'border-line text-steel hover:border-ink hover:text-ink'
      }`}
    >
      {label}
    </button>
  );
}
