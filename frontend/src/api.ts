import axios from 'axios';
import type { Event, PriceSnapshot, Prediction, Category } from './types';

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
