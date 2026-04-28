import { useState } from 'react';
import type { SearchResult, Event } from '../types';
import { trackEvent } from '../api';

interface Props {
  query: string;
  results: SearchResult[];
  trackedEvents: Event[];
  onTracked: () => void;
  onClose: () => void;
  isMobile: boolean;
}

function fmtDate(iso: string | null): { top: string; bot: string } {
  if (!iso) return { top: '—', bot: '' };
  const d = new Date(iso);
  const mon = d.toLocaleString('en-US', { month: 'short' });
  const day = d.getDate().toString().padStart(2, '0');
  const dow = d.toLocaleString('en-US', { weekday: 'short' });
  const time = d.toLocaleString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
  return { top: `${mon} ${day}`, bot: `${dow} ${time}` };
}

export function BrowsePanel({ query, results, trackedEvents, onTracked, onClose, isMobile }: Props) {
  const [tracked, setTracked] = useState<Set<string>>(new Set());
  const [tracking, setTracking] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  const trackedIds = new Set(trackedEvents.map(e => e.name + '|' + e.event_date));

  const handleTrack = async (r: SearchResult) => {
    setTracking(prev => new Set([...prev, r.ticketmaster_id]));
    setError(null);
    try {
      await trackEvent({ ...r, category: 'events' });
      setTracked(prev => new Set([...prev, r.ticketmaster_id]));
      onTracked();
    } catch {
      setError('Failed to track. Try again.');
    } finally {
      setTracking(prev => { const s = new Set(prev); s.delete(r.ticketmaster_id); return s; });
    }
  };

  const isTracked = (r: SearchResult) =>
    r.already_tracked ||
    tracked.has(r.ticketmaster_id) ||
    trackedIds.has(r.name + '|' + r.event_date);

  return (
    <div style={{
      width: isMobile ? '100%' : 300,
      flexShrink: 0,
      borderRight: isMobile ? 'none' : '1px solid #1a1a1a',
      borderBottom: isMobile ? '1px solid #1a1a1a' : 'none',
      background: '#0d0d1a',
      display: 'flex',
      flexDirection: 'column',
      overflowY: 'auto',
      maxHeight: isMobile ? 340 : undefined,
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '10px 14px', borderBottom: '1px solid #1a1a1a',
        background: '#111118', flexShrink: 0,
      }}>
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#a78bfa' }}>
            {results.length} result{results.length !== 1 ? 's' : ''}
          </div>
          <div style={{ fontSize: 11, opacity: 0.4, marginTop: 1, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {query}
          </div>
        </div>
        <button
          onClick={onClose}
          style={{
            background: '#ffffff10', border: 'none', color: '#fff',
            borderRadius: '50%', width: 24, height: 24, cursor: 'pointer',
            fontSize: 12, display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
        >
          ✕
        </button>
      </div>

      {error && (
        <div style={{ fontSize: 11, color: '#f87171', padding: '6px 14px' }}>{error}</div>
      )}

      {/* Result rows */}
      <div style={{ overflowY: 'auto', flex: 1 }}>
        {results.map(r => {
          const { top, bot } = fmtDate(r.event_date);
          const done = isTracked(r);
          const busy = tracking.has(r.ticketmaster_id);
          return (
            <div
              key={r.ticketmaster_id}
              style={{
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '10px 12px', borderBottom: '1px solid #111',
                background: done ? '#0f1f18' : 'transparent',
              }}
            >
              {/* Date column */}
              <div style={{ width: 48, flexShrink: 0, textAlign: 'center' }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#fff' }}>{top}</div>
                <div style={{ fontSize: 10, color: '#ffffff50', marginTop: 1 }}>{bot}</div>
              </div>

              {/* Info column */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  fontSize: 11, fontWeight: 600, color: '#fff',
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>
                  {r.name}
                </div>
                <div style={{
                  fontSize: 10, color: '#ffffff45', marginTop: 2,
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>
                  {[r.venue, r.city].filter(Boolean).join(' · ')}
                </div>
                {r.lowest_price != null && (
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#34d399', marginTop: 3 }}>
                    From ${r.lowest_price.toFixed(0)}+
                  </div>
                )}
              </div>

              {/* Track button */}
              <button
                onClick={() => !done && !busy && handleTrack(r)}
                disabled={done || busy}
                style={{
                  flexShrink: 0,
                  padding: '4px 9px', borderRadius: 5, fontSize: 10,
                  background: done ? '#1a3a2a' : '#a78bfa20',
                  border: `1px solid ${done ? '#34d39970' : '#a78bfa50'}`,
                  color: done ? '#34d399' : '#a78bfa',
                  cursor: (done || busy) ? 'default' : 'pointer',
                  opacity: busy ? 0.5 : 1,
                  whiteSpace: 'nowrap',
                }}
              >
                {busy ? '…' : done ? '✓' : '+ Track'}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
