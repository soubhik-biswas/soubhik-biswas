const number = new Intl.NumberFormat('en');
const compactNumber = new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 });
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

export function commitMetrics(snapshot, date) {
  if (!snapshot?.days || typeof snapshot.from !== 'string' || typeof snapshot.to !== 'string' ||
    date < snapshot.from || date > snapshot.to) return null;
  const row = snapshot.days[date];
  if (row === undefined) return { commits: 0, additions: 0, deletions: 0 };
  if (!row || ![row.commits, row.additions, row.deletions].every((value) => Number.isSafeInteger(value) && value >= 0)) {
    return null;
  }
  return row;
}

export function mountActivityCalendar(days, commitRequest) {
  const grid = document.getElementById('calendar-grid');
  const previous = document.getElementById('calendar-prev');
  const next = document.getElementById('calendar-next');
  const heading = document.getElementById('calendar-month');
  const summary = document.getElementById('calendar-month-total');
  const output = document.getElementById('calendar-point');
  const peak = document.getElementById('calendar-peak');
  const commitScope = document.getElementById('calendar-commit-scope');
  const commitValues = ['commits', 'additions', 'deletions'].map((metric) =>
    [metric, document.getElementById('calendar-' + metric)]);
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
  let commitSnapshot;

  function describe(day) {
    return fullDate.format(utcDate(day.date)) + ' · ' + number.format(day.count) +
      (day.count === 1 ? ' contribution' : ' contributions');
  }

  function renderMonth(month) {
    const records = months.get(month).map((index) => days[index]);
    const monthCount = records.reduce((sum, day) => sum + day.count, 0);
    const active = records.filter((day) => day.count > 0).length;
    const busiestDay = Math.max(1, ...records.map(({ count }) => count));
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
        const contribution = document.createElement('span');
        contribution.className = 'calendar-contributions';
        contribution.setAttribute('aria-hidden', 'true');
        const count = document.createElement('span');
        count.className = 'calendar-count';
        const countFull = document.createElement('span');
        countFull.className = 'calendar-count-full';
        countFull.textContent = number.format(day.count);
        const countShort = document.createElement('span');
        countShort.className = 'calendar-count-short';
        countShort.textContent = compactNumber.format(day.count);
        count.append(countFull, countShort);
        const label = document.createElement('span');
        label.className = 'calendar-label';
        const labelFull = document.createElement('span');
        labelFull.className = 'calendar-label-full';
        labelFull.textContent = day.count === 1 ? 'Contribution' : 'Contributions';
        const labelShort = document.createElement('span');
        labelShort.className = 'calendar-label-short';
        labelShort.textContent = 'Contrib.';
        label.append(labelFull, labelShort);
        contribution.append(count, label);
        const meter = document.createElement('span');
        meter.className = 'calendar-meter';
        meter.setAttribute('aria-hidden', 'true');
        const fill = document.createElement('span');
        fill.style.width = (day.count / busiestDay) * 100 + '%';
        fill.toggleAttribute('data-positive', day.count > 0);
        meter.append(fill);
        button.append(contribution, meter);
      }
      const dateNumber = document.createElement('span');
      dateNumber.className = 'calendar-date';
      dateNumber.textContent = date;
      dateNumber.setAttribute('aria-hidden', 'true');
      button.append(dateNumber);
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

  function updateCommits() {
    const row = commitMetrics(commitSnapshot, days[selected].date);
    for (const [metric, node] of commitValues) node.textContent = row ? number.format(row[metric]) : '—';
    const scope = 'Commits attributed to Soubhik Biswas on default branches of his public repositories. Dates use UTC.';
    commitScope.textContent = scope + (commitSnapshot === undefined
      ? ' Loading commit data…'
      : row ? '' : ' Commit data unavailable for this date.');
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
    updateCommits();
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
  Promise.resolve(commitRequest).then((snapshot) => {
    commitSnapshot = snapshot ?? null;
    updateCommits();
  });
}
