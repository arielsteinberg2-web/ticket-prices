import { useMemo, useState } from 'react';
import type { Event } from '../types';

interface Props {
  events: Event[];
  selectedId: number | null;
  onSelect: (event: Event) => void;
}

type SortKey = 'name' | 'latest_price' | 'weekly_change_pct' | 'event_date';

export function EventList({ events, selectedId, onSelect }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>('event_date');
  const [sortAsc, setSortAsc] = useState(true);
  const [search, setSearch] = useState('');

  const sorted = useMemo(() => {
    const filtered = events.filter(e =>
      e.name.toLowerCase().includes(search.toLowerCase()) ||
      (e.city ?? '').toLowerCase().includes(search.toLowerCase())
    );
    return [...filtered].sort((a, b) => {
      const av = a[sortKey] ?? (sortAsc ? Infinity : -Infinity);
      const bv = b[sortKey] ?? (sortAsc ? Infinity : -Infinity);
      if (av < bv) return sortAsc ? -1 : 1;
      if (av > bv) return sortAsc ? 1 : -1;
      return 0;
    });
  }, [events, sortKey, sortAsc, search]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc(a => !a);
    else { setSortKey(key); setSortAsc(true); }
  };

  return (
    <div style={{ width: 280, borderRight: '1px solid #333', display: 'flex', flexDirection: 'column', background: '#161622' }}>
      <div style={{ padding: '8px 12px', borderBottom: '1px solid #333' }}>
        <input
          placeholder="Search events..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{
            width: '100%', padding: '6px 10px', background: '#0e0e1a',
            border: '1px solid #333', borderRadius: 6, color: '#fff',
            fontSize: 13, boxSizing: 'border-box',
          }}
        />
      </div>
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
              }}
            >
              <div style={{ fontWeight: 600, fontSize: 13 }}>{event.name}</div>
              {event.city && (
                <div style={{ fontSize: 11, opacity: 0.5, marginTop: 2 }}>
                  {event.event_date ? new Date(event.event_date).toLocaleDateString() : '—'} · {event.city}
                </div>
              )}
              <div style={{ marginTop: 5, display: 'flex', alignItems: 'center', gap: 6 }}>
                {event.latest_price != null ? (
                  <span style={{ fontWeight: 700, color: changeColor }}>
                    ${event.latest_price.toFixed(0)}
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
