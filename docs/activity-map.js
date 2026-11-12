const SVG_NS = 'http://www.w3.org/2000/svg';
const DAY_MS = 86_400_000;
const number = new Intl.NumberFormat('en');
const share = new Intl.NumberFormat('en', { style: 'percent', maximumFractionDigits: 1 });
const dateLabel = new Intl.DateTimeFormat('en', { dateStyle: 'long', timeZone: 'UTC' });
const monthLabel = new Intl.DateTimeFormat('en', { month: 'short', timeZone: 'UTC' });
const shortDate = new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', timeZone: 'UTC' });
const dayTime = (day) => Date.parse(day.date + 'T00:00:00Z');

function shape(tag, attributes, text) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, value);
  if (text) node.textContent = text;
  return node;
}

export function busiestRun(days) {
  const size = Math.min(days.length, 7);
  let count = 0;
  let peak = { start: 0, end: size - 1, count: 0 };
  for (let index = 0; index < days.length; index++) {
    count += days[index].count;
    if (index >= size) count -= days[index - size].count;
    if (index >= size - 1 && count > peak.count) peak = { start: index - size + 1, end: index, count };
  }
  return peak;
}

export function mountActivityMap(days) {
  const map = document.getElementById('terrain-map');
  const viewport = document.getElementById('terrain-viewport');
  const scrub = document.getElementById('terrain-scrub');
  const previous = document.getElementById('terrain-prev');
  const next = document.getElementById('terrain-next');
  const output = document.getElementById('terrain-point');
  const peak = document.getElementById('terrain-peak');
  const firstTime = dayTime(days[0]);
  const startOffset = (new Date(firstTime).getUTCDay() + 6) % 7;
  const maxCount = Math.max(1, ...days.map((day) => day.count));
  const total = days.reduce((sum, day) => sum + day.count, 0);
  const busiest = busiestRun(days);

  if (total) {
    const start = days[busiest.start];
    const end = days[busiest.end];
    const formatter = start.date.slice(0, 4) === end.date.slice(0, 4) ? shortDate : dateLabel;
    const first = formatter.format(dayTime(start));
    const last = formatter.format(dayTime(end));
    const range = first === last ? first : first + ' – ' + last;
    peak.textContent = 'Busiest ' + (busiest.end - busiest.start + 1) + ' days · ' + range +
      ' · ' + number.format(busiest.count) + ' contributions (' + share.format(busiest.count / total) + ' of the snapshot)';
  } else {
    peak.textContent = 'No contributions in this snapshot.';
  }

  const dates = days.map((day, index) => {
    const slot = startOffset + Math.round((dayTime(day) - firstTime) / DAY_MS);
    const weekday = slot % 7;
    const week = Math.floor(slot / 7);
    const x = 56 + week * 16 + weekday * 4;
    const base = 118 + weekday * 13;
    const strength = Math.sqrt(day.count / maxCount);
    const height = 3 + Math.round(strength * 87);
    const top = base - height;
    const level = day.count ? Math.ceil(strength * 4) : 0;
    const upper = 'M' + x + ',' + top + 'h11l5,8h-11z';
    const column = shape('g', { class: 'terrain-day', 'data-day-index': index, 'data-level': level });
    column.append(
      shape('path', { d: 'M' + (x + 5) + ',' + (top + 8) + 'h11v' + height + 'h-11z', class: 'terrain-front' }),
      shape('path', { d: 'M' + (x + 11) + ',' + top + 'l5,8v' + height + 'l-5,-8z', class: 'terrain-side' }),
      shape('path', { d: upper, class: 'terrain-top' }),
    );
    return { index, weekday, week, upper, column };
  });
  const width = 110 + dates.at(-1).week * 16;
  const labels = shape('g', {});
  ['Mon', 'Wed', 'Fri', 'Sun'].forEach((day, index) => {
    labels.append(shape('text', { x: 17 + index * 8, y: 123 + index * 26 }, day));
  });
  let month = '';
  for (const date of dates) {
    const time = dayTime(days[date.index]);
    const label = monthLabel.format(time);
    if (label === month) continue;
    month = label;
    const x = 55 + date.week * 16;
    labels.append(shape('text', { x, y: 222 }, label));
  }
  const selection = shape('path', { class: 'terrain-selection' });
  const depthOrder = [...dates].sort((a, b) => a.weekday - b.weekday || a.week - b.week);
  map.setAttribute('viewBox', '0 0 ' + width + ' 241');
  map.replaceChildren(...depthOrder.map(({ column }) => column), labels, selection);
  scrub.max = days.length - 1;

  let selected = days.length - 1;

  function inspect(index, reveal = false) {
    selected = Math.min(Math.max(index, 0), days.length - 1);
    const day = days[selected];
    const date = dates[selected];
    const text = dateLabel.format(dayTime(day)) + ' · ' + number.format(day.count) +
      (day.count === 1 ? ' contribution' : ' contributions');
    output.textContent = text;
    scrub.value = selected;
    scrub.setAttribute('aria-valuetext', text);
    selection.setAttribute('d', date.upper);
    previous.disabled = selected === 0;
    next.disabled = selected === days.length - 1;
    if (reveal) {
      const bounds = viewport.getBoundingClientRect();
      const marker = date.column.getBoundingClientRect();
      if (marker.left < bounds.left || marker.right > bounds.right) {
        viewport.scrollLeft += (marker.left + marker.right - bounds.left - bounds.right) / 2;
      }
    }
  }

  map.addEventListener('click', (event) => {
    const column = event.target.closest('[data-day-index]');
    if (column) inspect(Number(column.dataset.dayIndex));
  });
  scrub.addEventListener('input', () => inspect(Number(scrub.value), true));
  previous.addEventListener('click', () => inspect(selected - 1, true));
  next.addEventListener('click', () => inspect(selected + 1, true));
  inspect(selected);
  requestAnimationFrame(() => inspect(selected, true));
}
