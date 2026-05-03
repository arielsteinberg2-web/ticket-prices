import type { Event, PriceSnapshot, Prediction } from '../types';
import { extractTeams, FlagImg } from '../utils/teams';

interface Props {
  event: Event;
  snapshots: PriceSnapshot[];
  prediction: Prediction | null;
}

function ConfidenceDots({ confidence }: { confidence?: 'low' | 'medium' | 'high' }) {
  const filled = confidence === 'high' ? 3 : confidence === 'medium' ? 2 : 1;
  const color = confidence === 'high' ? '#34d399' : confidence === 'medium' ? '#f59e0b' : '#f87171';
  return (
    <div style={{ display: 'flex', justifyContent: 'center', gap: 3, marginTop: 5 }} title={`Confidence: ${confidence ?? 'low'}`}>
      {[1, 2, 3].map(i => (
        <div key={i} style={{
          width: 6, height: 6, borderRadius: '50%',
          background: i <= filled ? color : '#ffffff15',
        }} />
      ))}
    </div>
  );
}

const COLORS = {
  'BUY NOW':  { bg: '#1a3a2a', border: '#34d399', text: '#34d399' },
  'BUY SOON': { bg: '#3a2a1a', border: '#f59e0b', text: '#f59e0b' },
  'WAIT':     { bg: '#1a1a3a', border: '#a78bfa', text: '#a78bfa' },
};

const TREND_LABEL = {
  rising:  '▲ Rising',
  falling: '▼ Falling',
  flat:    '→ Stable',
};

export function BuyRecommendation({ event, snapshots, prediction }: Props) {
  const prices = snapshots.map(s => s.lowest_price);
  const latest = prices.at(-1) ?? null;
  const allTimeLow = prices.length ? Math.min(...prices) : null;
  const uniqueDays = new Set(snapshots.map(s => s.fetched_at.slice(0, 10))).size;

  const rec = prediction?.recommendation;
  const colors = rec ? COLORS[rec] : null;

  const teams = event.category === 'world_cup' ? extractTeams(event.name) : [];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
        <div style={{ flex: 1, paddingRight: 12 }}>
          {teams.length > 0 ? (
            <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 8, marginBottom: 4 }}>
              {teams.map((t, i) => (
                <span key={t.iso} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  {i > 0 && <span style={{ opacity: 0.35, fontSize: 12 }}>vs</span>}
                  <FlagImg iso={t.iso} size={28} />
                  <span style={{ fontSize: 14, fontWeight: 700 }}>{t.display}</span>
                </span>
              ))}
            </div>
          ) : (
            <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 4 }}>{event.name}</div>
          )}
          <div style={{ fontSize: 12, opacity: 0.5 }}>
            {event.event_date ? new Date(event.event_date).toLocaleDateString('en-US', { dateStyle: 'long' }) : 'Date TBD'}
            {event.venue ? ` · ${event.venue}` : ''}
            {event.city ? `, ${event.city}` : ''}
          </div>
        </div>

        {prediction?.has_data && colors && rec ? (
          <div style={{
            background: colors.bg, border: `1px solid ${colors.border}`,
            borderRadius: 8, padding: '8px 14px', textAlign: 'center', minWidth: 110, flexShrink: 0,
          }}>
            <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: 1, color: colors.text }}>
              Recommendation
            </div>
            <div style={{ fontSize: 20, fontWeight: 800, color: colors.text, marginTop: 2 }}>{rec}</div>
            {prediction.trend && (
              <div style={{ fontSize: 10, opacity: 0.6, marginTop: 2 }}>
                {TREND_LABEL[prediction.trend]}
              </div>
            )}
            <ConfidenceDots confidence={prediction.confidence} />
          </div>
        ) : (
          <div style={{
            background: '#1a1a2e', border: '1px solid #333',
            borderRadius: 8, padding: '8px 14px', textAlign: 'center', minWidth: 110, flexShrink: 0,
          }}>
            <div style={{ fontSize: 11, opacity: 0.4 }}>
              {prediction == null ? 'Loading...' : 'Not enough data yet\n(7 days needed)'}
            </div>
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {[
          { label: 'Current Low', value: latest != null ? `$${latest.toFixed(0)}` : '—', color: '#34d399' },
          { label: 'All-Time Low', value: allTimeLow != null ? `$${allTimeLow.toFixed(0)}` : '—' },
          {
            label: 'Predicted 7d',
            value: prediction?.has_data && prediction.predicted_price_7d != null
              ? `~$${prediction.predicted_price_7d.toFixed(0)}` : '—',
            color: '#f59e0b',
          },
          { label: 'Days Tracked', value: String(uniqueDays) },
        ].map(stat => (
          <div key={stat.label} style={{
            flex: '1 1 120px', background: '#0e0e1a', borderRadius: 8,
            padding: 10, textAlign: 'center', minWidth: 0,
          }}>
            <div style={{ fontSize: 10, opacity: 0.4, textTransform: 'uppercase', letterSpacing: 0.5 }}>
              {stat.label}
            </div>
            <div style={{ fontSize: 18, fontWeight: 700, marginTop: 2, color: stat.color ?? '#fff' }}>
              {stat.value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
