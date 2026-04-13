import { useEffect, useState, useCallback } from 'react';
import type { Category, Event, PriceSnapshot, Prediction } from './types';
import { fetchEvents, fetchHistory, fetchPrediction, triggerFetch, deleteEvent, fetchStatus, setQuantity } from './api';
import { WorldCupGrid } from './components/WorldCupGrid';
import { PriceChart } from './components/PriceChart';
import { BuyRecommendation } from './components/BuyRecommendation';
import { EventSearch } from './components/EventSearch';
import { LocationFilter } from './components/LocationFilter';

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
  const [quantity, setQuantityState] = useState<Record<Category, number>>({ world_cup: 1, events: 1 });
  const [settingQty, setSettingQty] = useState(false);
  const [locationFilter, setLocationFilter] = useState<Record<Category, string>>({ world_cup: '', events: '' });
  const [lastFetch, setLastFetch] = useState<string | null>(null);
  const [tokenDays, setTokenDays] = useState<number | null>(null);

  useEffect(() => {
    fetchStatus().then(s => setTokenDays(s?.tickpick_token?.days_remaining ?? null));
  }, []);

  const loadEvents = useCallback(async (category: Category, silent = false) => {
    if (!silent) setLoading(true);
    try {
      const data = await fetchEvents(category);
      setEvents(data);
      if (!silent) setSelectedEvent(prev => prev ?? (data[0] ?? null));
      // Sync quantity dropdown to what's stored in DB (use first event's quantity)
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

  const handleQuantityChange = async (q: number) => {
    setSettingQty(true);
    try {
      await setQuantity(activeTab, q);
      setQuantityState(prev => ({ ...prev, [activeTab]: q }));
      await loadEvents(activeTab, true);
    } finally {
      setSettingQty(false);
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
            <div style={{ padding: '12px 20px 0', borderBottom: '1px solid #222', background: '#111', maxWidth: 480 }}>
              <EventSearch category="world_cup" onTracked={() => loadEvents('world_cup', true)} events={events} onSelect={e => setSelectedEvent(e)} />
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '6px 20px' }}>
              <span style={{ fontSize: 11, opacity: 0.3 }}>
                {events.filter(e => !locationFilter['world_cup'] || e.city === locationFilter['world_cup']).length} games
                {locationFilter['world_cup'] && ` in ${locationFilter['world_cup']}`}
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginLeft: 'auto' }}>
                <LocationFilter events={events} value={locationFilter['world_cup']} onChange={c => setLocationFilter(prev => ({ ...prev, world_cup: c }))} />
                <span style={{ fontSize: 11, opacity: 0.5 }}>🎟</span>
                <select value={quantity[activeTab]} onChange={e => handleQuantityChange(Number(e.target.value))} disabled={settingQty}
                  style={{ background: '#1a1a2e', border: '1px solid #333', color: '#a78bfa', borderRadius: 5, padding: '3px 8px', fontSize: 12, cursor: 'pointer', opacity: settingQty ? 0.5 : 1 }}>
                  {[1,2,3,4,5,6].map(n => <option key={n} value={n}>{n}</option>)}
                </select>
                {settingQty && <span style={{ fontSize: 11, opacity: 0.4 }}>Updating…</span>}
              </div>
            </div>
            <WorldCupGrid
              events={events.filter(e => !locationFilter['world_cup'] || e.city === locationFilter['world_cup'])}
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
        /* Events tab — card grid + detail panel */
        <div style={{ display: 'flex', height: 'calc(100vh - 49px)' }}>
          <div style={{ flex: 1, overflowY: 'auto', background: '#0d0d1a' }}>
            <div style={{ padding: '12px 20px 0', borderBottom: '1px solid #222', background: '#111', maxWidth: 480 }}>
              <EventSearch category="events" onTracked={() => loadEvents('events', true)} events={events} onSelect={e => setSelectedEvent(e)} />
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '6px 20px' }}>
              <span style={{ fontSize: 11, opacity: 0.3 }}>
                {events.filter(e => !locationFilter['events'] || e.city === locationFilter['events']).length} events
                {locationFilter['events'] && ` in ${locationFilter['events']}`}
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginLeft: 'auto' }}>
                <LocationFilter events={events} value={locationFilter['events']} onChange={c => setLocationFilter(prev => ({ ...prev, events: c }))} />
                <span style={{ fontSize: 11, opacity: 0.5 }}>🎟</span>
                <select value={quantity[activeTab]} onChange={e => handleQuantityChange(Number(e.target.value))} disabled={settingQty}
                  style={{ background: '#1a1a2e', border: '1px solid #333', color: '#a78bfa', borderRadius: 5, padding: '3px 8px', fontSize: 12, cursor: 'pointer', opacity: settingQty ? 0.5 : 1 }}>
                  {[1,2,3,4,5,6].map(n => <option key={n} value={n}>{n}</option>)}
                </select>
                {settingQty && <span style={{ fontSize: 11, opacity: 0.4 }}>Updating…</span>}
              </div>
            </div>
            <WorldCupGrid
              events={events.filter(e => !locationFilter['events'] || e.city === locationFilter['events'])}
              selectedId={selectedEvent?.id ?? null}
              onSelect={e => setSelectedEvent(e)}
              onDelete={handleDelete}
              showTeams={false}
            />
          </div>
          {selectedEvent && (
            <div style={{ width: 380, borderLeft: '1px solid #333', padding: '20px 24px', overflowY: 'auto', background: '#13131f', flexShrink: 0 }}>
              <BuyRecommendation event={selectedEvent} snapshots={snapshots} prediction={prediction} />
              <PriceChart snapshots={snapshots} slope={prediction?.slope} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
