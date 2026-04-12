const TEAMS: { match: string; iso: string; display: string }[] = [
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
  { match: 'curacau',       iso: 'cw', display: 'Curaçao' },
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
  { match: 'congo dr',      iso: 'cd', display: 'DR Congo' },
  { match: 'tanzania',      iso: 'tz', display: 'Tanzania' },
  { match: 'comoros',       iso: 'km', display: 'Comoros' },
  { match: 'angola',        iso: 'ao', display: 'Angola' },
  { match: 'mozambique',    iso: 'mz', display: 'Mozambique' },
  { match: 'zimbabwe',      iso: 'zw', display: 'Zimbabwe' },
  { match: 'japan',         iso: 'jp', display: 'Japan' },
  { match: 'south korea',   iso: 'kr', display: 'South Korea' },
  { match: 'korea republic', iso: 'kr', display: 'South Korea' },
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

const SORTED_TEAMS = [...TEAMS].sort((a, b) => b.match.length - a.match.length);

export function extractTeams(name: string): { iso: string; display: string }[] {
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

export function FlagImg({ iso, size = 24 }: { iso: string; size?: number }) {
  const h = Math.round(size * 0.75);
  return (
    <img
      src={`https://flagcdn.com/${size}x${h}/${iso}.png`}
      width={size}
      height={h}
      style={{ borderRadius: 2, objectFit: 'cover', flexShrink: 0 }}
      alt={iso}
    />
  );
}
