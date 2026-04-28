export type Category = 'world_cup' | 'events';

export interface Event {
  id: number;
  name: string;
  category: Category;
  event_date: string | null;
  venue: string | null;
  city: string | null;
  quantity: number;
  latest_price: number | null;
  weekly_change_pct: number | null;
  snapshot_count: number;
  price_source?: string | null;
  price_history?: number[];
  prices_by_qty?: Record<number, number>;
}

export interface PriceSnapshot {
  fetched_at: string;
  lowest_price: number;
}

export interface Prediction {
  has_data: boolean;
  trend?: 'rising' | 'falling' | 'flat';
  predicted_price_7d?: number;
  recommendation?: 'BUY NOW' | 'BUY SOON' | 'WAIT';
  slope?: number;
  message?: string;
}

export interface SearchResult {
  ticketmaster_id: string;
  name: string;
  category: string;
  event_date: string | null;
  venue: string | null;
  city: string | null;
  lowest_price: number | null;
  already_tracked: boolean;
  event_id?: number | null;
  tickpick_url?: string;
}
