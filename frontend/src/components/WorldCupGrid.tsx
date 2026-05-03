import { useState } from 'react';
import type { Event } from '../types';
import type { AlertMap } from '../api';
import { setAlert, deleteAlert, getSavedEmail, saveEmail } from '../api';
import { extractTeams, FlagImg } from '../utils/teams';

const CITY_DISPLAY: Record<string, string> = {
  'east rutherford': 'New York',
  'foxborough': 'Boston',
  'inglewood': 'Los Angeles',
  'santa clara': 'San Francisco',
  'arlington': 'Dallas',
  'miami gardens': 'Miami',
  'zapopan': 'Guadalajara',
};

function displayCity(city: string | null): string | null {
  if (!city) return null;
  return CITY_DISPLAY[city.toLowerCase()] ?? city;
}

function Sparkline({ prices }: { prices: number[] }) {
  if (prices.length < 2) return null;
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;
  const w = 80, h = 24;
  const points = prices.map((p, i) => {
    const x = (i / (prices.length - 1)) * w;
    const y = h - ((p - min) / range) * (h - 4) - 2;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  const isUp = prices[prices.length - 1] > prices[0];
  const color = isUp ? '#f59e0b' : '#34d399';
  return (
    <svg width={w} height={h} style={{ display: 'block', overflow: 'visible' }}>
      <polyline points={points} fill="none" stroke={color} strokeWidth={1.5} strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}

interface AlertModalProps {
  event: Event;
  existing: { threshold_price: number; email: string } | null;
  onSave: (email: string, threshold: number) => void;
  onDelete: () => void;
  onClose: () => void;
}

function AlertModal({ event, existing, onSave, onDelete, onClose }: AlertModalProps) {
  const [email, setEmailVal] = useState(existing?.email || getSavedEmail());
  const defaultThreshold = existing?.threshold_price ?? Math.round((event.latest_price ?? 200) * 0.9);
  const [threshold, setThreshold] = useState(String(defaultThreshold));
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    const t = parseFloat(threshold);
    if (!email || isNaN(t) || t <= 0) return;
    setSaving(true);
    saveEmail(email);
    await onSave(email, t);
    setSaving(false);
    onClose();
  };

  return (
    <div
      onClick={e => e.stopPropagation()}
      style={{
        position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
        background: '#13132a', borderRadius: 10, zIndex: 10,
        padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 10,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: '#a78bfa' }}>Price alert</span>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#ffffff50', cursor: 'pointer', fontSize: 14 }}>✕</button>
      </div>

      <div style={{ fontSize: 11, opacity: 0.5, lineHeight: 1.4 }}>
        Email me when price drops below:
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <span style={{ color: '#34d399', fontWeight: 700, fontSize: 16 }}>$</span>
        <input
          type="number"
          value={threshold}
          onChange={e => setThreshold(e.target.value)}
          style={{
            background: '#1e1e3a', border: '1px solid #333', color: '#fff',
            borderRadius: 6, padding: '5px 10px', fontSize: 14, width: 80,
          }}
        />
      </div>

      <input
        type="email"
        placeholder="your@email.com"
        value={email}
        onChange={e => setEmailVal(e.target.value)}
        style={{
          background: '#1e1e3a', border: '1px solid #333', color: '#fff',
          borderRadius: 6, padding: '6px 10px', fontSize: 12,
        }}
      />

      <div style={{ display: 'flex', gap: 6, marginTop: 2 }}>
        <button
          onClick={handleSave}
          disabled={saving}
          style={{
            flex: 1, background: '#a78bfa20', border: '1px solid #a78bfa60',
            color: '#a78bfa', borderRadius: 6, padding: '6px 0', fontSize: 12,
            cursor: saving ? 'not-allowed' : 'pointer', fontWeight: 600,
          }}
        >
          {saving ? '...' : existing ? 'Update' : 'Set alert'}
        </button>
        {existing && (
          <button
            onClick={async () => { await onDelete(); onClose(); }}
            style={{
              background: '#3a1a1a', border: '1px solid #f8717140',
              color: '#f87171', borderRadius: 6, padding: '6px 10px', fontSize: 12,
              cursor: 'pointer',
            }}
          >
            Remove
          </button>
        )}
      </div>
    </div>
  );
}

interface Props {
  events: Event[];
  selectedId: number | null;
  onSelect: (event: Event) => void;
  onDelete: (eventId: number) => void;
  alerts: AlertMap;
  onAlertsChange: (alerts: AlertMap) => void;
  showTeams?: boolean;
  quantity?: number;
  isMobile?: boolean;
}

export function WorldCupGrid({ events, selectedId, onSelect, onDelete, alerts, onAlertsChange, showTeams = true, quantity = 1, isMobile = false }: Props) {
  const [alertModal, setAlertModal] = useState<number | null>(null);

  const sorted = [...events].sort((a, b) => {
    if (!a.event_date) return 1;
    if (!b.event_date) return -1;
    return a.event_date < b.event_date ? -1 : 1;
  });

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: `repeat(auto-fill, minmax(${isMobile ? '160px' : '260px'}, 1fr))`,
      gap: isMobile ? 8 : 12,
      padding: isMobile ? '10px 12px' : '16px 20px',
      alignContent: 'start',
    }}>
      {sorted.map(event => {
        const isSelected = event.id === selectedId;
        const teams = showTeams ? extractTeams(event.name) : [];
        const displayPrice = (event.prices_by_qty?.[quantity] ?? event.latest_price);
        const change = event.weekly_change_pct;
        const changeColor = change == null ? '#fff' : change > 0 ? '#f59e0b' : '#34d399';
        const changeBg   = change == null ? 'transparent' : change > 0 ? '#3a2a1a' : '#1a3a2a';
        const hasAlert = Boolean(alerts[event.id]);
        const showModal = alertModal === event.id;

        return (
          <div
            key={event.id}
            onClick={() => { if (!showModal) onSelect(event); }}
            style={{
              background: isSelected ? '#2a2a3e' : '#1a1a2e',
              border: isSelected ? '1px solid #a78bfa' : 'none',
              borderRadius: 10, padding: isMobile ? '10px 12px' : '14px 16px',
              cursor: 'pointer', position: 'relative', transition: 'background 0.15s',
            }}
          >
            {/* Alert modal overlay */}
            {showModal && (
              <AlertModal
                event={event}
                existing={alerts[event.id] ?? null}
                onSave={async (email, threshold) => {
                  await setAlert(event.id, email, threshold);
                  onAlertsChange({ ...alerts, [event.id]: { email, threshold_price: threshold } });
                }}
                onDelete={async () => {
                  await deleteAlert(event.id);
                  const next = { ...alerts };
                  delete next[event.id];
                  onAlertsChange(next);
                }}
                onClose={() => setAlertModal(null)}
              />
            )}

            {/* Bell button */}
            <button
              onClick={e => { e.stopPropagation(); setAlertModal(showModal ? null : event.id); }}
              title={hasAlert ? 'Edit alert' : 'Set price alert'}
              style={{
                position: 'absolute', top: 8, right: 28,
                background: 'none', border: 'none',
                color: hasAlert ? '#a78bfa' : '#ffffff25',
                cursor: 'pointer', fontSize: 13, lineHeight: 1, padding: '2px 4px',
                borderRadius: 3,
              }}
            >
              {hasAlert ? '🔔' : '🔕'}
            </button>

            {/* Delete button */}
            <button
              onClick={e => { e.stopPropagation(); onDelete(event.id); }}
              style={{
                position: 'absolute', top: 8, right: 10,
                background: 'none', border: 'none', color: '#ffffff30',
                cursor: 'pointer', fontSize: 11, lineHeight: 1, padding: '2px 4px',
                borderRadius: 3,
              }}
              title="Untrack"
            >✕</button>

            {teams.length > 0 ? (
              <div style={{ marginBottom: 6, display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 6 }}>
                {teams.map((t, i) => (
                  <span key={t.iso} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                    {i > 0 && <span style={{ opacity: 0.35, fontSize: 11, margin: '0 2px' }}>vs</span>}
                    <FlagImg iso={t.iso} />
                    <span style={{ fontSize: 12, fontWeight: 600 }}>{t.display}</span>
                  </span>
                ))}
              </div>
            ) : (
              <div style={{ fontWeight: 600, fontSize: 13, paddingRight: 40, lineHeight: 1.4, marginBottom: 4 }}>
                {event.name}
              </div>
            )}

            {event.event_date && (
              <div style={{ fontSize: 11, opacity: 0.45, marginTop: 2 }}>
                {new Date(event.event_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
                {event.city ? ` · ${displayCity(event.city)}` : ''}
              </div>
            )}
            {event.venue && (
              <div style={{ fontSize: 11, opacity: 0.3, marginTop: 1 }}>{event.venue}</div>
            )}

            <div style={{ marginTop: 10, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {displayPrice != null ? (
                  <span style={{ fontWeight: 700, fontSize: 16, color: changeColor }}>
                    ${displayPrice.toFixed(0)}
                    {event.price_source === 'seatgeek' && <span style={{ fontSize: 9, opacity: 0.5, marginLeft: 4 }}>via SeatGeek</span>}
                    {event.price_source === 'tickpick' && <span style={{ fontSize: 9, opacity: 0.5, marginLeft: 4 }}>via TickPick</span>}
                  </span>
                ) : (
                  <span style={{ opacity: 0.25, fontSize: 12 }}>No price yet</span>
                )}
                {change != null && (
                  <span style={{ fontSize: 10, background: changeBg, color: changeColor, padding: '2px 7px', borderRadius: 4 }}>
                    {change > 0 ? '▲' : '▼'} {Math.abs(change)}%
                  </span>
                )}
              </div>
              {event.price_history && event.price_history.length >= 2 && (
                <Sparkline prices={event.price_history.map(s => s.lowest_price)} />
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
