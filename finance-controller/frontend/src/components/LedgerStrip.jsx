export default function LedgerStrip({ summary }) {
  if (!summary) {
    return (
      <div className="border border-line rounded-sm bg-white px-6 py-8 text-steel text-sm">
        No reconciliation batch has been run yet.
      </div>
    );
  }

  const stats = [
    { label: 'Orders processed', value: summary.total_transactions },
    { label: 'Matched', value: summary.matched, tone: 'text-teal' },
    { label: 'Exceptions', value: summary.exceptions, tone: 'text-amber' },
    { label: 'Match rate', value: `${summary.match_rate}%`, tone: 'text-ink' },
  ];

  return (
    <div className="border border-line rounded-sm bg-white flex flex-col sm:flex-row divide-y sm:divide-y-0 sm:divide-x divide-line">
      {stats.map((s) => (
        <div key={s.label} className="flex-1 px-6 py-5">
          <p className="text-xs text-steel mb-1">{s.label}</p>
          <p className={`font-serif text-3xl tabular-nums ${s.tone || 'text-ink'}`}>{s.value}</p>
        </div>
      ))}
      {summary.last_run && (
        <div className="px-6 py-5 flex items-center text-xs text-steel sm:ml-auto">
          Last run {summary.last_run}
        </div>
      )}
    </div>
  );
}
