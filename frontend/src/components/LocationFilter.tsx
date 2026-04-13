import { useState, useRef, useEffect } from 'react';
import type { Event } from '../types';

interface Props {
  events: Event[];
  value: string;
  onChange: (city: string) => void;
}

export function LocationFilter({ events, value, onChange }: Props) {
  const [input, setInput] = useState(value);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Unique cities sorted alphabetically
  const cities = Array.from(
    new Set(events.map(e => e.city).filter(Boolean) as string[])
  ).sort();

  const suggestions = input.trim().length >= 1
    ? cities.filter(c => c.toLowerCase().includes(input.trim().toLowerCase()))
    : cities;

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Keep input in sync if value is cleared externally
  useEffect(() => { setInput(value); }, [value]);

  const select = (city: string) => {
    setInput(city);
    onChange(city);
    setOpen(false);
  };

  const clear = () => {
    setInput('');
    onChange('');
    setOpen(false);
  };

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        <span style={{ fontSize: 11, opacity: 0.5 }}>📍</span>
        <input
          value={input}
          onChange={e => { setInput(e.target.value); setOpen(true); if (!e.target.value) onChange(''); }}
          onFocus={() => setOpen(true)}
          placeholder="All cities"
          style={{
            width: 130, padding: '3px 6px', background: '#1a1a2e',
            border: '1px solid #333', borderRadius: 5, color: '#fff',
            fontSize: 12, outline: 'none',
          }}
        />
        {value && (
          <button onClick={clear} style={{ background: 'none', border: 'none', color: '#ffffff50', cursor: 'pointer', fontSize: 13, lineHeight: 1, padding: 0 }}>✕</button>
        )}
      </div>

      {open && suggestions.length > 0 && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, marginTop: 4,
          background: '#1a1a2e', border: '1px solid #333', borderRadius: 6,
          zIndex: 200, maxHeight: 200, overflowY: 'auto', minWidth: 160,
          boxShadow: '0 4px 16px #00000060',
        }}>
          {suggestions.map(city => (
            <div
              key={city}
              onMouseDown={() => select(city)}
              style={{
                padding: '7px 12px', fontSize: 12, cursor: 'pointer',
                background: city === value ? '#2a2a4e' : 'transparent',
                color: city === value ? '#a78bfa' : '#fff',
              }}
              onMouseEnter={e => (e.currentTarget.style.background = '#2a2a3e')}
              onMouseLeave={e => (e.currentTarget.style.background = city === value ? '#2a2a4e' : 'transparent')}
            >
              {city}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
