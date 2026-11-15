import { brazilOutline } from './brazil-outline';

// Each Bézier motif starts and ends with the same tangent. Translating by one
// motif keeps the flow continuous even when ribbons have different periods.
export function mapRibbons(): string {
  const ribbons = [
    {width: 820, base: 256, lift: -174, dip: 112, fold: 78, phase: 96, seconds: 38},
    {width: 680, base: 274, lift: 116, dip: -102, fold: -58, phase: 220, seconds: 32},
    {width: 930, base: 241, lift: -111, dip: 148, fold: -63, phase: 420, seconds: 46},
    {width: 710, base: 281, lift: -83, dip: 70, fold: 45, phase: 70, seconds: 28}
  ];
  const layers = ribbons.map(({width, base, lift, dip, fold, phase, seconds}, index) => {
    const half = width / 2;
    const curve = (a: number, b: number) =>
      `c${half * .46} 0 ${half * .68} ${a} ${half} ${a} s${half * .55} ${-a} ${half} ${-a} c${half * .46} 0 ${half * .67} ${b} ${half} ${b} s${half * .55} ${-b} ${half} ${-b}`;
    const period = 2 * width;
    const start = -period + phase;
    const edge = `M${start} ${base} ${(curve(lift,dip)+' ').repeat(3)}`;
    const other = `M${start} ${base} ${(curve(lift + fold,dip - fold)+' ').repeat(3)}`;
    // Even-odd filling leaves just the silk between the two crossing edges.
    const close = `V530 H${start} Z`;
    const filled = `${edge} ${close} ${other} ${close}`;
    return `<g class="map-ribbon" style="--period:${period}px;--duration:${seconds}s;--phase:-${seconds*.41}s;--fold-time:${5.8 + index * 1.3}s;--fold-origin:${base}px"><g class="ribbon-fold">
      <path d="${filled}" fill="url(#ribbon-silk)" fill-rule="evenodd"/>
      <path d="${edge}" fill="none" stroke="#ac50ff" stroke-opacity=".16" stroke-width="6"/>
      <path d="${edge}" fill="none" stroke="url(#ribbon-thread)" stroke-width="1.65"/>
      <path d="${other}" fill="none" stroke="#b878ff" stroke-opacity=".42" stroke-width=".8"/>
    </g></g>`;
  });
  return `<svg viewBox="0 0 1000 530" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><defs>
    <linearGradient id="ribbon-silk" x1="0" y1="0" x2=".24" y2="1">
      <stop stop-color="#8541ec" stop-opacity=".08"/><stop offset=".42" stop-color="#9248fc" stop-opacity=".35"/>
      <stop offset=".67" stop-color="#e5c2ff" stop-opacity=".42"/><stop offset="1" stop-color="#7830d0" stop-opacity=".06"/>
    </linearGradient>
    <linearGradient id="ribbon-thread" x2="0" y2="1">
      <stop stop-color="#944afa" stop-opacity=".55"/><stop offset=".54" stop-color="#efd9ff"/><stop offset="1" stop-color="#bf85ff" stop-opacity=".68"/>
    </linearGradient>
  </defs><g class="map-current" aria-hidden="true">${layers.join('')}</g></svg>`;
}
const cities = [
  {name: 'Manaus', lon: -60.02, lat: -3.12},
  {name: 'Belém', lon: -48.49, lat: -1.46},
  {name: 'Fortaleza', lon: -38.53, lat: -3.73},
  {name: 'Recife', lon: -34.88, lat: -8.05},
  {name: 'Salvador', lon: -38.50, lat: -12.97},
  {name: 'Cuiabá', lon: -56.10, lat: -15.60},
  {name: 'Rio Branco', lon: -67.81, lat: -9.97},
  {name: 'São Paulo', lon: -46.63, lat: -23.55},
  {name: 'Porto Alegre', lon: -51.23, lat: -30.03}
];

function project(lon: number, lat: number) {
  return {x: 156 + (lon + 74) * 12, y: 24 + (6 - lat) * 12};
}

export function drawMap(): string {
  // Brasília is the illustrative destination; the page does not request device location.
  const user = project(-47.88, -15.79);
  const routes = cities.map(({lon, lat}, i) => {
    const {x, y} = project(lon, lat);
    const cx = (x + user.x) / 2 + (user.y - y) * .21;
    const cy = (y + user.y) / 2 - (user.x - x) * .21;
    const path = `M${x} ${y} Q${cx} ${cy} ${user.x} ${user.y}`;
    return `<g style="--departure:${i * .18}s">
      <mask id="draw-route-${i}" maskUnits="userSpaceOnUse" x="90" y="0" width="640" height="530">
        <path class="route-reveal" d="${path}" pathLength="1" fill="none" stroke="white" stroke-width="6" stroke-dasharray="1 1"/>
      </mask>
      <path d="${path}" mask="url(#draw-route-${i})" fill="none" stroke="#c9ff98" stroke-width="1.8" stroke-linecap="round" stroke-dasharray="4 5"/>
    </g>`;
  });
  const labels = cities.map(({name, lon, lat}) => {
    const {x,y} = project(lon, lat);
    return `<g transform="translate(${x} ${y})"><circle r="4.3" fill="#bbff80" stroke="#1e1829" stroke-width="2"/><text x="6" y="-7">${name}</text></g>`;
  });
  return `<svg viewBox="152 43 534 434" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Nove cidades brasileiras convergem para um marcador ilustrativo do usuário em Brasília.">
    <defs><pattern id="territory-grid" width="17" height="17" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r=".85" fill="#ab85ca" opacity=".43"/></pattern></defs>
    <path d="${brazilOutline}" fill="#302138"/>
    <path d="${brazilOutline}" fill="url(#territory-grid)" stroke="#9976ae" stroke-width="1.4"/>

    ${routes.join('')}
    <g class="city-labels">${labels.join('')}</g>
    <g transform="translate(${user.x} ${user.y})"><ellipse rx="19" ry="6" fill="#bcff7b" opacity=".18"/>
    <path d="M0 0C-3-6-12-15-12-22a12 12 0 1 1 24 0C12-15 3-6 0 0" fill="#bcff7b" stroke="#251b30" stroke-width="2"/>
    <circle cy="-22" r="4" fill="#251b30"/><text class="user-label" x="17" y="-17">Você</text></g></svg>`;
}