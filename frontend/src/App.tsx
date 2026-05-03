import { useEffect, useState, useCallback, useRef } from 'react';
import type { Category, Event, PriceSnapshot, Prediction } from './types';
import { fetchEvents, fetchHistory, fetchPrediction, triggerFetch, deleteEvent, fetchStatus, setQuantity, fetchAlerts } from './api';
import type { AlertMap } from './api';
import { WorldCupGrid } from './components/WorldCupGrid';
import { PriceChart } from './components/PriceChart';
import { BuyRecommendation } from './components/BuyRecommendation';
import { EventSearch } from './components/EventSearch';
import { LocationFilter } from './components/LocationFilter';
import { BrowsePanel } from './components/BrowsePanel';
import type { SearchResult } from './types';

const TABS: { key: Category; label: string; emoji: string }[] = [
  { key: 'world_cup', label: 'World Cup 2026', emoji: '⚽' },
  { key: 'events',    label: 'Events',          emoji: '🎭' },
];

const SELECT_STYLE: React.CSSProperties = {
  background: '#1a1a2e', border: '1px solid #333', color: '#a78bfa',
  borderRadius: 5, padding: '3px 8px', fontSize: 12, cursor: 'pointer',
  WebkitAppearance: 'none', appearance: 'none',
};

export default function App() {
  const [activeTab, setActiveTab] = useState<Category>('world_cup');
  const [events, setEvents] = useState<Event[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [snapshots, setSnapshots] = useState<PriceSnapshot[]>([]);
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [quantity, setQuantityState] = useState<Record<Category, number>>({ world_cup: 1, events: 1 });
  const [locationFilter, setLocationFilter] = useState<Record<Category, string>>({ world_cup: '', events: '' });
  const [lastFetch, setLastFetch] = useState<string | null>(null);
  const [tokenDays, setTokenDays] = useState<number | null>(null);
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  const [browseResults, setBrowseResults] = useState<SearchResult[]>([]);
  const [browseQuery, setBrowseQuery] = useState('');
  const [browseLoading, setBrowseLoading] = useState(false);
  const [alerts, setAlerts] = useState<AlertMap>({});
  const eventsCache = useRef<Partial<Record<Category, { data: Event[]; ts: number }>>>({});

  useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', handler);
    return () => window.removeEventListener('resize', handler);
  }, []);

  useEffect(() => {
    fetchStatus().then(s => setTokenDays(s?.tickpick_token?.days_remaining ?? null));
    fetchAlerts().then(setAlerts).catch(() => {});
  }, []);

  const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

  const loadEvents = useCallback(async (category: Category, silent = false) => {
    const cached = eventsCache.current[category];
    const fresh = cached && Date.now() - cached.ts < CACHE_TTL;

    // Return cached data immediately if fresh and not a forced refresh
    if (fresh && !silent) {
      setEvents(cached!.data);
      setSelectedEvent(null);
      return;
    }
    if (fresh && silent) {
      // Silent refresh: update in background without showing loader
    }

    if (!silent) setLoading(true);
    try {
      const data = await fetchEvents(category);
      eventsCache.current[category] = { data, ts: Date.now() };
      setEvents(data);
      if (!silent) setSelectedEvent(null);
      if (data.length > 0 && data[0].quantity) {
        setQuantityState(prev => ({ ...prev, [category]: data[0].quantity }));
      }
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    setSelectedEvent(null);
    setSnapshots([]);
    setPrediction(null);
    loadEvents(activeTab);
    setLocationFilter(prev => ({ ...prev, [activeTab]: '' }));
    setBrowseResults([]);
    setBrowseQuery('');
    setBrowseLoading(false);
  }, [activeTab, loadEvents]);

  useEffect(() => {
    if (!selectedEvent) return;
    // Show cached price history instantly — no waiting
    if (selectedEvent.price_history?.length) {
      setSnapshots(selectedEvent.price_history);
    } else {
      setSnapshots([]);
    }
    setPrediction(null);
    // Fetch full history (may have more than 20 points) + prediction in background
    Promise.all([
      fetchHistory(selectedEvent.id),
      fetchPrediction(selectedEvent.id),
    ]).then(([hist, pred]) => {
      setSnapshots(hist);
      setPrediction(pred);
    });
  }, [selectedEvent]);

  const handleQuantityChange = (q: number) => {
    setQuantityState(prev => ({ ...prev, [activeTab]: q }));
    setQuantity(activeTab, q).catch(() => {});
    if (selectedEvent) {
      Promise.all([
        fetchHistory(selectedEvent.id, q),
        fetchPrediction(selectedEvent.id, q),
      ]).then(([hist, pred]) => {
        setSnapshots(hist);
        setPrediction(pred);
      });
    }
  };

  const handleDelete = async (eventId: number) => {
    await deleteEvent(eventId);
    if (selectedEvent?.id === eventId) setSelectedEvent(null);
    await loadEvents(activeTab);
  };

  const handleFetch = async () => {
    setFetching(true);
    try {
      await triggerFetch();
      eventsCache.current = {}; // bust cache so next load is fresh
      setLastFetch(new Date().toLocaleString('en-US', { timeZone: 'America/New_York', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false }));
      await loadEvents(activeTab);
      if (selectedEvent) {
        const [hist, pred] = await Promise.all([
          fetchHistory(selectedEvent.id),
          fetchPrediction(selectedEvent.id),
        ]);
        setSnapshots(hist);
        setPrediction(pred);
      }
    } finally {
      setFetching(false);
    }
  };

  const loc = locationFilter[activeTab];
  const filteredEvents = events.filter(e => {
    if (loc && e.city !== loc) return false;
    if (activeTab === 'events') {
      const n = e.name.toLowerCase();
      if (n.includes('world cup') || n.includes('fifa')) return false;
    }
    return true;
  });

  const detailPanel = selectedEvent && (
    <>
      <BuyRecommendation event={selectedEvent} snapshots={snapshots} prediction={prediction} />
      <PriceChart snapshots={snapshots} />
    </>
  );

  return (
    <div style={{ minHeight: '100vh', background: '#0d0d1a', color: '#fff', fontFamily: 'system-ui, sans-serif' }}>

      {/* Top nav */}
      <div style={{ background: '#111', borderBottom: '1px solid #222', display: 'flex', alignItems: 'center', flexWrap: 'nowrap', minHeight: 49 }}>
        {!isMobile && (
          <div style={{ padding: '12px 16px', fontWeight: 700, fontSize: 14, opacity: 0.9, whiteSpace: 'nowrap' }}>
            🎟 Ticket Tracker
          </div>
        )}
        <div style={{ display: 'flex', flex: 1 }}>
          {TABS.map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              style={{
                padding: isMobile ? '12px 16px' : '12px 20px',
                background: 'none', border: 'none',
                borderBottom: activeTab === tab.key ? '2px solid #a78bfa' : '2px solid transparent',
                color: activeTab === tab.key ? '#a78bfa' : '#ffffff70',
                fontWeight: activeTab === tab.key ? 600 : 400,
                cursor: 'pointer', fontSize: 13, whiteSpace: 'nowrap',
              }}
            >
              {tab.emoji}{isMobile ? '' : ` ${tab.label}`}
            </button>
          ))}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '0 12px' }}>
          {!isMobile && tokenDays !== null && tokenDays <= 14 && (
            <span style={{ fontSize: 11, color: tokenDays <= 7 ? '#f87171' : '#f59e0b', fontWeight: 600 }}>
              ⚠ {tokenDays}d
            </span>
          )}
          {!isMobile && lastFetch && (
            <span style={{ fontSize: 11, opacity: 0.35 }}>↑ {lastFetch}</span>
          )}
          <button
            onClick={handleFetch}
            disabled={fetching}
            style={{
              padding: '6px 12px', background: '#a78bfa20', border: '1px solid #a78bfa40',
              color: '#a78bfa', borderRadius: 6, cursor: fetching ? 'not-allowed' : 'pointer',
              fontSize: 12, opacity: fetching ? 0.5 : 1,
            }}
          >
            {fetching ? '…' : '↻'}
          </button>
        </div>
      </div>

      {/* Body */}
      {loading ? (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 'calc(100vh - 49px)', opacity: 0.4 }}>
          Loading...
        </div>
      ) : (
        <div style={{ display: 'flex', height: isMobile ? undefined : 'calc(100vh - 49px)', minHeight: isMobile ? 'calc(100vh - 49px)' : undefined }}>

          {/* Browse panel — events tab only, desktop left / mobile top */}
          {activeTab === 'events' && (browseResults.length > 0 || browseLoading) && !isMobile && (
            <BrowsePanel
              query={browseQuery}
              results={browseResults}
              trackedEvents={events}
              onTracked={() => loadEvents(activeTab, true)}
              onClose={() => { setBrowseResults([]); setBrowseQuery(''); setBrowseLoading(false); }}
              isMobile={false}
              loading={browseLoading}
            />
          )}

          {/* Left: grid */}
          <div style={{ flex: 1, overflowY: 'auto', background: '#0d0d1a', minWidth: 0 }}>

            {/* Search bar */}
            <div style={{ borderBottom: '1px solid #1a1a1a', background: '#0d0d1a' }}>
              <EventSearch
                category={activeTab}
                onTracked={() => loadEvents(activeTab, true)}
                events={filteredEvents}
                onSelect={e => setSelectedEvent(e)}
                onBrowseResults={activeTab === 'events' ? (r, q) => { if (r.length === 0 && !q) { setBrowseResults([]); setBrowseQuery(''); } else { setBrowseResults(r); if (q) setBrowseQuery(q); } } : undefined}
                onBrowseLoading={activeTab === 'events' ? setBrowseLoading : undefined}
              />
            </div>

            {/* Mobile browse panel — below search bar */}
            {activeTab === 'events' && (browseResults.length > 0 || browseLoading) && isMobile && (
              <BrowsePanel
                query={browseQuery}
                results={browseResults}
                trackedEvents={events}
                onTracked={() => loadEvents(activeTab, true)}
                onClose={() => { setBrowseResults([]); setBrowseQuery(''); setBrowseLoading(false); }}
                isMobile={true}
                loading={browseLoading}
              />
            )}

            {/* Filter bar */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 14px', flexWrap: 'nowrap', overflowX: 'auto' }}>
              <span style={{ fontSize: 11, opacity: 0.3, whiteSpace: 'nowrap', flexShrink: 0 }}>
                {filteredEvents.length} {activeTab === 'world_cup' ? 'games' : 'events'}
                {loc && ` · ${loc}`}
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 'auto', flexShrink: 0 }}>
                <LocationFilter
                  events={events}
                  value={locationFilter[activeTab]}
                  onChange={c => setLocationFilter(prev => ({ ...prev, [activeTab]: c }))}
                />
                <span style={{ fontSize: 11, opacity: 0.4 }}>🎟</span>
                <select
                  value={quantity[activeTab]}
                  onChange={e => handleQuantityChange(Number(e.target.value))}
                  style={SELECT_STYLE}
                >
                  {[1,2,3,4,5,6].map(n => <option key={n} value={n}>{n}</option>)}
                </select>
              </div>
            </div>

            <WorldCupGrid
              events={filteredEvents}
              selectedId={selectedEvent?.id ?? null}
              onSelect={e => setSelectedEvent(e)}
              onDelete={handleDelete}
              alerts={alerts}
              onAlertsChange={setAlerts}
              showTeams={activeTab === 'world_cup'}
              quantity={quantity[activeTab]}
              isMobile={isMobile}
            />

            {/* Mobile padding so bottom sheet doesn't cover last card */}
            {isMobile && selectedEvent && <div style={{ height: 320 }} />}
          </div>

          {/* Desktop: sidebar detail panel */}
          {!isMobile && selectedEvent && (
            <div style={{ width: 360, borderLeft: '1px solid #1a1a1a', padding: '20px 22px', overflowY: 'auto', background: '#0f0f1c', flexShrink: 0 }}>
              {detailPanel}
            </div>
          )}
        </div>
      )}

      {/* Mobile: backdrop */}
      {isMobile && selectedEvent && (
        <div
          onClick={() => setSelectedEvent(null)}
          style={{ position: 'fixed', inset: 0, zIndex: 299, background: '#00000070', backdropFilter: 'blur(2px)' }}
        />
      )}

      {/* Mobile: bottom sheet detail panel */}
      {isMobile && selectedEvent && (
        <div style={{
          position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 300,
          background: '#1e1e30',
          borderTop: '2px solid #a78bfa',
          borderRadius: '20px 20px 0 0',
          padding: '0 20px 44px',
          maxHeight: '75vh', overflowY: 'auto',
          boxShadow: '0 -20px 60px #000000cc',
        }}>
          {/* Drag handle */}
          <div style={{ display: 'flex', justifyContent: 'center', padding: '12px 0 6px' }}>
            <div style={{ width: 40, height: 4, borderRadius: 2, background: '#a78bfa60' }} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: '#fff', maxWidth: '80%', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {selectedEvent.name}
            </span>
            <button
              onClick={() => setSelectedEvent(null)}
              style={{ background: '#ffffff18', border: 'none', color: '#fff', borderRadius: '50%', width: 28, height: 28, cursor: 'pointer', fontSize: 14, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            >
              ✕
            </button>
          </div>
          {detailPanel}
        </div>
      )}
    </div>
  );
}
