import axios from 'axios';
import type { Event, PriceSnapshot, Prediction, Category, SearchResult } from './types';

function getUserId(): string {
  let id = localStorage.getItem('ticket_user_id');
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem('ticket_user_id', id);
  }
  return id;
}

const base = axios.create({ baseURL: '/api' });
base.interceptors.request.use(config => {
  config.headers['X-User-Id'] = getUserId();
  return config;
});

export async function fetchEvents(category?: Category): Promise<Event[]> {
  const params = category ? { category } : {};
  const { data } = await base.get<Event[]>('/events', { params });
  return data;
}

export async function fetchHistory(eventId: number, quantity?: number): Promise<PriceSnapshot[]> {
  const params = quantity ? { quantity } : {};
  const { data } = await base.get<PriceSnapshot[]>(`/events/${eventId}/history`, { params });
  return data;
}

export async function fetchPrediction(eventId: number, quantity?: number): Promise<Prediction> {
  const params = quantity ? { quantity } : {};
  const { data } = await base.get<Prediction>(`/events/${eventId}/prediction`, { params });
  return data;
}

export async function triggerFetch(): Promise<void> {
  await base.post('/fetch');
}

export async function searchEvents(q: string, category: string): Promise<SearchResult[]> {
  const { data } = await base.get<SearchResult[]>('/search', { params: { q, category } });
  return data;
}

export async function trackEvent(result: SearchResult): Promise<{ status: string; id: number }> {
  const { data } = await base.post('/track', result);
  return data;
}

export async function deleteEvent(eventId: number): Promise<void> {
  await base.delete(`/events/${eventId}`);
}

export async function setQuantity(category: string, quantity: number): Promise<void> {
  await base.post('/quantity', { category, quantity });
}

export async function fetchStatus(): Promise<any> {
  const { data } = await base.get('/status');
  return data;
}
