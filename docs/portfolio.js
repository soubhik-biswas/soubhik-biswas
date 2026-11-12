import { mountActivityCalendar } from './activity-calendar.js?v=activity-detail';
import { renderRepositoryStats } from './repository-stats.js?v=activity-detail';

const byId = (id) => document.getElementById(id);
const number = new Intl.NumberFormat('en');
const percent = new Intl.NumberFormat('en', { style: 'percent', maximumFractionDigits: 1 });
const shortDate = new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', timeZone: 'UTC' });
const fullDate = new Intl.DateTimeFormat('en', {
  month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC',
});
const ranges = [...document.querySelectorAll('[data-days]')];
const liveSnapshot = 'https://raw.githubusercontent.com/soubhik-biswas/soubhik-biswas/main/assets/public-data.json';

function element(tag, content, className) {
  const node = document.createElement(tag);
  if (content !== undefined) node.textContent = content;
  if (className) node.className = className;
  return node;
}

function formatDate(value, formatter = fullDate) {
  return formatter.format(new Date(value + 'T00:00:00Z'));
}

function dateRange(first, last) {
  if (first === last) return formatDate(last);
  const formatter = first.slice(0, 4) === last.slice(0, 4) ? shortDate : fullDate;
  return formatDate(first, formatter) + ' – ' + formatDate(last);
}

function getTotals(days) {
  return days.reduce((total, day) => ({
    count: total.count + day.count,
    active: total.active + Number(day.count > 0),
  }), { count: 0, active: 0 });
}

function makeBuckets(days, previous, step) {
  const buckets = [];
  let start = 0;
  while (start < days.length) {
    const end = start + ((days.length - start) % step || step);
    buckets.push({
      start: days[start].date,
      end: days[end - 1].date,
      ...getTotals(days.slice(start, end)),
      previous: previous ? {
        start: previous[start].date,
        end: previous[end - 1].date,
        ...getTotals(previous.slice(start, end)),
      } : null,
    });
    start = end;
  }
  return buckets;
}

async function getJSON(url) {
  const response = await fetch(url, { signal: AbortSignal.timeout?.(8000) });
  if (!response.ok) throw new Error('Snapshot request failed');
  return response.json();
}

function checkSnapshot(snapshot) {
  if (!Array.isArray(snapshot.days) || !snapshot.days.length || !Array.isArray(snapshot.repos)
    || !snapshot.languages || !snapshot.days.every(({ date, count }) =>
      /^\d{4}-\d{2}-\d{2}$/.test(date) && Number.isInteger(count) && count >= 0)) {
    throw new Error('Unexpected snapshot format');
  }
  return snapshot;
}

async function getSnapshot() {
  if (location.hostname === 'soubhik-biswas.github.io') {
    try {
      return { data: checkSnapshot(await getJSON(liveSnapshot)), fallback: false };
    } catch {
      return { data: checkSnapshot(await getJSON('./snapshot.json')), fallback: true };
    }
  }
  return { data: checkSnapshot(await getJSON('./snapshot.json')), fallback: false };
}

async function getCommitActivity() {
  if (location.hostname === 'soubhik-biswas.github.io') {
    try {
      const latest = await getJSON(new URL('commit-activity.json', liveSnapshot));
      if (latest?.days && latest.from && latest.to) return latest;
    } catch {
      // The deployed snapshot remains available if the live request fails.
    }
  }
  return getJSON('./commit-activity.json').catch(() => null);
}

function showProjects(projects) {
  byId('project-list').replaceChildren(...projects.map((project) => {
    const article = element('article', undefined, 'project');
    const heading = element('h3');
    const link = element('a', project.name + ' ↗');
    link.href = project.url;
    heading.append(link);
    article.append(heading, element('p', project.summary), element('p', project.detail));
    return article;
  }));
}

function mountActivity(data) {
  const compare = byId('compare');
  const plot = byId('plot');
  const previousButton = byId('point-prev');
  const nextButton = byId('point-next');
  const pointDate = byId('point-date');
  const pointValue = byId('point-value');
  const pointComparison = byId('point-comparison');
  let length = 90;
  let buckets = [];
  let columns = [];
  let selection = -1;
  let wantsComparison = compare.checked;

  function inspect(index) {
    index = Math.min(Math.max(index, 0), buckets.length - 1);
    if (selection === index) return;
    const bucket = buckets[index];
    if (columns[selection]) columns[selection].dataset.selected = 'false';
    columns[index].dataset.selected = 'true';
    selection = index;
    previousButton.setAttribute('aria-disabled', index === 0);
    nextButton.setAttribute('aria-disabled', index === buckets.length - 1);
    pointDate.textContent = dateRange(bucket.start, bucket.end);
    pointValue.textContent = number.format(bucket.count) + (bucket.count === 1 ? ' contribution' : ' contributions') +
      ' · ' + bucket.active + (bucket.active === 1 ? ' active day' : ' active days');
    pointComparison.hidden = !bucket.previous;
    pointComparison.textContent = bucket.previous
      ? 'Previous period · ' + dateRange(bucket.previous.start, bucket.previous.end) + ' · ' +
        number.format(bucket.previous.count) + (bucket.previous.count === 1 ? ' contribution' : ' contributions')
      : '';
  }

  function render() {
    const days = data.days.slice(-(length || data.days.length));
    const start = data.days.length - days.length;
    const prior = start >= days.length ? data.days.slice(start - days.length, start) : null;
    const previous = wantsComparison ? prior : null;
    compare.disabled = !prior;
    compare.checked = Boolean(previous);
    byId('previous-key').hidden = !previous;
    byId('previous-column').hidden = !previous;
    for (const button of ranges) {
      button.setAttribute('aria-pressed', Number(button.dataset.days) === length);
    }

    const totals = getTotals(days);
    const peak = days.reduce((best, day) => day.count > best.count ? day : best, days[0]);
    const diff = previous ? totals.count - getTotals(previous).count : 0;
    byId('total').textContent = number.format(totals.count);
    byId('delta').textContent = previous
      ? (diff > 0 ? '+' : '') + number.format(diff) + ' vs. previous'
      : 'In this period';
    byId('active').textContent = number.format(totals.active);
    byId('active-note').textContent = 'of ' + days.length + ' days';
    byId('peak').textContent = number.format(peak.count);
    byId('peak-note').textContent = peak.count ? formatDate(peak.date) : 'No activity';

    const step = days.length <= 31 ? 1 : days.length <= 182 ? 7 : 28;
    const grouping = { 1: 'day', 7: 'week', 28: 'four-week block' }[step];
    byId('interval').textContent = grouping;
    buckets = makeBuckets(days, previous, step);
    const max = Math.max(2, ...buckets.map(({ count, previous }) => Math.max(count, previous?.count ?? 0)));
    const rounding = 10 ** Math.floor(Math.log10(max));
    const top = Math.ceil(max / rounding) * rounding;
    byId('scale').replaceChildren(...[top, top / 2, 0].map((tick) => element('span', number.format(tick))));

    plot.style.gridTemplateColumns = 'repeat(' + buckets.length + ', minmax(0, 1fr))';
    columns = buckets.map((bucket, index) => {
      const column = element('div', undefined, 'bucket');
      const bar = element('div', undefined, 'bar current');
      bar.style.height = (bucket.count / top) * 100 + '%';
      column.append(bar);
      if (bucket.previous) {
        const priorBar = element('div', undefined, 'bar previous');
        priorBar.style.height = (bucket.previous.count / top) * 100 + '%';
        column.append(priorBar);
      }
      column.addEventListener('pointerenter', () => inspect(index));
      column.addEventListener('click', () => inspect(index));
      return column;
    });
    plot.replaceChildren(...columns);

    const positions = [...new Set([0, Math.floor((days.length - 1) / 2), days.length - 1])];
    byId('time-labels').replaceChildren(...positions.map((position) =>
      element('span', formatDate(days[position].date, shortDate))));
    byId('rows').replaceChildren(...buckets.map((bucket) => {
      const row = element('tr');
      const heading = element('th', dateRange(bucket.start, bucket.end));
      heading.scope = 'row';
      row.append(heading, element('td', number.format(bucket.count)), element('td', number.format(bucket.active)));
      if (bucket.previous) row.append(element('td', number.format(bucket.previous.count)));
      return row;
    }));

    const currentRange = dateRange(days[0].date, days.at(-1).date);
    const previousRange = previous
      ? ' Previous period: ' + dateRange(previous[0].date, previous.at(-1).date) + '.'
      : prior ? '' : ' The snapshot has no earlier window of the same length.';
    byId('period-note').textContent = currentRange + ' · Counts grouped by ' + grouping + '.' + previousRange;
    const target = selection < 0 ? buckets.length - 1 : Math.min(selection, buckets.length - 1);
    selection = -1;
    inspect(target);
  }

  previousButton.addEventListener('click', () => inspect(selection - 1));
  nextButton.addEventListener('click', () => inspect(selection + 1));
  byId('point-controls').addEventListener('keydown', (event) => {
    if (event.altKey || event.ctrlKey || event.metaKey) return;
    if (event.key === 'ArrowLeft') inspect(selection - 1);
    else if (event.key === 'ArrowRight') inspect(selection + 1);
    else if (event.key === 'Home') inspect(0);
    else if (event.key === 'End') inspect(buckets.length - 1);
    else return;
    event.preventDefault();
  });
  compare.addEventListener('change', () => {
    wantsComparison = compare.checked;
    render();
  });
  for (const button of ranges) {
    button.addEventListener('click', () => {
      length = Number(button.dataset.days);
      selection = -1;
      render();
    });
  }
  render();
}

function shares(breakdown) {
  const entries = Object.entries(breakdown ?? {});
  const total = entries.reduce((sum, [, count]) => sum + count, 0);
  return new Map(total ? entries.map(([name, count]) => [name, count / total]) : []);
}

function mountLanguages(data, projects) {
  const selector = byId('repository');
  const portfolio = shares(data.languages);
  const available = projects.flatMap(({ slug, name }) => {
    const repository = data.repos.find((repo) => repo.name === slug);
    const composition = shares(repository?.languages);
    return composition.size ? [{ slug, name, composition }] : [];
  });
  selector.replaceChildren(new Option('Portfolio only', ''), ...available.map(({ name, slug }) => new Option(name, slug)));
  selector.value = available[0]?.slug ?? '';
  const key = document.querySelector('.language-key');
  const selectedKey = key.firstElementChild;

  function render() {
    const active = available.find(({ slug }) => slug === selector.value);
    selectedKey.hidden = !active;
    if (active) selectedKey.replaceChildren(element('i', undefined, 'key-current'), active.name);
    const names = [...new Set([...portfolio.keys(), ...(active?.composition.keys() ?? [])])];
    const rows = names.map((name) => ({
      name,
      overall: portfolio.get(name) ?? 0,
      selected: active?.composition.get(name) ?? 0,
    })).sort((a, b) => Math.max(b.overall, b.selected) - Math.max(a.overall, a.selected));
    const shown = rows.slice(0, 8);
    if (rows.length > shown.length) {
      shown.push(rows.slice(shown.length).reduce((other, row) => ({
        name: 'Other',
        overall: other.overall + row.overall,
        selected: other.selected + row.selected,
      }), { overall: 0, selected: 0 }));
    }
    byId('language-chart').replaceChildren(...shown.map(({ name, overall, selected }) => {
      const row = element('div', undefined, 'language-row');
      const bars = element('div', undefined, 'language-bars');
      const values = element('div', undefined, 'language-values');
      const series = active ? [[selected, 'key-current'], [overall, 'key-previous']] : [[overall, 'key-previous']];
      for (const [share, className] of series) {
        const track = element('div', undefined, 'language-track');
        const label = className === 'key-current' ? active.name : 'Public portfolio';
        track.title = label + ' · ' + percent.format(share);
        const bar = element('div', undefined, className);
        bar.style.width = share * 100 + '%';
        track.append(bar);
        bars.append(track);
      }
      bars.setAttribute('aria-hidden', 'true');
      if (active) values.append(element('strong', percent.format(selected)), ' / ');
      values.append(percent.format(overall));
      values.setAttribute('aria-label', (active ? active.name + ': ' + percent.format(selected) + '. ' : '') +
        'Public portfolio: ' + percent.format(overall));
      row.append(element('h3', name), bars, values);
      return row;
    }));
    if (!shown.length) byId('language-chart').append(element('p', 'No language data in this snapshot.', 'muted'));
  }

  selector.addEventListener('change', render);
  render();
}

const projectsRequest = getJSON('./projects.json').then((projects) => {
  showProjects(projects);
  return projects;
}).catch(() => {
  byId('project-list').textContent = 'Project details could not be loaded. See the GitHub profile.';
  return [];
});

try {
  const [{ data, fallback }, projects] = await Promise.all([getSnapshot(), projectsRequest]);
  mountActivity(data);
  mountActivityCalendar(data.days, getCommitActivity());
  mountLanguages(data, projects);
  renderRepositoryStats(data);
  const through = formatDate(data.days.at(-1).date);
  byId('snapshot').textContent = (fallback ? 'Saved snapshot through ' : 'GitHub data through ') + through;
  byId('data-status').hidden = true;
  document.querySelectorAll('[data-needs-data]').forEach((node) => { node.hidden = false; });
  if (location.hash === '#calendar') {
    requestAnimationFrame(() => byId('calendar').scrollIntoView({ block: 'start', behavior: 'instant' }));
  }
} catch {
  byId('snapshot').textContent = 'Snapshot unavailable';
  const status = byId('data-status');
  status.textContent = 'Could not load the public snapshot. ';
  const link = element('a', 'View contributions on GitHub');
  link.href = 'https://github.com/soubhik-biswas#contribution-trends';
  status.append(link);
}
