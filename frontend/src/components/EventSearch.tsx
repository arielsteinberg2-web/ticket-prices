import { useState } from 'react';
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
  const [tickpickUrls, setTickpickUrls] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  const localMatches = query.trim().length >= 2
    ? events.filter(e => e.name.toLowerCase().includes(query.trim().toLowerCase()))
    : [];

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
    const tickpick_url = tickpickUrls[result.ticketmaster_id] || undefined;
    await trackEvent({ ...result, category, tickpick_url });
    setTracked(prev => new Set([...prev, result.ticketmaster_id]));
    onTracked();
  };

  const handleSelectLocal = (event: Event) => {
    onSelect?.(event);
    setQuery('');
    setResults([]);
  };

  const showLocalSuggestions = localMatches.length > 0 && results.length === 0;

  return (
    <div style={{ padding: '10px 12px', borderBottom: '1px solid #222', background: '#111118' }}>
      <div style={{ display: 'flex', gap: 6, marginBottom: showLocalSuggestions || results.length > 0 || error ? 8 : 0 }}>
        <input
          value={query}
          onChange={e => { setQuery(e.target.value); setResults([]); setError(null); }}
          onKeyDown={e => e.key === 'Enter' && handleSearch()}
          placeholder={`Search ${category === 'world_cup' ? 'World Cup' : ''} events...`}
          style={{
            flex: 1, padding: '7px 10px', background: '#1a1a2e',
            border: '1px solid #333', borderRadius: 6, color: '#fff',
            fontSize: 12, outline: 'none',
          }}
        />
        <button
          onClick={handleSearch}
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
                  {!isTracked && (
                    <input
                      value={tickpickUrls[r.ticketmaster_id] || ''}
                      onChange={e => setTickpickUrls(prev => ({ ...prev, [r.ticketmaster_id]: e.target.value }))}
                      placeholder="TickPick URL (optional)"
                      onClick={ev => ev.stopPropagation()}
                      style={{
                        marginTop: 4, width: '100%', padding: '3px 7px', background: '#0e0e1a',
                        border: '1px solid #333', borderRadius: 4, color: '#fff',
                        fontSize: 10, boxSizing: 'border-box', outline: 'none',
                      }}
                    />
                  )}
                </div>
                {r.lowest_price != null && (
                  <span style={{ fontSize: 12, fontWeight: 700, color: '#34d399', whiteSpace: 'nowrap' }}>
                    ${r.lowest_price.toFixed(0)}
                  </span>
                )}
                <button
                  onClick={ev => { ev.stopPropagation(); !isTracked && handleTrack(r); }}
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
