const number = new Intl.NumberFormat('en');
const share = new Intl.NumberFormat('en', { style: 'percent', maximumFractionDigits: 1 });
const fullDate = new Intl.DateTimeFormat('en', { dateStyle: 'full', timeZone: 'UTC' });
const monthLabel = new Intl.DateTimeFormat('en', { month: 'long', year: 'numeric', timeZone: 'UTC' });
const shortDate = new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', timeZone: 'UTC' });
const utcDate = (date) => new Date(date + 'T00:00:00Z');

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

export function monthLayout(month) {
  const first = utcDate(month + '-01');
  const offset = (first.getUTCDay() + 6) % 7;
  const next = new Date(first);
  next.setUTCMonth(next.getUTCMonth() + 1, 0);
  return { offset, length: next.getUTCDate() };
}

export function mountActivityCalendar(days) {
  const grid = document.getElementById('calendar-grid');
  const previous = document.getElementById('calendar-prev');
  const next = document.getElementById('calendar-next');
  const heading = document.getElementById('calendar-month');
  const summary = document.getElementById('calendar-month-total');
  const output = document.getElementById('calendar-point');
  const peak = document.getElementById('calendar-peak');
  const months = new Map();
  const dates = new Map();
  days.forEach((day, index) => {
    const month = day.date.slice(0, 7);
    if (!months.has(month)) months.set(month, []);
    months.get(month).push(index);
    dates.set(day.date, index);
  });
  const monthKeys = [...months.keys()];
  const total = days.reduce((sum, day) => sum + day.count, 0);
  const busiest = busiestRun(days);
  if (total) {
    const start = days[busiest.start].date;
    const end = days[busiest.end].date;
    const formatter = start.slice(0, 4) === end.slice(0, 4) ? shortDate : fullDate;
    const range = formatter.format(utcDate(start)) + (start === end ? '' : ' – ' + formatter.format(utcDate(end)));
    peak.textContent = 'Busiest ' + (busiest.end - busiest.start + 1) + ' days · ' + range +
      ' · ' + number.format(busiest.count) + ' contributions (' + share.format(busiest.count / total) + ' of the snapshot)';
  } else {
    peak.textContent = 'No contributions in this snapshot.';
  }

  let selected = days.length - 1;
  let displayedMonth = '';

  function describe(day) {
    return fullDate.format(utcDate(day.date)) + ' · ' + number.format(day.count) +
      (day.count === 1 ? ' contribution' : ' contributions');
  }

  function renderMonth(month) {
    const records = months.get(month).map((index) => days[index]);
    const monthCount = records.reduce((sum, day) => sum + day.count, 0);
    const active = records.filter((day) => day.count > 0).length;
    const { offset, length } = monthLayout(month);
    const elements = [];
    for (let position = 0; position < offset; position++) {
      const blank = document.createElement('span');
      blank.setAttribute('aria-hidden', 'true');
      elements.push(blank);
    }
    for (let date = 1; date <= length; date++) {
      const key = month + '-' + String(date).padStart(2, '0');
      const index = dates.get(key);
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'calendar-day';
      button.textContent = date;
      button.tabIndex = -1;
      if (index === undefined) {
        button.disabled = true;
        button.setAttribute('aria-label', fullDate.format(utcDate(key)) + ' · outside the snapshot');
      } else {
        const day = days[index];
        button.dataset.calendarIndex = index;
        button.dataset.level = day.level ?? Number(day.count > 0);
        button.setAttribute('aria-label', describe(day));
        button.setAttribute('aria-pressed', 'false');
        if (day.count) {
          const count = document.createElement('span');
          count.className = 'calendar-count';
          count.textContent = number.format(day.count);
          button.append(count);
        }
      }
      elements.push(button);
    }
    grid.replaceChildren(...elements);
    heading.textContent = monthLabel.format(utcDate(month + '-01'));
    summary.textContent = number.format(monthCount) + (monthCount === 1 ? ' contribution' : ' contributions') +
      ' · ' + active + (active === 1 ? ' active day' : ' active days');
    previous.disabled = month === monthKeys[0];
    next.disabled = month === monthKeys.at(-1);
    displayedMonth = month;
  }

  function select(index, focus = false) {
    selected = Math.min(Math.max(index, 0), days.length - 1);
    const day = days[selected];
    const month = day.date.slice(0, 7);
    if (month !== displayedMonth) renderMonth(month);
    const old = grid.querySelector('[aria-pressed="true"]');
    const button = grid.querySelector('[data-calendar-index="' + selected + '"]');
    if (old && old !== button) {
      old.setAttribute('aria-pressed', 'false');
      old.tabIndex = -1;
    }
    button.setAttribute('aria-pressed', 'true');
    button.tabIndex = 0;
    output.textContent = describe(day);
    if (focus) button.focus({ preventScroll: true });
  }

  function moveMonth(direction, focus = false) {
    const target = monthKeys[monthKeys.indexOf(displayedMonth) + direction];
    if (!target) return;
    const date = Number(days[selected].date.slice(8));
    const candidate = months.get(target).find((index) => Number(days[index].date.slice(8)) >= date);
    select(candidate ?? months.get(target).at(-1), focus);
  }

  previous.addEventListener('click', () => moveMonth(-1));
  next.addEventListener('click', () => moveMonth(1));
  grid.addEventListener('click', (event) => {
    const button = event.target.closest('[data-calendar-index]');
    if (button) select(Number(button.dataset.calendarIndex), true);
  });
  grid.addEventListener('keydown', (event) => {
    if (event.altKey || event.ctrlKey || event.metaKey) return;
    const moves = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 };
    const weekday = (utcDate(days[selected].date).getUTCDay() + 6) % 7;
    if (event.key in moves) select(selected + moves[event.key], true);
    else if (event.key === 'Home') select(selected - weekday, true);
    else if (event.key === 'End') select(selected + 6 - weekday, true);
    else if (event.key === 'PageUp') moveMonth(-1, true);
    else if (event.key === 'PageDown') moveMonth(1, true);
    else return;
    event.preventDefault();
  });
  select(selected);
}
