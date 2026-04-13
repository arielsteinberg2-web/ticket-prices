import { useState, useEffect, useRef } from 'react';
import type { Event, SearchResult } from '../types';
import { searchEvents, trackEvent } from '../api';

interface Props {
  category: string;
  onTracked: () => void;
  events?: Event[];
  onSelect?: (event: Event) => void;
}

export function EventSearch({ category, onTracked, events = [], onSelect }: Props) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [tracked, setTracked] = useState<Set<string>>(new Set());
  const [tracking, setTracking] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const localMatches = query.trim().length >= 2
    ? events.filter(e => e.name.toLowerCase().includes(query.trim().toLowerCase()))
    : [];

  const handleSearch = async (q = query) => {
    if (!q.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await searchEvents(q.trim(), category);
      setResults(data);
      if (data.length === 0) setError('No events found. Try a different search.');
    } catch {
      setError('Search failed. Check your connection.');
    } finally {
      setLoading(false);
    }
  };

  // Auto-search after user stops typing for 500ms
  useEffect(() => {
    if (query.trim().length < 2) { setResults([]); setError(null); return; }
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => handleSearch(query), 500);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [query]);

  const handleTrack = async (result: SearchResult) => {
    setTracking(prev => new Set([...prev, result.ticketmaster_id]));
    try {
      await trackEvent({ ...result, category });
      setTracked(prev => new Set([...prev, result.ticketmaster_id]));
      onTracked();
    } catch {
      setError('Failed to track event. Try again.');
    } finally {
      setTracking(prev => { const s = new Set(prev); s.delete(result.ticketmaster_id); return s; });
    }
  };

  const handleSelectLocal = (event: Event) => {
    onSelect?.(event);
    setQuery('');
    setResults([]);
  };

  const showLocalSuggestions = localMatches.length > 0 && results.length === 0;

  return (
    <div style={{ padding: '10px 12px', borderBottom: '1px solid #222', background: '#111118', position: 'relative', zIndex: 100 }}>
      <div style={{ display: 'flex', gap: 6, marginBottom: showLocalSuggestions || results.length > 0 || error ? 8 : 0 }}>
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') { if (debounceRef.current) clearTimeout(debounceRef.current); handleSearch(); } }}
          placeholder={`Search ${category === 'world_cup' ? 'World Cup' : ''} events...`}
          style={{
            flex: 1, padding: '7px 10px', background: '#1a1a2e',
            border: '1px solid #333', borderRadius: 6, color: '#fff',
            fontSize: 12, outline: 'none',
          }}
        />
        <button
          onClick={() => { if (debounceRef.current) clearTimeout(debounceRef.current); handleSearch(); }}
          disabled={loading}
          style={{
            padding: '7px 12px', background: '#a78bfa15', border: '1px solid #a78bfa40',
            color: '#a78bfa', borderRadius: 6, cursor: loading ? 'not-allowed' : 'pointer',
            fontSize: 12, opacity: loading ? 0.6 : 1, whiteSpace: 'nowrap',
          }}
        >
          {loading ? '…' : '🔍'}
        </button>
      </div>

      {error && <div style={{ fontSize: 12, color: '#f87171', marginBottom: 8 }}>{error}</div>}

      {/* Local suggestions while typing */}
      {showLocalSuggestions && (
        <div style={{ maxHeight: 200, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 4 }}>
          {localMatches.map(e => (
            <div
              key={e.id}
              onClick={() => handleSelectLocal(e)}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                background: '#1a1a2e', borderRadius: 6, padding: '7px 10px',
                border: '1px solid #a78bfa30', cursor: 'pointer',
              }}
            >
              <div>
                <div style={{ fontSize: 12, fontWeight: 600 }}>{e.name}</div>
                <div style={{ fontSize: 11, opacity: 0.45, marginTop: 1 }}>
                  {e.event_date ? new Date(e.event_date).toLocaleDateString() : '—'}
                  {e.city ? ` · ${e.city}` : ''}
                </div>
              </div>
              {e.latest_price != null && (
                <span style={{ fontSize: 12, fontWeight: 700, color: '#34d399' }}>${e.latest_price.toFixed(0)}</span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Ticketmaster search results */}
      {results.length > 0 && (
        <div style={{ maxHeight: 240, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6 }}>
          {results.map(r => {
            const isTracked = r.already_tracked || tracked.has(r.ticketmaster_id);
            const localEvent = isTracked ? events.find(e => e.name === r.name) : undefined;
            return (
              <div
                key={r.ticketmaster_id}
                onClick={() => localEvent && handleSelectLocal(localEvent)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  background: '#1a1a2e', borderRadius: 6, padding: '8px 10px',
                  border: '1px solid #333', cursor: localEvent ? 'pointer' : 'default',
                }}
              >
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
                  onClick={ev => { ev.stopPropagation(); !isTracked && !tracking.has(r.ticketmaster_id) && handleTrack(r); }}
                  disabled={isTracked || tracking.has(r.ticketmaster_id)}
                  style={{
                    padding: '4px 10px', borderRadius: 5, fontSize: 11, whiteSpace: 'nowrap',
                    background: isTracked ? '#1a3a2a' : '#a78bfa20',
                    border: `1px solid ${isTracked ? '#34d399' : '#a78bfa50'}`,
                    color: isTracked ? '#34d399' : '#a78bfa',
                    cursor: (isTracked || tracking.has(r.ticketmaster_id)) ? 'default' : 'pointer',
                    opacity: tracking.has(r.ticketmaster_id) ? 0.5 : 1,
                  }}
                >
                  {tracking.has(r.ticketmaster_id) ? '…' : isTracked ? '✓ Tracked' : '+ Track'}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
