import { useEffect, useState, useCallback } from 'react';
import type { Category, Event, PriceSnapshot, Prediction } from './types';
import { fetchEvents, fetchHistory, fetchPrediction, triggerFetch } from './api';
import { EventList } from './components/EventList';
import { PriceChart } from './components/PriceChart';
import { BuyRecommendation } from './components/BuyRecommendation';
import { EventSearch } from './components/EventSearch';

const TABS: { key: Category; label: string; emoji: string }[] = [
  { key: 'world_cup', label: 'World Cup 2026', emoji: '⚽' },
  { key: 'sports',    label: 'Sports',          emoji: '🏆' },
];

export default function App() {
  const [activeTab, setActiveTab] = useState<Category>('world_cup');
  const [events, setEvents] = useState<Event[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [snapshots, setSnapshots] = useState<PriceSnapshot[]>([]);
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(false);
  const [lastFetch, setLastFetch] = useState<string | null>(null);
  const [showSearch, setShowSearch] = useState(false);

  const loadEvents = useCallback(async (category: Category) => {
    setLoading(true);
    try {
      const data = await fetchEvents(category);
      setEvents(data);
      setSelectedEvent(prev => prev ?? (data[0] ?? null));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setSelectedEvent(null);
    setSnapshots([]);
    setPrediction(null);
    setShowSearch(false);
    loadEvents(activeTab);
  }, [activeTab, loadEvents]);

  useEffect(() => {
    if (!selectedEvent) return;
    setSnapshots([]);
    setPrediction(null);
    Promise.all([
      fetchHistory(selectedEvent.id),
      fetchPrediction(selectedEvent.id),
    ]).then(([hist, pred]) => {
      setSnapshots(hist);
      setPrediction(pred);
    });
  }, [selectedEvent]);

  const handleFetch = async () => {
    setFetching(true);
    try {
      await triggerFetch();
      setLastFetch(new Date().toLocaleTimeString());
      await loadEvents(activeTab);
    } finally {
      setFetching(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', background: '#0d0d1a', color: '#fff', fontFamily: 'system-ui, sans-serif' }}>
      {/* Top nav */}
      <div style={{ background: '#111', borderBottom: '1px solid #333', display: 'flex', alignItems: 'center' }}>
        <div style={{ padding: '12px 20px', fontWeight: 700, fontSize: 15, opacity: 0.9 }}>
          🎟 Ticket Price Tracker
        </div>
        <div style={{ display: 'flex', flex: 1 }}>
          {TABS.map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              style={{
                padding: '12px 22px', background: 'none', border: 'none',
                borderBottom: activeTab === tab.key ? '2px solid #a78bfa' : '2px solid transparent',
                color: activeTab === tab.key ? '#a78bfa' : '#ffffff80',
                fontWeight: activeTab === tab.key ? 600 : 400,
                cursor: 'pointer', fontSize: 13,
              }}
            >
              {tab.emoji} {tab.label}
            </button>
          ))}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '0 20px' }}>
          {lastFetch && <span style={{ fontSize: 11, opacity: 0.4 }}>Last fetch: {lastFetch}</span>}
          <button
            onClick={handleFetch}
            disabled={fetching}
            style={{
              padding: '6px 14px', background: '#a78bfa20', border: '1px solid #a78bfa50',
              color: '#a78bfa', borderRadius: 6, cursor: fetching ? 'not-allowed' : 'pointer',
              fontSize: 12, opacity: fetching ? 0.5 : 1,
            }}
          >
            {fetching ? 'Fetching...' : '↻ Fetch Now'}
          </button>
        </div>
      </div>

      {/* Body */}
      {loading ? (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 'calc(100vh - 49px)', opacity: 0.4 }}>
          Loading events...
        </div>
      ) : (
        <div style={{ display: 'flex', height: 'calc(100vh - 49px)' }}>
          {/* Left panel */}
          <div style={{ width: 280, borderRight: '1px solid #333', display: 'flex', flexDirection: 'column', background: '#161622' }}>
            {/* Search toggle */}
            <div style={{ padding: '8px 12px', borderBottom: '1px solid #333', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 11, opacity: 0.4, textTransform: 'uppercase', letterSpacing: 1 }}>
                {events.length} events
              </span>
              <button
                onClick={() => setShowSearch(s => !s)}
                style={{
                  background: showSearch ? '#a78bfa20' : 'none',
                  border: `1px solid ${showSearch ? '#a78bfa' : '#333'}`,
                  color: showSearch ? '#a78bfa' : '#ffffff60',
                  borderRadius: 5, padding: '3px 10px', fontSize: 11, cursor: 'pointer',
                }}
              >
                {showSearch ? '✕ Close' : '+ Add Events'}
              </button>
            </div>

            {/* Search panel */}
            {showSearch && (
              <EventSearch
                category={activeTab}
                onTracked={() => loadEvents(activeTab)}
              />
            )}

            {/* Event list */}
            <EventList
              events={events}
              selectedId={selectedEvent?.id ?? null}
              onSelect={e => setSelectedEvent(e)}
            />
          </div>

          {/* Detail panel */}
          <div style={{ flex: 1, padding: '20px 24px', overflowY: 'auto', background: '#13131f' }}>
            {selectedEvent ? (
              <>
                <BuyRecommendation event={selectedEvent} snapshots={snapshots} prediction={prediction} />
                <PriceChart snapshots={snapshots} slope={prediction?.slope} />
              </>
            ) : (
              <div style={{ opacity: 0.3, marginTop: 60, textAlign: 'center' }}>
                Select an event to see its price history
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
