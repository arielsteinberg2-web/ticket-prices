import type { Event } from '../types';

const TEAMS: { match: string; iso: string; display: string }[] = [
  // North/Central America & Caribbean
  { match: 'united states', iso: 'us', display: 'United States' },
  { match: 'usa',           iso: 'us', display: 'United States' },
  { match: 'mexico',        iso: 'mx', display: 'Mexico' },
  { match: 'canada',        iso: 'ca', display: 'Canada' },
  { match: 'costa rica',    iso: 'cr', display: 'Costa Rica' },
  { match: 'panama',        iso: 'pa', display: 'Panama' },
  { match: 'honduras',      iso: 'hn', display: 'Honduras' },
  { match: 'jamaica',       iso: 'jm', display: 'Jamaica' },
  { match: 'el salvador',   iso: 'sv', display: 'El Salvador' },
  { match: 'guatemala',     iso: 'gt', display: 'Guatemala' },
  { match: 'haiti',         iso: 'ht', display: 'Haiti' },
  { match: 'trinidad and tobago', iso: 'tt', display: 'Trinidad & Tobago' },
  { match: 'trinidad',      iso: 'tt', display: 'Trinidad & Tobago' },
  { match: 'curaçao',       iso: 'cw', display: 'Curaçao' },
  { match: 'curacao',       iso: 'cw', display: 'Curaçao' },
  // South America
  { match: 'argentina',     iso: 'ar', display: 'Argentina' },
  { match: 'brazil',        iso: 'br', display: 'Brazil' },
  { match: 'brasil',        iso: 'br', display: 'Brazil' },
  { match: 'uruguay',       iso: 'uy', display: 'Uruguay' },
  { match: 'colombia',      iso: 'co', display: 'Colombia' },
  { match: 'ecuador',       iso: 'ec', display: 'Ecuador' },
  { match: 'venezuela',     iso: 've', display: 'Venezuela' },
  { match: 'chile',         iso: 'cl', display: 'Chile' },
  { match: 'paraguay',      iso: 'py', display: 'Paraguay' },
  { match: 'peru',          iso: 'pe', display: 'Peru' },
  { match: 'bolivia',       iso: 'bo', display: 'Bolivia' },
  // Europe
  { match: 'france',        iso: 'fr', display: 'France' },
  { match: 'germany',       iso: 'de', display: 'Germany' },
  { match: 'spain',         iso: 'es', display: 'Spain' },
  { match: 'portugal',      iso: 'pt', display: 'Portugal' },
  { match: 'england',       iso: 'gb-eng', display: 'England' },
  { match: 'netherlands',   iso: 'nl', display: 'Netherlands' },
  { match: 'holland',       iso: 'nl', display: 'Netherlands' },
  { match: 'belgium',       iso: 'be', display: 'Belgium' },
  { match: 'switzerland',   iso: 'ch', display: 'Switzerland' },
  { match: 'croatia',       iso: 'hr', display: 'Croatia' },
  { match: 'serbia',        iso: 'rs', display: 'Serbia' },
  { match: 'poland',        iso: 'pl', display: 'Poland' },
  { match: 'denmark',       iso: 'dk', display: 'Denmark' },
  { match: 'turkey',        iso: 'tr', display: 'Turkey' },
  { match: 'türkiye',       iso: 'tr', display: 'Turkey' },
  { match: 'scotland',      iso: 'gb-sct', display: 'Scotland' },
  { match: 'austria',       iso: 'at', display: 'Austria' },
  { match: 'ukraine',       iso: 'ua', display: 'Ukraine' },
  { match: 'hungary',       iso: 'hu', display: 'Hungary' },
  { match: 'czech republic', iso: 'cz', display: 'Czech Republic' },
  { match: 'czechia',       iso: 'cz', display: 'Czech Republic' },
  { match: 'slovakia',      iso: 'sk', display: 'Slovakia' },
  { match: 'sweden',        iso: 'se', display: 'Sweden' },
  { match: 'norway',        iso: 'no', display: 'Norway' },
  { match: 'romania',       iso: 'ro', display: 'Romania' },
  { match: 'albania',       iso: 'al', display: 'Albania' },
  { match: 'wales',         iso: 'gb-wls', display: 'Wales' },
  { match: 'ireland',       iso: 'ie', display: 'Ireland' },
  { match: 'greece',        iso: 'gr', display: 'Greece' },
  { match: 'iceland',       iso: 'is', display: 'Iceland' },
  { match: 'bosnia',        iso: 'ba', display: 'Bosnia-Herzegovina' },
  { match: 'bosnia-herzegovina', iso: 'ba', display: 'Bosnia-Herzegovina' },
  // Africa
  { match: 'morocco',       iso: 'ma', display: 'Morocco' },
  { match: 'senegal',       iso: 'sn', display: 'Senegal' },
  { match: 'nigeria',       iso: 'ng', display: 'Nigeria' },
  { match: 'cameroon',      iso: 'cm', display: 'Cameroon' },
  { match: "côte d'ivoire", iso: 'ci', display: "Côte d'Ivoire" },
  { match: 'ivory coast',   iso: 'ci', display: "Côte d'Ivoire" },
  { match: "cote d'ivoire", iso: 'ci', display: "Côte d'Ivoire" },
  { match: 'ghana',         iso: 'gh', display: 'Ghana' },
  { match: 'egypt',         iso: 'eg', display: 'Egypt' },
  { match: 'mali',          iso: 'ml', display: 'Mali' },
  { match: 'south africa',  iso: 'za', display: 'South Africa' },
  { match: 'tunisia',       iso: 'tn', display: 'Tunisia' },
  { match: 'algeria',       iso: 'dz', display: 'Algeria' },
  { match: 'cabo verde',    iso: 'cv', display: 'Cabo Verde' },
  { match: 'cape verde',    iso: 'cv', display: 'Cabo Verde' },
  { match: 'democratic republic of congo', iso: 'cd', display: 'DR Congo' },
  { match: 'dr congo',      iso: 'cd', display: 'DR Congo' },
  { match: 'congo dr',     iso: 'cd', display: 'DR Congo' },
  { match: 'korea republic', iso: 'kr', display: 'South Korea' },
  { match: 'curacau',      iso: 'cw', display: 'Curaçao' },
  { match: 'tanzania',      iso: 'tz', display: 'Tanzania' },
  { match: 'comoros',       iso: 'km', display: 'Comoros' },
  { match: 'angola',        iso: 'ao', display: 'Angola' },
  { match: 'mozambique',    iso: 'mz', display: 'Mozambique' },
  { match: 'zimbabwe',      iso: 'zw', display: 'Zimbabwe' },
  // Asia/Oceania
  { match: 'japan',         iso: 'jp', display: 'Japan' },
  { match: 'south korea',   iso: 'kr', display: 'South Korea' },
  { match: 'korea',         iso: 'kr', display: 'South Korea' },
  { match: 'saudi arabia',  iso: 'sa', display: 'Saudi Arabia' },
  { match: 'iran',          iso: 'ir', display: 'Iran' },
  { match: 'australia',     iso: 'au', display: 'Australia' },
  { match: 'uzbekistan',    iso: 'uz', display: 'Uzbekistan' },
  { match: 'iraq',          iso: 'iq', display: 'Iraq' },
  { match: 'jordan',        iso: 'jo', display: 'Jordan' },
  { match: 'qatar',         iso: 'qa', display: 'Qatar' },
  { match: 'china',         iso: 'cn', display: 'China' },
  { match: 'indonesia',     iso: 'id', display: 'Indonesia' },
  { match: 'new zealand',   iso: 'nz', display: 'New Zealand' },
  { match: 'bahrain',       iso: 'bh', display: 'Bahrain' },
  { match: 'oman',          iso: 'om', display: 'Oman' },
];

const CITY_DISPLAY: Record<string, string> = {
  'east rutherford': 'New York',
  'foxborough': 'Boston',
  'inglewood': 'Los Angeles',
  'santa clara': 'San Francisco',
  'arlington': 'Dallas',
  'miami gardens': 'Miami',
  'zapopan': 'Guadalajara',
};

function displayCity(city: string | null): string | null {
  if (!city) return null;
  return CITY_DISPLAY[city.toLowerCase()] ?? city;
}

// Sort longest match first so "south korea" matches before "korea"
const SORTED_TEAMS = [...TEAMS].sort((a, b) => b.match.length - a.match.length);

function extractTeams(name: string): { iso: string; display: string }[] {
  const lower = name.toLowerCase();
  const matched: { iso: string; display: string }[] = [];
  const seenIso = new Set<string>();
  for (const team of SORTED_TEAMS) {
    if (seenIso.has(team.iso)) continue;
    if (lower.includes(team.match)) {
      matched.push({ iso: team.iso, display: team.display });
      seenIso.add(team.iso);
    }
  }
  return matched;
}

function FlagImg({ iso }: { iso: string }) {
  return (
    <img
      src={`https://flagcdn.com/24x18/${iso}.png`}
      width={24}
      height={18}
      style={{ borderRadius: 2, objectFit: 'cover', flexShrink: 0 }}
      alt={iso}
    />
  );
}

function Sparkline({ prices }: { prices: number[] }) {
  if (prices.length < 2) return null;
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;
  const w = 80, h = 24;
  const points = prices.map((p, i) => {
    const x = (i / (prices.length - 1)) * w;
    const y = h - ((p - min) / range) * (h - 4) - 2;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  const isUp = prices[prices.length - 1] > prices[0];
  const color = isUp ? '#f59e0b' : '#34d399';
  return (
    <svg width={w} height={h} style={{ display: 'block', overflow: 'visible' }}>
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}

interface Props {
  events: Event[];
  selectedId: number | null;
  onSelect: (event: Event) => void;
  onDelete: (eventId: number) => void;
}

export function WorldCupGrid({ events, selectedId, onSelect, onDelete }: Props) {
  const sorted = [...events].sort((a, b) => {
    if (!a.event_date) return 1;
    if (!b.event_date) return -1;
    return a.event_date < b.event_date ? -1 : 1;
  });

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
      gap: 12,
      padding: '16px 20px',
      alignContent: 'start',
    }}>
      {sorted.map(event => {
        const isSelected = event.id === selectedId;
        const teams = extractTeams(event.name);
        const change = event.weekly_change_pct;
        const changeColor = change == null ? '#fff' : change > 0 ? '#f59e0b' : '#34d399';
        const changeBg   = change == null ? 'transparent' : change > 0 ? '#3a2a1a' : '#1a3a2a';

        return (
          <div
            key={event.id}
            onClick={() => onSelect(event)}
            style={{
              background: isSelected ? '#2a2a3e' : '#1a1a2e',
              border: isSelected ? '1px solid #a78bfa' : '1px solid #2a2a3a',
              borderRadius: 10,
              padding: '14px 16px',
              cursor: 'pointer',
              position: 'relative',
              transition: 'border-color 0.15s',
            }}
          >
            <button
              onClick={e => { e.stopPropagation(); onDelete(event.id); }}
              style={{
                position: 'absolute', top: 8, right: 10,
                background: 'none', border: 'none', color: '#ffffff25',
                cursor: 'pointer', fontSize: 13, lineHeight: 1, padding: '0 2px',
              }}
              title="Remove"
            >✕</button>

            {teams.length > 0 ? (
              <div style={{ marginBottom: 6, display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 6 }}>
                {teams.map((t, i) => (
                  <span key={t.iso} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                    {i > 0 && <span style={{ opacity: 0.35, fontSize: 11, margin: '0 2px' }}>vs</span>}
                    <FlagImg iso={t.iso} />
                    <span style={{ fontSize: 12, fontWeight: 600 }}>{t.display}</span>
                  </span>
                ))}
              </div>
            ) : (
              <div style={{ fontWeight: 600, fontSize: 13, paddingRight: 20, lineHeight: 1.4, marginBottom: 4 }}>
                {event.name}
              </div>
            )}

            {event.event_date && (
              <div style={{ fontSize: 11, opacity: 0.45, marginTop: 2 }}>
                {new Date(event.event_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
                {event.city ? ` · ${displayCity(event.city)}` : ''}
              </div>
            )}
            {event.venue && (
              <div style={{ fontSize: 11, opacity: 0.3, marginTop: 1 }}>{event.venue}</div>
            )}

            <div style={{ marginTop: 10, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {event.latest_price != null ? (
                  <span style={{ fontWeight: 700, fontSize: 16, color: changeColor }}>
                    ${event.latest_price.toFixed(0)}
                    {event.price_source === 'seatgeek' && (
                      <span style={{ fontSize: 9, opacity: 0.5, marginLeft: 4 }}>via SeatGeek</span>
                    )}
                    {event.price_source === 'tickpick' && (
                      <span style={{ fontSize: 9, opacity: 0.5, marginLeft: 4 }}>via TickPick</span>
                    )}
                  </span>
                ) : (
                  <span style={{ opacity: 0.25, fontSize: 12 }}>No price yet</span>
                )}
                {change != null && (
                  <span style={{
                    fontSize: 10, background: changeBg, color: changeColor,
                    padding: '2px 7px', borderRadius: 4,
                  }}>
                    {change > 0 ? '▲' : '▼'} {Math.abs(change)}%
                  </span>
                )}
              </div>
              {event.price_history && event.price_history.length >= 2 && (
                <Sparkline prices={event.price_history} />
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
