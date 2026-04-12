import axios from 'axios';
import type { Event, PriceSnapshot, Prediction, Category, SearchResult } from './types';

const base = axios.create({ baseURL: '/api' });

export async function fetchEvents(category?: Category): Promise<Event[]> {
  const params = category ? { category } : {};
  const { data } = await base.get<Event[]>('/events', { params });
  return data;
}

export async function fetchHistory(eventId: number): Promise<PriceSnapshot[]> {
  const { data } = await base.get<PriceSnapshot[]>(`/events/${eventId}/history`);
  return data;
}

export async function fetchPrediction(eventId: number): Promise<Prediction> {
  const { data } = await base.get<Prediction>(`/events/${eventId}/prediction`);
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

export async function fetchStatus(): Promise<any> {
  const { data } = await base.get('/status');
  return data;
}
