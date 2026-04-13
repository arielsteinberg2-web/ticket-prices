import { useMemo, useState } from 'react';
import type { Event } from '../types';

interface Props {
  events: Event[];
  selectedId: number | null;
  onSelect: (event: Event) => void;
  onDelete: (eventId: number) => void;
}

type SortKey = 'name' | 'latest_price' | 'weekly_change_pct' | 'event_date';

export function EventList({ events, selectedId, onSelect, onDelete }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>('event_date');
  const [sortAsc, setSortAsc] = useState(true);

  const sorted = useMemo(() => {
    return [...events].sort((a, b) => {
      const av = a[sortKey] ?? (sortAsc ? Infinity : -Infinity);
      const bv = b[sortKey] ?? (sortAsc ? Infinity : -Infinity);
      if (av < bv) return sortAsc ? -1 : 1;
      if (av > bv) return sortAsc ? 1 : -1;
      return 0;
    });
  }, [events, sortKey, sortAsc]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc(a => !a);
    else { setSortKey(key); setSortAsc(true); }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
      <div style={{ display: 'flex', gap: 4, padding: '6px 12px', borderBottom: '1px solid #222', fontSize: 11, opacity: 0.5 }}>
        {(['event_date', 'latest_price', 'weekly_change_pct'] as SortKey[]).map(k => (
          <button key={k} onClick={() => handleSort(k)} style={{
            background: 'none', border: 'none', color: sortKey === k ? '#a78bfa' : '#fff',
            cursor: 'pointer', fontSize: 11, padding: '2px 4px',
          }}>
            {k === 'event_date' ? 'Date' : k === 'latest_price' ? 'Price' : 'Change'}
            {sortKey === k ? (sortAsc ? ' ↑' : ' ↓') : ''}
          </button>
        ))}
        <span style={{ marginLeft: 'auto' }}>{sorted.length}</span>
      </div>
      <div style={{ overflowY: 'auto', flex: 1 }}>
        {sorted.map(event => {
          const isSelected = event.id === selectedId;
          const change = event.weekly_change_pct;
          const changeColor = change == null ? '#fff' : change > 0 ? '#f59e0b' : '#34d399';
          const changeBg = change == null ? 'transparent' : change > 0 ? '#3a2a1a' : '#1a3a2a';
          return (
            <div
              key={event.id}
              onClick={() => onSelect(event)}
              style={{
                padding: '10px 14px',
                borderBottom: '1px solid #222',
                borderLeft: isSelected ? '3px solid #a78bfa' : '3px solid transparent',
                background: isSelected ? '#2a2a3e' : 'transparent',
                cursor: 'pointer',
                position: 'relative',
              }}
            >
              <button
                onClick={e => { e.stopPropagation(); onDelete(event.id); }}
                style={{
                  position: 'absolute', top: 8, right: 8,
                  background: 'none', border: 'none', color: '#ffffff30',
                  cursor: 'pointer', fontSize: 13, padding: '0 2px',
                  lineHeight: 1,
                }}
                title="Remove"
              >✕</button>
              <div style={{ fontWeight: 600, fontSize: 13, paddingRight: 16 }}>{event.name}</div>
              {event.city && (
                <div style={{ fontSize: 11, opacity: 0.5, marginTop: 2 }}>
                  {event.event_date ? new Date(event.event_date).toLocaleDateString() : '—'} · {event.city}
                </div>
              )}
              <div style={{ marginTop: 5, display: 'flex', alignItems: 'center', gap: 6 }}>
                {event.latest_price != null ? (
                  <span style={{ fontWeight: 700, color: changeColor }}>
                    ${event.latest_price.toFixed(0)}
                    {event.price_source === 'seatgeek' && (
                      <span style={{ fontSize: 9, opacity: 0.5, marginLeft: 2 }}>SG</span>
                    )}
                  </span>
                ) : (
                  <span style={{ opacity: 0.3, fontSize: 12 }}>No price</span>
                )}
                {change != null && (
                  <span style={{
                    fontSize: 10, background: changeBg, color: changeColor,
                    padding: '1px 6px', borderRadius: 4,
                  }}>
                    {change > 0 ? '▲' : '▼'} {Math.abs(change)}%
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
