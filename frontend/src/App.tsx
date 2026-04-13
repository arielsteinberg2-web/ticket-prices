import { useEffect, useState, useCallback } from 'react';
import type { Category, Event, PriceSnapshot, Prediction } from './types';
import { fetchEvents, fetchHistory, fetchPrediction, triggerFetch, deleteEvent, fetchStatus } from './api';
import { EventList } from './components/EventList';
import { WorldCupGrid } from './components/WorldCupGrid';
import { PriceChart } from './components/PriceChart';
import { BuyRecommendation } from './components/BuyRecommendation';
import { EventSearch } from './components/EventSearch';

const TABS: { key: Category; label: string; emoji: string }[] = [
  { key: 'world_cup', label: 'World Cup 2026', emoji: '⚽' },
  { key: 'events',    label: 'Events',          emoji: '🎭' },
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
  const [showSearch] = useState(true);
  const [tokenDays, setTokenDays] = useState<number | null>(null);

  useEffect(() => {
    fetchStatus().then(s => setTokenDays(s?.tickpick_token?.days_remaining ?? null));
  }, []);

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

  const handleDelete = async (eventId: number) => {
    await deleteEvent(eventId);
    if (selectedEvent?.id === eventId) setSelectedEvent(null);
    await loadEvents(activeTab);
  };

  const handleFetch = async () => {
    setFetching(true);
    try {
      await triggerFetch();
      setLastFetch(new Date().toLocaleString(undefined, { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false }));
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
          {tokenDays !== null && tokenDays <= 14 && (
            <span style={{ fontSize: 11, color: tokenDays <= 7 ? '#f87171' : '#f59e0b', fontWeight: 600 }}>
              ⚠ TickPick token expires in {tokenDays}d
            </span>
          )}
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
      ) : activeTab === 'world_cup' ? (
        /* World Cup — card grid + detail panel */
        <div style={{ display: 'flex', height: 'calc(100vh - 49px)' }}>
          <div style={{ flex: 1, overflowY: 'auto', background: '#0d0d1a' }}>
            <div style={{ padding: '12px 20px 0', borderBottom: '1px solid #222', background: '#111' }}>
              <EventSearch category="world_cup" onTracked={() => loadEvents('world_cup')} events={events} onSelect={e => setSelectedEvent(e)} />
            </div>
            <div style={{ padding: '6px 8px', fontSize: 11, opacity: 0.3, paddingLeft: 20 }}>
              {events.length} games tracked
            </div>
            <WorldCupGrid
              events={events}
              selectedId={selectedEvent?.id ?? null}
              onSelect={e => setSelectedEvent(e)}
              onDelete={handleDelete}
            />
          </div>
          {selectedEvent && (
            <div style={{ width: 380, borderLeft: '1px solid #333', padding: '20px 24px', overflowY: 'auto', background: '#13131f', flexShrink: 0 }}>
              <BuyRecommendation event={selectedEvent} snapshots={snapshots} prediction={prediction} />
              <PriceChart snapshots={snapshots} slope={prediction?.slope} />
            </div>
          )}
        </div>
      ) : (
        /* Events tab — sidebar + detail panel */
        <div style={{ display: 'flex', height: 'calc(100vh - 49px)', overflow: 'hidden' }}>
          {/* Left panel */}
          <div style={{ width: 320, flexShrink: 0, borderRight: '1px solid #222', display: 'flex', flexDirection: 'column', background: '#111118', overflow: 'hidden' }}>
            <EventSearch
              category={activeTab}
              onTracked={() => loadEvents(activeTab)}
              events={events}
              onSelect={e => setSelectedEvent(e)}
            />
            <div style={{ padding: '6px 14px 4px', fontSize: 11, opacity: 0.3, letterSpacing: 0.5 }}>
              {events.length} tracked events
            </div>
            <EventList
              events={events}
              selectedId={selectedEvent?.id ?? null}
              onSelect={e => setSelectedEvent(e)}
              onDelete={handleDelete}
            />
          </div>

          {/* Detail panel */}
          <div style={{ flex: 1, overflowY: 'auto', background: '#0d0d1a', padding: '28px 32px' }}>
            {selectedEvent ? (
              <div style={{ maxWidth: 680, margin: '0 auto' }}>
                <BuyRecommendation event={selectedEvent} snapshots={snapshots} prediction={prediction} />
                <PriceChart snapshots={snapshots} slope={prediction?.slope} />
              </div>
            ) : (
              <div style={{ opacity: 0.3, marginTop: 80, textAlign: 'center', fontSize: 14 }}>
                Select an event to see its price history
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
