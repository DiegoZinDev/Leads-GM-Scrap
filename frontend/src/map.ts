// Schematic urban blocks use a fixed grid so the map is identical on every visit.
export function drawMap(): string {
  let blocks = '';
  for (let row = -5; row < 16; row++) {
    for (let col = -5; col < 17; col++) {
      const x = col * 58 + (row % 3) * 8;
      const y = row * 37;
      const fill = ['#282032','#251e2f','#30263b','#211c2b'][Math.abs(col * 3 + row * 7) % 4];
      blocks += `<path d="M${x},${y}h47l-2,27h-47z" fill="${fill}" stroke="#46354f" stroke-width=".8"/>`;
    }
  }
  const routes = [
    {d:'M372 285 L404 258 L447 268 L489 213 L530 224 L580 150',x:580,y:150,name:'Farmácia',align:1},
    {d:'M372 285 L330 273 L291 309 L245 294 L203 346',x:203,y:346,name:'Studio',align:-1},
    {d:'M372 285 L415 300 L398 335 L484 358 L465 398 L521 415',x:521,y:415,name:'Café',align:1},
    {d:'M372 285 L348 241 L376 197 L332 176 L355 134',x:355,y:134,name:'Clínica',align:-1}
  ];
  return `<svg viewBox="0 0 760 530" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><defs><mask id="edge"><rect width="760" height="530" fill="white"/></mask></defs>
  <g transform="rotate(-22 380 265) skewX(8)">${blocks}</g>
  <path d="M80 -20 Q115 80 229 105T477 181T815 245" fill="none" stroke="#15121e" stroke-width="22"/>
  <path d="M80 -20 Q115 80 229 105T477 181T815 245" fill="none" stroke="#392948" stroke-width="10"/>
  <g fill="none" stroke="#63506f" stroke-width="2"><path d="M-40 385 Q212 181 780 349"/><path d="M242 560 Q330 305 676 -15"/></g>
  <g class="district" fill="#a38eaf" font-family="sans-serif" font-size="10" letter-spacing="3"><text x="445" y="90">BELA VISTA</text><text x="180" y="232">CONSOLAÇÃO</text><text x="330" y="465">JARDINS</text></g>
  ${routes.map((r,i)=>`<g style="--delay:${i*.23}s"><path d="${r.d}" fill="none" stroke="#24182d" stroke-width="6"/><path class="route" d="${r.d}" pathLength="100" fill="none" stroke="#b6fb75" stroke-width="2.4" stroke-dasharray="5 5"/><circle cx="${r.x}" cy="${r.y}" r="7" fill="#211729" stroke="#c3ff90" stroke-width="2"/><circle cx="${r.x}" cy="${r.y}" r="2.4" fill="#c3ff90"/><text x="${r.x+13*r.align}" y="${r.y+4}" text-anchor="${r.align>0?'start':'end'}" fill="#f2ecf4" stroke="#201927" stroke-width="4" paint-order="stroke" font-family="sans-serif" font-size="13">${r.name}</text></g>`).join('')}
  <g transform="translate(372 285)"><ellipse rx="32" ry="12" fill="#bcff7b" opacity=".13"/><path d="M0 0C-4 -8 -21 -20 -21 -34a21 21 0 1 1 42 0C21 -20 4 -8 0 0" fill="#bcff7b"/><circle cy="-34" r="7" fill="#251b30"/></g></svg>`;
}
