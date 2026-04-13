import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { PriceSnapshot } from '../types';

interface Props {
  snapshots: PriceSnapshot[];
  slope?: number;
}

function formatTick(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
    hour12: false,
  });
}

export function PriceChart({ snapshots, slope }: Props) {
  if (snapshots.length === 0) {
    return (
      <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: 0.4 }}>
        No price data yet
      </div>
    );
  }

  const chartData = snapshots.map((s, i) => ({
    label: formatTick(s.fetched_at),
    price: s.lowest_price,
    trend: slope != null ? +(snapshots[0].lowest_price + slope * i).toFixed(2) : undefined,
  }));

  const prices = snapshots.map(s => s.lowest_price);
  const minY = Math.floor(Math.min(...prices) * 0.9);
  const maxY = Math.ceil(Math.max(...prices) * 1.1);

  // Show at most ~6 ticks to avoid crowding
  const tickInterval = Math.max(1, Math.floor(chartData.length / 6));

  return (
    <div style={{ background: '#0e0e1a', borderRadius: 8, padding: '12px 0 4px', marginBottom: 14 }}>
      <div style={{ fontSize: 11, opacity: 0.4, paddingLeft: 16, marginBottom: 6 }}>Lowest price over time ($)</div>
      <ResponsiveContainer width="100%" height={160}>
        <LineChart data={chartData} margin={{ top: 4, right: 20, bottom: 20, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 9, fill: '#ffffff60' }}
            tickLine={false}
            interval={tickInterval}
            angle={-35}
            textAnchor="end"
            height={40}
          />
          <YAxis domain={[minY, maxY]} tick={{ fontSize: 10, fill: '#ffffff60' }} tickLine={false} width={50} />
          <Tooltip
            contentStyle={{ background: '#1e1e2e', border: '1px solid #333', borderRadius: 6, fontSize: 12 }}
            formatter={(value: number) => [`$${value.toFixed(2)}`, '']}
            labelFormatter={(label) => label}
          />
          <Line
            type="monotone" dataKey="price" stroke="#34d399"
            strokeWidth={2.5} dot={{ r: 3, fill: '#34d399' }} activeDot={{ r: 5 }}
            name="Actual price"
          />
          {slope != null && (
            <Line
              type="linear" dataKey="trend" stroke="#a78bfa"
              strokeWidth={1.5} strokeDasharray="6 4" dot={false}
              name="Trend"
            />
          )}
        </LineChart>
      </ResponsiveContainer>
      <div style={{ display: 'flex', gap: 16, fontSize: 11, padding: '4px 16px', opacity: 0.6 }}>
        <span><span style={{ color: '#34d399' }}>—</span> actual price</span>
        {slope != null && <span><span style={{ color: '#a78bfa' }}>- -</span> trend line</span>}
      </div>
    </div>
  );
}
