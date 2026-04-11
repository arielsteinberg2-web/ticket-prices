import { useState } from 'react';
import type { SearchResult } from '../types';
import { searchEvents, trackEvent } from '../api';

interface Props {
  category: string;
  onTracked: () => void;
}

export function EventSearch({ category, onTracked }: Props) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [tracked, setTracked] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await searchEvents(query.trim(), category);
      setResults(data);
      if (data.length === 0) setError('No events found. Try a different search.');
    } catch {
      setError('Search failed. Check your connection.');
    } finally {
      setLoading(false);
    }
  };

  const handleTrack = async (result: SearchResult) => {
    await trackEvent({ ...result, category });
    setTracked(prev => new Set([...prev, result.ticketmaster_id]));
    onTracked();
  };

  return (
    <div style={{ padding: '12px 14px', borderBottom: '1px solid #333', background: '#0e0e1a' }}>
      <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSearch()}
          placeholder={`Search ${category === 'world_cup' ? 'World Cup' : 'sports'} events...`}
          style={{
            flex: 1, padding: '7px 11px', background: '#1a1a2e',
            border: '1px solid #a78bfa50', borderRadius: 6, color: '#fff',
            fontSize: 13, outline: 'none',
          }}
        />
        <button
          onClick={handleSearch}
          disabled={loading}
          style={{
            padding: '7px 14px', background: '#a78bfa20', border: '1px solid #a78bfa50',
            color: '#a78bfa', borderRadius: 6, cursor: loading ? 'not-allowed' : 'pointer',
            fontSize: 12, opacity: loading ? 0.6 : 1, whiteSpace: 'nowrap',
          }}
        >
          {loading ? '...' : '🔍 Search'}
        </button>
      </div>

      {error && <div style={{ fontSize: 12, color: '#f87171', marginBottom: 8 }}>{error}</div>}

      {results.length > 0 && (
        <div style={{ maxHeight: 240, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6 }}>
          {results.map(r => {
            const isTracked = r.already_tracked || tracked.has(r.ticketmaster_id);
            return (
              <div key={r.ticketmaster_id} style={{
                display: 'flex', alignItems: 'center', gap: 10,
                background: '#1a1a2e', borderRadius: 6, padding: '8px 10px',
                border: '1px solid #333',
              }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {r.name}
                  </div>
                  <div style={{ fontSize: 11, opacity: 0.45, marginTop: 2 }}>
                    {r.event_date ? new Date(r.event_date).toLocaleDateString() : '—'}
                    {r.city ? ` · ${r.city}` : ''}
                  </div>
                </div>
                {r.lowest_price != null && (
                  <span style={{ fontSize: 12, fontWeight: 700, color: '#34d399', whiteSpace: 'nowrap' }}>
                    ${r.lowest_price.toFixed(0)}
                  </span>
                )}
                <button
                  onClick={() => !isTracked && handleTrack(r)}
                  disabled={isTracked}
                  style={{
                    padding: '4px 10px', borderRadius: 5, fontSize: 11, whiteSpace: 'nowrap',
                    background: isTracked ? '#1a3a2a' : '#a78bfa20',
                    border: `1px solid ${isTracked ? '#34d399' : '#a78bfa50'}`,
                    color: isTracked ? '#34d399' : '#a78bfa',
                    cursor: isTracked ? 'default' : 'pointer',
                  }}
                >
                  {isTracked ? '✓ Tracked' : '+ Track'}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
