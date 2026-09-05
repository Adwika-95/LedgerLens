import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

const STATUS_LABELS = {
  MISSING_FROM_GATEWAY: 'Missing from gateway',
  MISSING_FROM_BANK: 'Missing from bank',
  AMOUNT_MISMATCH: 'Amount mismatch',
  DUPLICATE_UTR: 'Duplicate UTR',
  STATUS_MISMATCH: 'Status mismatch',
};

export default function ExceptionBreakdownChart({ breakdown }) {
  const data = (breakdown || [])
    .map((b) => ({
      name: STATUS_LABELS[b.reconciliation_status] || b.reconciliation_status,
      count: b.count,
    }))
    .sort((a, b) => b.count - a.count);

  if (data.length === 0) {
    return <p className="text-sm text-steel">No exceptions to chart yet.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={Math.max(140, data.length * 44)}>
      <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16, top: 4, bottom: 4 }}>
        <CartesianGrid horizontal={false} stroke="#E7E3DC" />
        <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11, fill: '#6B7280' }} axisLine={{ stroke: '#E7E3DC' }} />
        <YAxis
          type="category"
          dataKey="name"
          width={140}
          tick={{ fontSize: 12, fill: '#1C1917' }}
          axisLine={{ stroke: '#E7E3DC' }}
          tickLine={false}
        />
        <Tooltip
          cursor={{ fill: '#FEF3E2' }}
          contentStyle={{ border: '1px solid #E7E3DC', borderRadius: 2, fontSize: 12 }}
        />
        <Bar dataKey="count" fill="#B45309" radius={[0, 2, 2, 0]} barSize={18} />
      </BarChart>
    </ResponsiveContainer>
  );
}
