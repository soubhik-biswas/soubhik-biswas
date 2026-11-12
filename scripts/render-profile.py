"""Build the animated profile panels and README data sections from public data."""
import base64
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
from datetime import date
from html import escape
from itertools import count, groupby
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANELS = ROOT / 'panels'
RAW_ROOT = 'https://raw.githubusercontent.com/soubhik-biswas/soubhik-biswas/main/panels/'
PROFILE = json.loads((ROOT / 'profile.json').read_text())
DATA = json.loads((ROOT / 'assets/public-data.json').read_text())
COMMIT_ACTIVITY = json.loads((ROOT / 'assets/commit-activity.json').read_text())
PROJECTS = json.loads((ROOT / 'assets/projects.json').read_text())
METRICS = json.loads((ROOT / 'assets/fonts/metrics.json').read_text())

GROUND, RAISED, RAISED_2, LINE = '#17162e', '#211f42', '#2b2853', '#3b3763'
INK, MUTED, DIM = '#f7f5ff', '#b9b5d8', '#8a86ad'
CITRON, PINK, VIOLET, AMBER, SKY = '#d8f36b', '#ff8fc7', '#8f88ff', '#ffb86b', '#56c7ec'
SERIES = (CITRON, PINK, VIOLET, AMBER, SKY)
OTHER = DIM
WEEKDAYS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
PAD, COLUMN = 32, 436
_ids = count(1)


# ── drawing toolkit ──────────────────────────────────────────────────────────

def inline(path, mime):
    return f'data:{mime};base64,' + base64.b64encode((ROOT / path).read_bytes()).decode()


def tw(value, size, weight=500, mono=False):
    """Rendered width of a string, from the stored advance widths."""
    value = str(value)
    if mono:
        return len(value) * METRICS['mono'] * size / 1000
    table = METRICS['display'][str(weight)]
    return sum(table.get(character, 600) for character in value) * size / 1000


def text(x, y, value, size=16, fill=INK, weight=500, anchor='start', mono=False, spacing=0, extra=''):
    attributes = f'x="{x:g}" y="{y:g}" font-size="{size:g}" fill="{fill}"'
    attributes += ' class="m"' if mono else f' font-weight="{weight}"'
    if anchor != 'start':
        attributes += f' text-anchor="{anchor}"'
    if spacing:
        attributes += f' letter-spacing="{spacing:g}"'
    return f'<text {attributes} {extra}>{escape(str(value))}</text>'


def rect(x, y, w, h, fill=RAISED, stroke='none', radius=0, extra=''):
    return (f'<rect x="{x:g}" y="{y:g}" width="{max(0, w):g}" height="{max(0, h):g}" rx="{radius:g}" '
            f'fill="{fill}" stroke="{stroke}" {extra}/>')


def group(x, y, content):
    return f'<g transform="translate({x:g} {y:g})">{content}</g>'


def anim(content, name, delay=0.0, extra=''):
    """Wrap content in an animated group. Base styles are always the end state."""
    return f'<g class="{name}" style="animation-delay:{delay:.2f}s" {extra}>{content}</g>'


def tip(content, label):
    """A mark with its exact value. Hovering shows it when the panel is opened on its own."""
    return f'<g class="mark"><title>{escape(label)}</title>{content}</g>'


def icon(name, x, y, size=24, color=CITRON):
    root = ET.fromstring((ROOT / f'assets/icons/{name}.svg').read_text())
    paths = ''.join(f'<path d="{p.attrib["d"]}"/>' for p in root.iter() if p.tag.endswith('path'))
    return f'<g transform="translate({x:g} {y:g}) scale({size / 24:g})" fill="{color}">{paths}</g>'


def arrow(x, y, color=CITRON, size=1.0):
    return (f'<path transform="translate({x:g} {y:g}) scale({size:g})" d="M-5 5L5 -5M-2.5 -5H5V2.5" fill="none" '
            f'stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>')


def chip(x, y, label, size=12, fill=RAISED_2, color=MUTED, stroke=LINE):
    width = tw(label, size, 500) + 18
    height = size + 12
    return rect(x, y, width, height, fill, stroke, height / 2) + text(x + 9, y + height / 2 + size * .35, label, size, color, 500), width


def wrap(value, size, weight, limit):
    lines, current = [], ''
    for word in value.split():
        attempt = f'{current} {word}'.strip()
        if current and tw(attempt, size, weight) > limit:
            lines.append(current)
            current = word
        else:
            current = attempt
    return lines + [current] if current else lines


def odometer(x, y, value, size, fill=INK, weight=700, delay=0.0):
    """A number whose digits roll into place. Reduced motion shows the final digits."""
    value = str(value)
    cell = size * .66
    widths = [cell if character.isdigit() else tw(character, size, weight) for character in value]
    row = size * 1.2
    clip = f'c{next(_ids)}'
    body = f'<clipPath id="{clip}"><rect x="{x - 2:g}" y="{y - size * .9:g}" width="{sum(widths) + 4:g}" height="{size * 1.12:g}"/></clipPath>'
    body += f'<g clip-path="url(#{clip})" data-value="{escape(value)}">'
    cursor = x
    for index, (character, width) in enumerate(zip(value, widths)):
        if character.isdigit():
            strip = list(range(10)) + list(range(int(character) + 1))
            digits = ''.join(text(cursor + width / 2, y + step * row, digit, size, fill, weight, 'middle')
                             for step, digit in enumerate(strip))
            shift = (len(strip) - 1) * row
            body += (f'<g class="roll" style="transform:translateY(-{shift:g}px);'
                     f'animation-delay:{delay + index * .09:.2f}s">{digits}</g>')
        else:
            body += text(cursor, y, character, size, fill, weight)
        cursor += width
    return body + '</g>', sum(widths)


def short_date(value):
    day = date.fromisoformat(value) if isinstance(value, str) else value
    return f'{day:%b} {day.day}'


def long_date(value):
    day = date.fromisoformat(value) if isinstance(value, str) else value
    return f'{day:%b} {day.day}, {day.year}'


def compact(value):
    if value >= 1_000_000:
        return f'{value / 1_000_000:.2f}M'
    if value >= 10_000:
        return f'{value / 1000:.0f}k'
    if value >= 1000:
        return f'{value / 1000:.1f}k'
    return f'{value:,}'


def nice_ceiling(peak, ticks=4):
    """Smallest round axis maximum at or above the peak, and its tick step."""
    if peak <= 0:
        return 1, 1
    raw = peak / ticks
    magnitude = 10 ** math.floor(math.log10(raw))
    step = next(m * magnitude for m in (1, 2, 2.5, 5, 10) if m * magnitude >= raw)
    step = max(1, int(step)) if step >= 1 else step
    return math.ceil(peak / step) * step, step


CSS = '''
text{font-family:Display,"Space Grotesk",system-ui,-apple-system,"Segoe UI",Helvetica,Arial,sans-serif}.m{font-family:Mono,"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-weight:500}
.in{animation:in .8s cubic-bezier(.2,.8,.2,1) both}
.fade{animation:fade .9s ease both}
.gy{transform-box:fill-box;transform-origin:50% 100%;animation:gy .9s cubic-bezier(.2,.8,.2,1) both}
.gd{transform-box:fill-box;transform-origin:50% 0;animation:gy .9s cubic-bezier(.2,.8,.2,1) both}
.gx{transform-box:fill-box;transform-origin:0 50%;animation:gx 1s cubic-bezier(.2,.8,.2,1) both}
.pop{transform-box:fill-box;transform-origin:50% 50%;animation:pop .55s cubic-bezier(.3,1.5,.5,1) both}
.draw{stroke-dasharray:1;animation:draw 1.8s cubic-bezier(.5,0,.2,1) both}
.redraw{stroke-dasharray:1;animation:redraw 12s cubic-bezier(.5,0,.2,1) infinite backwards}
.roll{animation:roll 1.7s cubic-bezier(.2,.8,.2,1) both}
.pulse{animation:pulse 2.4s ease-in-out infinite}
.ping{transform-box:fill-box;transform-origin:50% 50%;animation:ping 2.4s ease-out infinite}
.glint{animation:glint 8s ease-in-out infinite}
.breathe{transform-box:fill-box;transform-origin:50% 50%;animation:breathe 7s ease-in-out infinite}
.march{animation:march 1.4s linear infinite}
.nudge{animation:nudge 2.6s ease-in-out infinite}
.mark:hover{filter:brightness(1.35)}
@keyframes in{from{opacity:0;transform:translateY(12px)}}
@keyframes fade{from{opacity:0}}
@keyframes gy{from{transform:scaleY(0)}}
@keyframes gx{from{transform:scaleX(0)}}
@keyframes pop{from{opacity:0;transform:scale(0)}}
@keyframes draw{from{stroke-dashoffset:1}}
@keyframes redraw{0%{stroke-dashoffset:1}16%,100%{stroke-dashoffset:0}}
@keyframes roll{from{transform:translateY(0)}}
@keyframes pulse{50%{opacity:.35}}
@keyframes ping{from{opacity:.75;transform:scale(1)}to{opacity:0;transform:scale(2.8)}}
@keyframes glint{0%,9%,100%{opacity:1}4.5%{opacity:.55}}
@keyframes breathe{0%,12%,100%{transform:scale(1)}6%{transform:scale(1.25)}}
@keyframes march{to{stroke-dashoffset:-24}}
@keyframes nudge{50%{transform:translate(3px,-3px)}}
@media(prefers-reduced-motion:reduce){*{animation:none!important}.motion{display:none}}
'''


def panel(name, width, height, title, description, body, css=''):
    faces = (f"@font-face{{font-family:Display;src:url({inline('assets/fonts/space-grotesk.woff2', 'font/woff2')}) "
             f"format('woff2');font-weight:300 700}}"
             f"@font-face{{font-family:Mono;src:url({inline('assets/fonts/jetbrains-mono.woff2', 'font/woff2')}) "
             f"format('woff2');font-weight:500}}")
    result = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height:g}" viewBox="0 0 {width} {height:g}" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>
<defs><linearGradient id="edge" x2="1" y2="1"><stop stop-color="{CITRON}" stop-opacity=".55"/><stop offset=".45" stop-color="{VIOLET}" stop-opacity=".3"/><stop offset="1" stop-color="{PINK}" stop-opacity=".45"/></linearGradient>
<radialGradient id="glow"><stop stop-color="{VIOLET}" stop-opacity=".2"/><stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/></radialGradient>
 <linearGradient id="wash" x2="0" y2="1"><stop stop-color="{PINK}" stop-opacity=".28"/><stop offset="1" stop-color="{PINK}" stop-opacity="0"/></linearGradient>
<pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r=".8" fill="#7972a3" opacity=".22"/></pattern>
<clipPath id="frame"><rect x="1" y="1" width="{width - 2}" height="{height - 2:g}" rx="24"/></clipPath></defs>
<style>{faces}{CSS}{css}</style>
{rect(1, 1, width - 2, height - 2, GROUND, 'url(#edge)', 24)}
<g clip-path="url(#frame)"><rect width="{width}" height="{height:g}" fill="url(#dots)"/><circle cx="0" cy="0" r="{width * .46:g}" fill="url(#glow)"/>{body}</g></svg>'''
    ET.fromstring(result)
    PANELS.mkdir(exist_ok=True)
    (PANELS / name).write_text(result + '\n')


def heading(title, note, width):
    """Panel title on the left; on wide panels the note sits on the same line, right aligned."""
    body = text(PAD, 60, title, 28, INK, 700, spacing=-.6)
    if width >= 1000:
        return body + text(width - PAD, 60, note, 13, MUTED, 400, 'end'), 84
    return body + text(PAD, 84, note, 13, MUTED, 400), 106


def block_title(title, note):
    return text(0, 20, title, 19, INK, 600, spacing=-.2) + text(0, 43, note, 13, MUTED, 400)


# ── derived metrics ──────────────────────────────────────────────────────────

def activity_metrics():
    days = DATA['days']
    counts = [day['count'] for day in days]
    longest = run = 0
    for value in counts:
        run = run + 1 if value else 0
        longest = max(longest, run)
    recent = counts[-91:]
    weekdays = [0] * 7
    for day in days[-91:]:
        if day['count']:
            weekdays[date.fromisoformat(day['date']).weekday()] += 1
    return {
        'active': sum(value > 0 for value in counts),
        'longest': longest,
        'last30': sum(counts[-30:]),
        'previous30': sum(counts[-60:-30]),
        'active30': sum(value > 0 for value in counts[-30:]),
        'previous_active30': sum(value > 0 for value in counts[-60:-30]),
        'weeks': [sum(recent[i:i + 7]) for i in range(0, len(recent), 7)],
        'weekdays': weekdays,
    }


def rolling_average(counts, window=7):
    """Trailing mean for each of the last 91 days, using earlier days where they exist."""
    start = len(counts) - min(91, len(counts))
    return [sum(counts[max(0, i - window + 1):i + 1]) / window for i in range(start, len(counts))]


def momentum(current, previous):
    """Plain-language comparison of two periods. No ratio is claimed from a zero base."""
    if not previous:
        return ('New', 'activity; the previous 30 days had none') if current else ('0', 'contributions in either period')
    ratio = current / previous
    label = f'{ratio:.1f}×' if ratio < 10 else f'{ratio:.0f}×'
    return label, 'the previous 30 days'


def commit_totals():
    days = COMMIT_ACTIVITY['days'].values()
    return {key: sum(day[key] for day in days) for key in ('commits', 'additions', 'deletions')}


def weekly_commits():
    days = DATA['days'][-91:]
    weeks = []
    for index in range(0, len(days), 7):
        chunk = [COMMIT_ACTIVITY['days'].get(day['date'], {}) for day in days[index:index + 7]]
        weeks.append({'start': days[index]['date'], 'end': days[min(index + 6, len(days) - 1)]['date'],
                      **{key: sum(day.get(key, 0) for day in chunk) for key in ('commits', 'additions', 'deletions')}})
    return weeks


def language_categories():
    ranked = sorted(DATA['languages'], key=lambda name: (-DATA['languages'][name], name))
    return [name for name in ranked[:5] if DATA['languages'][name] > 0]


def language_segments(breakdown, categories):
    segments = [(name, breakdown.get(name, 0), SERIES[index]) for index, name in enumerate(categories)]
    other = sum(amount for name, amount in breakdown.items() if name not in categories)
    if other:
        segments.append(('Other', other, OTHER))
    return [(name, amount, color) for name, amount, color in segments if amount]


def squarify(items, x, y, w, h):
    """Squarified treemap. items: (key, value) sorted descending, values above zero."""
    total = sum(value for _, value in items)
    if not total or w <= 0 or h <= 0:
        return []
    scale = w * h / total
    areas = [(key, value * scale) for key, value in items]
    placed = []

    def worst(row, side):
        s = sum(area for _, area in row)
        return max(max(side * side * area / (s * s), s * s / (side * side * area)) for _, area in row)

    while areas:
        side = min(w, h)
        row = [areas.pop(0)]
        while areas and worst(row + [areas[0]], side) <= worst(row, side):
            row.append(areas.pop(0))
        s = sum(area for _, area in row)
        thickness = s / side
        offset = 0
        for key, area in row:
            length = area / thickness
            if w >= h:
                placed.append((key, x, y + offset, thickness, length))
            else:
                placed.append((key, x + offset, y, length, thickness))
            offset += length
        if w >= h:
            x, w = x + thickness, w - thickness
        else:
            y, h = y + thickness, h - thickness
    return placed


# ── hero ─────────────────────────────────────────────────────────────────────

def inspector(width):
    metrics = activity_metrics()
    days = DATA['days'][-91:]
    body = rect(0, 0, width, 300, RAISED, LINE, 16)
    body += text(22, 33, 'Inspect', 14, INK, 600) + text(width - 22, 33, 'Profile', 11, DIM, anchor='end', mono=True)
    body += f'<path d="M0 50H{width}" stroke="{LINE}"/>'
    rows = (('Team', PROFILE['company']), ('Focus', 'Design systems, product UI'),
            ('Based', PROFILE['home']), ('GitHub', f'Since {DATA["account"]["created_at"][:4]}'))
    for index, (label, value) in enumerate(rows):
        y = 79 + index * 27
        body += anim(text(22, y, label, 13, DIM, 400) + text(92, y, value, 13, INK, 500), 'in', 1.2 + index * .09)
    y = 79 + len(rows) * 27
    chips, x = text(22, y, 'Stack', 13, DIM, 400), 92
    for index, label in enumerate(('React', 'Next.js', 'TypeScript')):
        drawn, used = chip(x, y - 17, label)
        chips += anim(drawn, 'pop', 1.65 + index * .08)
        x += used + 6
    body += chips + f'<path d="M0 208H{width}" stroke="{LINE}"/>'
    body += text(22, 233, 'Contributions, last 13 weeks', 12, MUTED, 400)
    number, _ = odometer(22, 277, f'{sum(metrics["weeks"]):,}', 36, INK, 700, 1.9)
    body += number
    peak = max(1, max(metrics['weeks']))
    left = width - 22 - 12 * 12 - 8
    for index, value in enumerate(metrics['weeks']):
        x = left + index * 12
        body += rect(x, 280, 8, 2, LINE, 'none', 1)
        if value:
            height = max(2, 52 * value / peak)
            latest = index == len(metrics['weeks']) - 1
            label = f'{short_date(days[index * 7]["date"])} to {short_date(days[min(index * 7 + 6, len(days) - 1)]["date"])}: {value:,} contributions'
            bar = rect(x, 282 - height, 8, height, CITRON if latest else VIOLET, 'none', 2, 'class="weekly-bar"')
            body += tip(anim(bar, 'gy', 2.0 + index * .05), label)
            if latest:
                body += f'<circle class="ping motion" cx="{x + 4}" cy="{282 - height:g}" r="4" fill="{CITRON}"/>'
    return body


def hero(mobile=False):
    width = 500 if mobile else 1000
    size = 76 if mobile else 92
    tracking = -.035 * size
    first, last = PROFILE['name'].split(' ', 1)
    left = PAD if mobile else 60
    base_1 = 148 if mobile else 162
    base_2 = base_1 + round(size * .94)
    name_width = max(tw(word, size, 700) + tracking * (len(word) - 1) for word in (first, last))
    box = (left - 12, base_1 - size * .7 - 14, name_width + 26, base_2 - base_1 + size * .7 + 30)
    box_right, box_bottom = box[0] + box[2], box[1] + box[3]
    canvas = width if mobile else 596

    body = text(PAD, 30, PROFILE['username'], 12, DIM, mono=True)
    body += text(PAD + tw(PROFILE['username'], 12, mono=True) + 8, 30, '/ profile', 12, MUTED, mono=True)
    body += text(width - PAD - 82, 30, 'Design', 12, DIM, 500, 'end')
    body += rect(width - PAD - 70, 14, 70, 24, '#d8f36b22', CITRON + '66', 12) + text(width - PAD - 35, 30, 'Inspect', 12, CITRON, 600, 'middle')
    body += f'<path d="M0 46H{width}" stroke="{LINE}"/>'

    guides = ''.join(f'<path d="M0 {y:g}H{canvas}" stroke="{PINK}" stroke-opacity=".4" stroke-dasharray="3 6"/>' for y in (base_1, base_2))
    body += anim(guides, 'fade', .1)
    body += anim(text(left, base_1, first, size, INK, 700, spacing=tracking), 'in', .2)
    body += anim(text(left, base_2, last, size, INK, 700, spacing=tracking), 'in', .34)

    body += f'<rect class="draw" style="animation-delay:1.45s;animation-duration:.9s" pathLength="1" x="{box[0]:g}" y="{box[1]:g}" width="{box[2]:g}" height="{box[3]:g}" fill="none" stroke="{CITRON}" stroke-width="1.5"/>'
    for index, (x, y) in enumerate(((box[0], box[1]), (box_right, box[1]), (box[0], box_bottom), (box_right, box_bottom))):
        body += anim(rect(x - 4, y - 4, 8, 8, GROUND, CITRON, 1.5, 'stroke-width="1.5"'), 'pop', 2.0 + index * .05)
    size_label = f'{round(box[2])} × {round(box[3])}'
    pill = tw(size_label, 11, mono=True) + 14
    centre = box[0] + box[2] / 2
    body += anim(rect(centre - pill / 2, box_bottom + 9, pill, 20, CITRON, 'none', 4)
                 + text(centre, box_bottom + 23, size_label, 11, GROUND, anchor='middle', mono=True), 'pop', 2.2)

    pointer = (f'<path d="M0 0V17L4.6 12.9L7.6 19.6L10.4 18.4L7.5 11.8H13.4Z" fill="{INK}" stroke="{GROUND}" stroke-width="1.2" stroke-linejoin="round"/>'
               + rect(13, 18, tw('You', 12, 600) + 18, 22, VIOLET, 'none', 11) + text(22, 33, 'You', 12, GROUND, 600))
    body += group(box_right + 5, box_bottom + 3, f'<g class="cursor"><g class="idle">{pointer}</g></g>')

    role_y = box_bottom + (62 if mobile else 66)
    body += anim(text(left, role_y, PROFILE['role'], 22 if mobile else 24, CITRON, 600, spacing=-.3), 'in', .7)
    body += anim(text(left, role_y + 29, f'Frontend architecture and design systems at {PROFILE["company"]}', 15 if mobile else 16, MUTED, 400), 'in', .85)

    if mobile:
        card_y = role_y + 60
        body += group(PAD, card_y, anim(inspector(COLUMN), 'fade', .6))
        height = card_y + 300 + PAD
    else:
        body += group(624, 66, anim(inspector(344), 'fade', .6))
        height = max(role_y + 29 + 38, 66 + 300 + 30)

    css = ('.cursor{animation:cursor 1.1s cubic-bezier(.2,.8,.2,1) .5s both}.idle{animation:idle 6s ease-in-out 2.6s infinite}'
           '@keyframes cursor{from{opacity:0;transform:translate(150px,96px)}}@keyframes idle{50%{transform:translate(6px,5px)}}')
    weeks = activity_metrics()['weeks']
    panel('hero-mobile.svg' if mobile else 'hero.svg', width, height,
          f'{PROFILE["name"]}, {PROFILE["role"]}',
          f'{PROFILE["name"]} is a {PROFILE["role"]} at {PROFILE["company"]}, working on frontend architecture and design systems '
          f'with React, Next.js and TypeScript. Based in {PROFILE["home"]}. {sum(weeks):,} publicly visible GitHub contributions '
          f'in the 13 weeks ending {DATA["days"][-1]["date"]}.', body, css)


# ── products ─────────────────────────────────────────────────────────────────

def art_passlore():
    secret = 'kV7#mQ2x!Rt9'
    body = rect(14, 22, 140, 38, GROUND, LINE, 10)
    for index, character in enumerate(secret):
        x = 26 + index * 9.9
        body += f'<circle cx="{x + 3.6:g}" cy="41" r="1.4" fill="{DIM}" opacity=".5"/>'
        body += f'<g class="type" style="animation-delay:{index * .22:.2f}s">{rect(x - 1, 31, 10, 20, GROUND)}{text(x, 46, character, 13, INK, mono=True)}</g>'
    for index in range(4):
        body += rect(14 + index * 36, 74, 32, 6, LINE, 'none', 3)
        body += f'<g class="type" style="animation-delay:{.4 + index * .66:.2f}s">{rect(14 + index * 36, 74, 32, 6, CITRON, "none", 3)}</g>'
    body += text(14, 97, 'Very strong', 11, MUTED, 500)
    return body, '.type{animation:type 7s steps(1) infinite both}@keyframes type{0%{opacity:0}6%,88%{opacity:1}94%,100%{opacity:0}}'


def art_awaketab():
    around = 2 * math.pi * 30
    body = f'<circle cx="52" cy="54" r="30" fill="none" stroke="{LINE}" stroke-width="6"/>'
    body += (f'<circle class="ring" cx="52" cy="54" r="30" fill="none" stroke="{CITRON}" stroke-width="6" stroke-linecap="round" '
             f'stroke-dasharray="{around:.1f}" transform="rotate(-90 52 54)"/>')
    body += text(52, 59, '30:00', 13, INK, anchor='middle', mono=True)
    body += rect(94, 43, 62, 22, GROUND, LINE, 11) + f'<circle class="pulse" cx="105" cy="54" r="3.5" fill="{CITRON}"/>'
    body += text(113, 58, 'Awake', 11, INK, 500)
    return body, f'.ring{{animation:ring 9s linear infinite}}@keyframes ring{{from{{stroke-dashoffset:0}}to{{stroke-dashoffset:{around:.1f}}}}}'


def art_shareroom():
    body = ''
    for x in (12, 96):
        body += rect(x, 22, 60, 64, GROUND, LINE, 8) + f'<path d="M{x} 36H{x + 60}" stroke="{LINE}"/>'
        body += f'<circle cx="{x + 9}" cy="29" r="2" fill="{DIM}"/><circle cx="{x + 16}" cy="29" r="2" fill="{DIM}"/>'
        body += rect(x + 9, 70, 30, 4, LINE, 'none', 2)
    body += f'<path class="march" d="M72 54H96" stroke="{VIOLET}" stroke-width="2" stroke-dasharray="3 5"/>'
    body += rect(105, 44, 42, 20, RAISED_2, 'none', 4, 'opacity=".5"')
    body += f'<g class="pass">{rect(21, 44, 42, 20, CITRON, "none", 4)}<path d="M28 51H50M28 57H42" stroke="{GROUND}" stroke-width="2" stroke-linecap="round"/></g>'
    return body, '.pass{animation:pass 5s cubic-bezier(.6,0,.2,1) infinite}@keyframes pass{0%,18%{transform:translateX(0)}46%,82%{transform:translateX(84px)}100%{transform:translateX(0)}}'


def art_oibuddy():
    body = rect(118, 26, 30, 52, GROUND, LINE, 6) + f'<g class="water">{rect(121, 30, 24, 45, SKY, "none", 4)}</g>'
    cat = f'<path d="M36 52L41 28L56 44Z M84 52L79 28L64 44Z" fill="{AMBER}"/><ellipse cx="60" cy="64" rx="27" ry="24" fill="{AMBER}"/>'
    cat += f'<g class="blink"><ellipse cx="50" cy="60" rx="3" ry="4" fill="{GROUND}"/><ellipse cx="70" cy="60" rx="3" ry="4" fill="{GROUND}"/></g>'
    cat += f'<path d="M57 68L60 71L63 68" fill="none" stroke="{GROUND}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>'
    body += f'<g class="peek">{cat}</g>' + rect(0, 78, 168, 30, RAISED_2) + f'<path d="M0 78H168" stroke="{LINE}"/>'
    return body, ('.peek{animation:peek 6s ease-in-out infinite}.blink{transform-box:fill-box;transform-origin:50% 50%;animation:blink 4s infinite}'
                  '.water{transform-box:fill-box;transform-origin:50% 100%;animation:water 8s ease-in-out infinite alternate}'
                  '@keyframes peek{0%,100%{transform:translateY(10px)}35%,70%{transform:translateY(0)}}'
                  '@keyframes blink{0%,46%,54%,100%{transform:scaleY(1)}50%{transform:scaleY(.1)}}@keyframes water{from{transform:scaleY(.25)}to{transform:scaleY(.95)}}')


def art_prismwink():
    person = f'<circle cx="62" cy="42" r="15" fill="{VIOLET}"/><path d="M32 94C32 72 46 62 62 62S92 72 92 94Z" fill="{VIOLET}"/>'
    body = rect(14, 16, 140, 78, GROUND, LINE, 10) + f'<g clip-path="url(#tile)"><g class="vanish">{person}</g>'
    for index in range(14):
        x, y = 44 + (index * 23) % 44, 30 + (index * 17) % 56
        body += (f'<rect class="dust" style="animation-delay:{index * .04:.2f}s;--x:{26 + (index * 13) % 40}px;--y:{-(8 + (index * 7) % 26)}px" '
                 f'x="{x}" y="{y}" width="3.5" height="3.5" rx="1" fill="{PINK if index % 3 else CITRON}"/>')
    body += '</g>' + f'<circle class="pulse" cx="140" cy="30" r="3.5" fill="{PINK}"/>'
    return body, ('.vanish{animation:vanish 6s ease-in-out infinite}.dust{opacity:0;animation:dust 6s ease-out infinite}'
                  '@keyframes vanish{0%,30%{opacity:1}44%,78%{opacity:0}92%,100%{opacity:1}}'
                  '@keyframes dust{0%,30%{opacity:0;transform:translate(0,0)}36%{opacity:1}62%,100%{opacity:0;transform:translate(var(--x),var(--y))}}')


def art_domscanner():
    blocks = ((16, 38, 62, 54), (86, 38, 66, 24), (86, 68, 66, 24))
    body = rect(16, 16, 136, 14, GROUND, LINE, 5) + f'<circle cx="25" cy="23" r="2.5" fill="{DIM}"/>' + rect(100, 20, 44, 6, LINE, 'none', 3)
    for index, (x, y, w, h) in enumerate(blocks):
        body += rect(x, y, w, h, GROUND, LINE, 6) + rect(x + 8, y + 9, w * .5, 5, DIM, 'none', 2.5)
        if h > 30:
            body += rect(x + 8, y + 21, w - 16, 4, LINE, 'none', 2) + rect(x + 8, y + 30, w - 24, 4, LINE, 'none', 2)
    for index, (x, y, w, h) in enumerate(blocks):
        label = f'{w * 4} × {h * 4}'
        width = tw(label, 9, mono=True) + 10
        pick = rect(x - 4, y - 4, w + 8, h + 8, 'none', PINK, 0, 'stroke-dasharray="3 3" stroke-opacity=".8"')
        pick += rect(x, y, w, h, CITRON + '22', CITRON, 6, 'stroke-width="2"')
        pick += rect(x + w - width, y + h - 15, width, 15, CITRON, 'none', 4) + text(x + w - width / 2, y + h - 4.5, label, 9, GROUND, anchor='middle', mono=True)
        body += f'<g class="pick" style="opacity:{0 if index else 1};animation-delay:-{(6 - index * 2) % 6}s">{pick}</g>'
    return body, '.pick{animation:pick 6s steps(1) infinite}@keyframes pick{0%{opacity:1}33.3%,100%{opacity:0}}'


ART = {'passlore': art_passlore, 'awaketab': art_awaketab, 'shareroom': art_shareroom,
       'domscanner': art_domscanner, 'oibuddy': art_oibuddy, 'prismwink': art_prismwink}


def project_card(project, mobile=False):
    width = 500 if mobile else 1000
    art, css = ART[project['art']]()
    body = f'<clipPath id="tile"><rect width="168" height="108" rx="14"/></clipPath>'
    body += group(20, 20, rect(0, 0, 168, 108, RAISED, LINE, 14) + f'<g clip-path="url(#tile)">{art}</g>')
    x = 212
    body += text(x, 54 if mobile else 52, project['name'], 26, INK, 700, spacing=-.5)
    kind_x, kind_y = (x, 68) if mobile else (x + tw(project['name'], 26, 700) - .5 * len(project['name']) + 12, 34)
    body += chip(kind_x, kind_y, project['kind'], 11, 'none', MUTED)[0]
    button = (f'<circle cx="0" cy="0" r="21" fill="{RAISED}" stroke="{CITRON}" stroke-opacity=".6"/>'
              f'<g class="nudge">{arrow(0, 0)}</g>')
    if mobile:
        lines = wrap(project['summary'], 15, 400, width - 2 * PAD - 8)
        y = 162
        for line in lines:
            body += text(24, y, line, 15, MUTED, 400)
            y += 22
        chips_y = y - 4
        cursor = 24
        for label in project['stack']:
            drawn, used = chip(cursor, chips_y, label, 11)
            body += drawn
            cursor += used + 6
        footer = chips_y + (44 if project['stack'] else 12)
        body += text(24, footer + 5, project['link'], 13, INK, 600)
        body += group(width - 46, footer, button)
        height = footer + 44
    else:
        limit = 560
        lines = wrap(project['summary'], 15, 400, limit)[:2]
        for index, line in enumerate(lines):
            body += text(x, 78 + index * 21, line, 15, MUTED, 400)
        cursor, chips_y = x, 78 + len(lines) * 21 - 6
        for label in project['stack']:
            drawn, used = chip(cursor, chips_y, label, 11)
            body += drawn
            cursor += used + 6
        body += group(width - 54, 60, button)
        body += text(width - PAD, 116, project['link'], 13, MUTED, 500, 'end')
        height = 148
    name = f'project-{project["art"]}' + ('-mobile' if mobile else '') + '.svg'
    panel(name, width, height, f'{project["name"]}: {project["kind"].lower()}',
          f'{project["summary"]} {project["detail"]}' + (f' Built with {", ".join(project["stack"])}.' if project['stack'] else ''), body, css)


# ── engineering pulse ────────────────────────────────────────────────────────

def kpi_tile(width, label, value, note, delay, suffix=''):
    body = rect(0, 0, width, 100, RAISED, LINE, 14) + text(18, 28, label, 13, MUTED, 400)
    number, used = odometer(18, 68, value, 36, INK, 700, delay)
    body += number
    if suffix:
        body += text(18 + used + 6, 68, suffix, 15, MUTED, 500)
    return body + text(18, 88, note, 12, DIM, 400)


def daily_chart(width):
    """Daily bars for the latest 13 weeks with a trailing seven-day average."""
    days = DATA['days'][-91:]
    counts = [day['count'] for day in days]
    average = rolling_average([day['count'] for day in DATA['days']])
    ceiling, step = nice_ceiling(max(counts))
    left, top, base = 44, 78, 300
    plot = width - left
    pitch = plot / len(days)
    bar = max(2.4, pitch - 2)
    body = block_title('Daily contributions', f'{short_date(days[0]["date"])} to {long_date(days[-1]["date"])}, with a 7-day average')
    value = 0
    while value <= ceiling:
        y = base - (base - top) * value / ceiling
        body += f'<path d="M{left} {y:g}H{width}" stroke="{LINE}" stroke-opacity="{1 if not value else .55}"/>'
        body += text(left - 8, y + 4, f'{value:,}', 11, DIM, anchor='end', mono=True)
        value += step
    peak = max(range(len(days)), key=lambda index: counts[index])
    for index, day in enumerate(days):
        x = left + index * pitch + (pitch - bar) / 2
        if day['count']:
            height = max(1.5, (base - top) * day['count'] / ceiling)
            latest = index == len(days) - 1
            mark = rect(x, base - height, bar, height, CITRON if latest else VIOLET, 'none', min(2, bar / 2), 'class="day-bar"')
            mark = f'<g class="glint" style="animation-delay:{4 + index * .035:.2f}s">{mark}</g>'
            body += tip(anim(mark, 'gy', .3 + index * .012), f'{long_date(day["date"])}: {day["count"]:,} contributions')
        if date.fromisoformat(day['date']).day == 1:
            body += f'<path d="M{left + index * pitch:g} {base}v5" stroke="{DIM}"/>'
            body += text(left + index * pitch, base + 20, f'{date.fromisoformat(day["date"]):%b}', 11, DIM, mono=True)
    points = [(left + index * pitch + pitch / 2, base - (base - top) * value / ceiling) for index, value in enumerate(average)]
    trace = 'M' + 'L'.join(f'{x:.1f} {y:.1f}' for x, y in points)
    body += anim(f'<path d="{trace}L{points[-1][0]:.1f} {base}L{points[0][0]:.1f} {base}Z" fill="url(#wash)"/>', 'fade', 1.2)
    body += f'<path class="redraw" pathLength="1" d="{trace}" fill="none" stroke="{PINK}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>'
    body += (f'<circle class="motion" r="3.5" fill="{PINK}" stroke="{GROUND}" stroke-width="1.5">'
             f'<animateMotion dur="12s" repeatCount="indefinite" keyPoints="0;1;1" keyTimes="0;.16;1" calcMode="linear" path="{trace}"/></circle>')
    if counts[peak]:
        px = left + peak * pitch + pitch / 2
        py = base - (base - top) * counts[peak] / ceiling
        label = f'{counts[peak]:,} on {short_date(days[peak]["date"])}'
        label_width = tw(label, 12, 600) + 16
        lx = min(max(px - label_width - 10, left), width - label_width)
        body += anim(rect(lx, py - 11, label_width, 22, RAISED_2, LINE, 11) + text(lx + 8, py + 4, label, 12, INK, 600), 'pop', 1.7)
        body += f'<circle class="ping motion" cx="{px:g}" cy="{py:g}" r="4" fill="{CITRON}"/>'
    legend_y = base + 46
    body += rect(left, legend_y - 9, 10, 10, VIOLET, 'none', 2) + text(left + 16, legend_y, 'Daily', 12, MUTED, 400)
    body += rect(left + 62, legend_y - 9, 10, 10, CITRON, 'none', 2) + text(left + 78, legend_y, 'Latest day', 12, MUTED, 400)
    body += f'<path d="M{left + 156} {legend_y - 4}h16" stroke="{PINK}" stroke-width="2" stroke-linecap="round"/>' + text(left + 178, legend_y, '7-day average', 12, MUTED, 400)
    return body, legend_y + 8


def momentum_card(width):
    metrics = activity_metrics()
    days = DATA['days']
    inner = width - 44
    label, note = momentum(metrics['last30'], metrics['previous30'])
    body = rect(0, 0, width, 338, RAISED, LINE, 16) + text(22, 34, '30-day momentum', 15, INK, 600)
    body += anim(text(22, 88, label, 46, INK, 700, spacing=-1.5), 'in', .5)
    body += text(22 + tw(label, 46, 700) - 1.5 * len(label) + 12, 88, note, 13, MUTED, 400)
    peak = max(1, metrics['last30'], metrics['previous30'])
    periods = ((days[-30:], metrics['last30'], metrics['active30'], CITRON),
               (days[-60:-30], metrics['previous30'], metrics['previous_active30'], VIOLET))
    pitch = inner / 30
    for index, (period, total, active, color) in enumerate(periods):
        y = 124 + index * 104
        if not period:
            continue
        body += text(22, y, f'{short_date(period[0]["date"])} to {short_date(period[-1]["date"])}', 13, MUTED, 400)
        body += text(width - 22, y, f'{total:,}', 15, INK, 600, 'end')
        body += rect(22, y + 10, inner, 8, LINE, 'none', 4)
        if total:
            body += tip(anim(rect(22, y + 10, max(8, inner * total / peak), 8, color, 'none', 4, 'class="period-bar"'), 'gx', .7 + index * .15),
                        f'{total:,} contributions')
        for day_index, day in enumerate(period):
            x = 22 + day_index * pitch + pitch / 2
            dot = f'<circle cx="{x:g}" cy="{y + 36}" r="{min(3.4, pitch / 2 - 1):g}" fill="{color if day["count"] else LINE}"/>'
            if day['count']:
                dot = f'<g class="glint" style="animation-delay:{5 + day_index * .06:.2f}s">{dot}</g>'
            body += tip(anim(dot, 'pop', 1 + index * .2 + day_index * .02), f'{long_date(day["date"])}: {day["count"]:,} contributions')
        body += text(22, y + 60, f'{active} of {len(period)} days active', 12, DIM, 400)
    return body


def pulse(mobile=False):
    width = 500 if mobile else 1000
    metrics = activity_metrics()
    days = DATA['days']
    busiest = max(days, key=lambda day: day['count'])
    body, top = heading('Activity at a glance', f'Public GitHub activity through {long_date(days[-1]["date"])}', width)
    tiles = (
        ('Contributions', f'{DATA["contributions"]:,}', 'in the past 12 months', ''),
        ('Active days', f'{metrics["active"]:,}', f'{metrics["active30"]} of them in the last 30 days', ''),
        ('Longest streak', f'{metrics["longest"]:,}', 'active days in a row', 'days'),
        ('Busiest day', f'{busiest["count"]:,}', long_date(busiest['date']) if busiest['count'] else 'No activity yet', ''),
    )
    tile_width = 210 if mobile else 222
    for index, (label, value, note, suffix) in enumerate(tiles):
        column, row = (index % 2, index // 2) if mobile else (index, 0)
        body += group(PAD + column * (tile_width + 16), top + row * 116, anim(kpi_tile(tile_width, label, value, note, .3 + index * .15, suffix), 'in', index * .08))
    top += 232 + 26 if mobile else 100 + 30
    chart, chart_height = daily_chart(COLUMN if mobile else 600)
    body += group(PAD, top, chart)
    if mobile:
        body += group(PAD, top + chart_height + 28, momentum_card(COLUMN))
        height = top + chart_height + 28 + 338 + PAD
    else:
        body += group(672, top, momentum_card(296))
        height = top + max(chart_height, 338) + PAD
    label, note = momentum(metrics['last30'], metrics['previous30'])
    panel('pulse-mobile.svg' if mobile else 'pulse.svg', width, height, 'Public GitHub activity at a glance',
          f'{DATA["contributions"]:,} contributions on {metrics["active"]} active days in the past 12 months, with a longest streak of '
          f'{metrics["longest"]} days. Busiest day: {busiest["count"]:,} contributions on {busiest["date"]}. Latest 30 days: '
          f'{metrics["last30"]:,} contributions on {metrics["active30"]} active days; previous 30 days: {metrics["previous30"]:,} '
          f'on {metrics["previous_active30"]}. A bar chart shows each of the latest 91 days with a seven-day average line.', body)


# ── rhythm and commit volume ─────────────────────────────────────────────────

def bubble_matrix(width):
    days = DATA['days'][-91:]
    metrics = activity_metrics()
    peak = max(1, max(day['count'] for day in days))
    left, top, row = 44, 84, 28
    pitch = (width - left) / 13
    body = block_title('Weekly rhythm', 'One bubble per day; area shows contributions')
    for weekday, label in enumerate(WEEKDAYS):
        body += text(0, top + weekday * row + 4, label, 12, DIM, 400)
    for index, day in enumerate(days):
        column = index // 7
        weekday = date.fromisoformat(day['date']).weekday()
        x, y = left + column * pitch + pitch / 2, top + weekday * row
        if day['count']:
            radius = max(2.4, 12.5 * math.sqrt(day['count'] / peak))
            top_day = day['count'] == peak
            bubble = f'<circle class="bubble" cx="{x:g}" cy="{y:g}" r="{radius:.2f}" fill="{CITRON if top_day else VIOLET}" fill-opacity="{1 if top_day else .82}" stroke="{GROUND}"/>'
            bubble = f'<g class="breathe" style="animation-delay:{3 + column * .12 + weekday * .05:.2f}s">{bubble}</g>'
            body += tip(anim(bubble, 'pop', .3 + column * .05 + weekday * .02), f'{WEEKDAYS[weekday]}, {long_date(day["date"])}: {day["count"]:,} contributions')
        else:
            body += f'<circle cx="{x:g}" cy="{y:g}" r="1.3" fill="{LINE}"/>'
    label_y = top + 6 * row + 30
    for column in (0, 4, 8, 12):
        if column * 7 < len(days):
            body += text(left + column * pitch + pitch / 2, label_y, short_date(days[column * 7]['date']), 11, DIM, anchor='middle', mono=True)
    best = max(range(7), key=lambda weekday: (metrics['weekdays'][weekday], -weekday))
    note = (f'{WEEKDAYS[best]} is the most regular day: active in {metrics["weekdays"][best]} of 13 weeks'
            if metrics['weekdays'][best] else 'No activity in these 13 weeks')
    body += text(0, label_y + 32, note, 13, MUTED, 400)
    return body, label_y + 40


def commit_volume(width):
    totals = commit_totals()
    weeks = weekly_commits()
    body = block_title('Commit volume', f'Default branches of {COMMIT_ACTIVITY["repositories"]} public repositories, past 12 months')
    stats = ((f'{totals["commits"]:,}', 'commits'), (f'+{compact(totals["additions"])}', 'lines added'), (f'−{compact(totals["deletions"])}', 'lines removed'))
    for index, (value, label) in enumerate(stats):
        x = index * (width / 3)
        body += anim(text(x, 92, value, 26, INK, 700, spacing=-.5) + text(x, 112, label, 12, MUTED, 400), 'in', .2 + index * .1)
    peak = max([1] + [max(week['additions'], week['deletions']) for week in weeks])
    ceiling, _ = nice_ceiling(peak, 4)
    left, centre, reach = 52, 214, 62
    pitch = (width - left) / 13
    for value, y in ((ceiling, centre - reach), (0, centre), (-ceiling, centre + reach)):
        body += f'<path d="M{left} {y}H{width}" stroke="{LINE}" stroke-opacity="{1 if not value else .55}"/>'
        label = '0' if not value else ('+' if value > 0 else '−') + compact(abs(value))
        body += text(left - 8, y + 4, label, 11, DIM, anchor='end', mono=True)
    for index, week in enumerate(weeks):
        x = left + index * pitch + (pitch - 14) / 2
        span = f'{short_date(week["start"])} to {short_date(week["end"])}'
        if week['additions']:
            height = max(1.5, reach * week['additions'] / ceiling)
            bar = rect(x, centre - height - 1, 14, height, CITRON, 'none', 3, 'class="added-bar"')
            body += tip(anim(f'<g class="glint" style="animation-delay:{4.5 + index * .12:.2f}s">{bar}</g>', 'gy', .5 + index * .05),
                        f'{span}: {week["additions"]:,} lines added in {week["commits"]:,} commits')
        if week['deletions']:
            height = max(1.5, reach * week['deletions'] / ceiling)
            bar = rect(x, centre + 1, 14, height, PINK, 'none', 3, 'class="removed-bar"')
            body += tip(anim(f'<g class="glint" style="animation-delay:{4.5 + index * .12:.2f}s">{bar}</g>', 'gd', .5 + index * .05),
                        f'{span}: {week["deletions"]:,} lines removed in {week["commits"]:,} commits')
    label_y = centre + reach + 24
    for column in (0, 4, 8, 12):
        if column < len(weeks):
            body += text(left + column * pitch + pitch / 2, label_y, short_date(weeks[column]['start']), 11, DIM, anchor='middle', mono=True)
    legend_y = label_y + 32
    body += rect(0, legend_y - 9, 10, 10, CITRON, 'none', 2) + text(16, legend_y, 'Lines added per week', 12, MUTED, 400)
    body += rect(166, legend_y - 9, 10, 10, PINK, 'none', 2) + text(182, legend_y, 'Lines removed', 12, MUTED, 400)
    return body, legend_y + 8


def rhythm(mobile=False):
    width = 500 if mobile else 1000
    days = DATA['days'][-91:]
    metrics = activity_metrics()
    totals = commit_totals()
    left, left_height = bubble_matrix(COLUMN)
    right, right_height = commit_volume(COLUMN)
    if mobile:
        body = group(PAD, 40, left) + group(PAD, 40 + left_height + 40, right)
        height = 40 + left_height + 40 + right_height + PAD
    else:
        body = group(PAD, 40, left) + f'<path d="M500 40V{40 + max(left_height, right_height) - 8}" stroke="{LINE}"/>' + group(532, 40, right)
        height = 40 + max(left_height, right_height) + PAD
    panel('rhythm-mobile.svg' if mobile else 'rhythm.svg', width, height, 'Weekly rhythm and commit volume',
          f'Bubble chart of daily contributions by weekday for the 13 weeks from {days[0]["date"]} to {days[-1]["date"]}. '
          f'Active days by weekday starting Monday: {", ".join(map(str, metrics["weekdays"]))}. '
          f'Commit snapshot: {totals["commits"]:,} commits, {totals["additions"]:,} lines added and {totals["deletions"]:,} lines removed '
          f'on the default branches of {COMMIT_ACTIVITY["repositories"]} public repositories.', body)


def months(mobile=False):
    """Month-by-month totals for the whole calendar, shown inside an expandable section."""
    width = 500 if mobile else 1000
    grouped = [(key, list(days)) for key, days in groupby(DATA['days'], lambda day: day['date'][:7])]
    totals = [sum(day['count'] for day in days) for _, days in grouped]
    ceiling, step = nice_ceiling(max(totals))
    left, top, base = PAD + 44, 104, 300
    pitch = (width - PAD - left) / len(grouped)
    bar = min(40, pitch * .62)
    body, _ = heading('Month by month', 'Contributions in each month of the calendar', width)
    if mobile:
        top, base = 126, 322
    value = 0
    while value <= ceiling:
        y = base - (base - top) * value / ceiling
        body += f'<path d="M{left} {y:g}H{width - PAD}" stroke="{LINE}" stroke-opacity="{1 if not value else .55}"/>'
        body += text(left - 8, y + 4, f'{value:,}', 11, DIM, anchor='end', mono=True)
        value += step
    for index, ((key, days), total) in enumerate(zip(grouped, totals)):
        x = left + index * pitch + (pitch - bar) / 2
        month = date.fromisoformat(key + '-01')
        latest = index == len(grouped) - 1
        if total:
            height = max(2, (base - top) * total / ceiling)
            mark = rect(x, base - height, bar, height, CITRON if latest else VIOLET, 'none', 4, 'class="month-bar"')
            body += tip(anim(f'<g class="glint" style="animation-delay:{4 + index * .15:.2f}s">{mark}</g>', 'gy', .2 + index * .06),
                        f'{month:%B %Y}: {total:,} contributions on {sum(day["count"] > 0 for day in days)} active days')
            if not mobile or total >= ceiling * .08:
                body += anim(text(x + bar / 2, base - height - 8, compact(total) if mobile else f'{total:,}', 11 if mobile else 12, INK, 600, 'middle'), 'in', .5 + index * .06)
        body += text(x + bar / 2, base + 20, f'{month:%b}', 11, MUTED if total else DIM, anchor='middle', mono=True)
        if month.month == 1 or index == 0:
            body += text(x + bar / 2, base + 36, f'{month:%Y}', 10, DIM, anchor='middle', mono=True)
    panel('months-mobile.svg' if mobile else 'months.svg', width, base + 62, 'Contributions month by month',
          'Monthly contribution totals: ' + '; '.join(f'{date.fromisoformat(key + "-01"):%b %Y} {total:,}' for (key, _), total in zip(grouped, totals)) + '.', body)


# ── code ─────────────────────────────────────────────────────────────────────

def repository_inventory():
    path = ROOT / 'assets/repository-inventory.json'
    return json.loads(path.read_text()) if path.is_file() else None


def treemap(width):
    categories = language_categories()
    repos = sorted(((repo, sum(repo.get('languages', {}).values())) for repo in DATA['repos']), key=lambda item: -item[1])
    repos = [(repo, size) for repo, size in repos if size]
    total = sum(size for _, size in repos)
    body = block_title('Where the code lives', f'{len(repos)} public repositories, sized by detected code bytes')
    if not repos:
        return body + text(0, 96, 'No language bytes in this snapshot', 14, MUTED, 400), 110
    cells = squarify([(index, size) for index, (_, size) in enumerate(repos)], 0, 62, width, 258)
    for order, (index, x, y, w, h) in enumerate(cells):
        repo, size = repos[index]
        segments = language_segments(repo['languages'], categories)
        color = segments[0][2] if segments else OTHER
        clip = f'c{next(_ids)}'
        cell = f'<clipPath id="{clip}"><rect x="{x + 1.5:g}" y="{y + 1.5:g}" width="{max(0, w - 3):g}" height="{max(0, h - 3):g}" rx="6"/></clipPath>'
        cell += rect(x + 1.5, y + 1.5, w - 3, h - 3, RAISED_2, color + '73', 6, 'class="cell"')
        strip, offset = '', x + 1.5
        for _, amount, segment_color in segments:
            span = (w - 3) * amount / size
            strip += rect(offset, y + h - 9.5, span, 8, segment_color)
            offset += span
        cell += f'<g clip-path="url(#{clip})">{strip}'
        if w > 96 and h > 54:
            cell += text(x + 14, y + 30, repo['name'], 15, INK, 600) + text(x + 14, y + 50, f'{size / total:.0%} of bytes', 12, MUTED, 400)
        elif h > 26 and tw(repo['name'], 12, 600) <= w - 18:
            cell += text(x + 10, y + 22, repo['name'], 12, INK, 600)
        cell += '</g>'
        cell = f'<g class="glint" style="animation-delay:{4 + order * .35:.2f}s">{cell}</g>'
        mix = ', '.join(f'{name} {amount / size:.0%}' for name, amount, _ in segments)
        body += tip(anim(cell, 'pop', .2 + order * .08), f'{repo["name"]}: {size / total:.1%} of public code bytes ({mix})')
    return body, 62 + 258 + 4


def language_list(width):
    categories = language_categories()
    aggregate = language_segments(DATA['languages'], categories)
    total = sum(amount for _, amount, _ in aggregate)
    body = block_title('Languages', 'Share of code bytes across public repositories')
    if not aggregate:
        body += text(0, 84, 'No language bytes in this snapshot', 14, MUTED, 400)
    track = width - 196
    for index, (name, amount, color) in enumerate(aggregate):
        y = 82 + index * 26
        body += f'<circle cx="5" cy="{y - 4}" r="5" fill="{color}"/>' + text(18, y, name, 14, INK, 500)
        body += rect(132, y - 9, track, 8, LINE, 'none', 4)
        body += tip(anim(rect(132, y - 9, max(3, track * amount / total), 8, color, 'none', 4, 'class="language-bar"'), 'gx', .4 + index * .1),
                    f'{name}: {amount:,} bytes')
        body += text(width, y, f'{amount / total:.1%}', 13, INK, 500, 'end')
    y = 82 + max(1, len(aggregate)) * 26 + 22
    inventory = repository_inventory()
    if inventory:
        body += f'<path d="M0 {y - 20}H{width}" stroke="{LINE}"/>'
        body += text(0, y + 14, f'{inventory["total"]:,} repositories', 19, INK, 600, spacing=-.2)
        body += text(width, y + 14, f'{inventory["public"]:,} public, {inventory["private"] + inventory["internal"]:,} private', 13, MUTED, 400, 'end')
        columns = max(1, int((width + 6) // 17))
        shown = min(inventory['total'], columns * 4)
        for index in range(shown):
            x, row = 6 + (index % columns) * 17, index // columns
            public = index < inventory['public']
            dot = f'<circle cx="{x}" cy="{y + 42 + row * 17}" r="5.5" fill="{CITRON if public else VIOLET}" fill-opacity="{1 if public else .45}"/>'
            if public:
                dot = f'<g class="glint" style="animation-delay:{5 + index * .2:.2f}s">{dot}</g>'
            body += anim(dot, 'pop', .8 + index * .012)
        y += 42 + ((shown - 1) // columns) * 17 + 14
    return body, y


def codebase(mobile=False):
    width = 500 if mobile else 1000
    categories = language_categories()
    aggregate = language_segments(DATA['languages'], categories)
    total = sum(amount for _, amount, _ in aggregate)
    left, left_height = treemap(COLUMN)
    right, right_height = language_list(COLUMN)
    if mobile:
        body = group(PAD, 40, left) + group(PAD, 40 + left_height + 40, right)
        height = 40 + left_height + 40 + right_height + PAD
    else:
        body = group(PAD, 40, left) + group(532, 40, right)
        height = 40 + max(left_height, right_height) + PAD
    summary = '; '.join(f'{name} {amount / total:.1%}' for name, amount, _ in aggregate) or 'no language bytes in this snapshot'
    inventory = repository_inventory()
    description = f'{len(DATA["repos"])} owned public repositories, excluding forks. Share of code bytes: {summary}.'
    if inventory:
        description += f' {inventory["total"]} owned repositories in total: {inventory["public"]} public and {inventory["private"] + inventory["internal"]} private.'
    panel('codebase-mobile.svg' if mobile else 'codebase.svg', width, height, 'Code across public repositories', description, body)


# ── how I build ──────────────────────────────────────────────────────────────

def craft(mobile=False):
    width = 500 if mobile else 1000
    body, top = heading('One system, many products', 'Shared tokens, themes and React components feed every interface I build', width)
    if mobile:
        body = text(PAD, 60, 'One system, many products', 28, INK, 700, spacing=-.6)
        for index, line in enumerate(wrap('Shared tokens, themes and React components feed every interface I build', 13, 400, COLUMN)):
            body += text(PAD, 84 + index * 18, line, 13, MUTED, 400)
        top = 122

    def stage(title, inner):
        return rect(0, 0, 208, 200, RAISED, LINE, 16) + text(18, 30, title, 14, INK, 600) + inner

    tokens = ''.join(f'<circle class="pulse" style="animation-delay:{index * .4:.1f}s" cx="{30 + index * 30}" cy="66" r="11" fill="{color}"/>' for index, color in enumerate((CITRON, PINK, VIOLET, AMBER)))
    tokens += text(18, 122, 'Aa', 30, INK, 700) + text(66, 122, 'Aa', 21, MUTED, 500) + text(100, 122, 'Aa', 14, DIM, 400)
    tokens += ''.join(rect(18 + offset, 148, size, 10, VIOLET, 'none', 3, 'fill-opacity=".8"') for offset, size in ((0, 8), (16, 16), (40, 32), (80, 64)))
    tokens += text(18, 182, 'Color, type, spacing', 12, DIM, 400)

    themes = rect(18, 48, 172, 54, '#f7f5ff', 'none', 10) + rect(30, 60, 60, 8, '#17162e', 'none', 4) + rect(30, 76, 96, 6, '#8a86ad', 'none', 3) + rect(142, 60, 36, 30, CITRON, 'none', 8)
    themes += rect(18, 110, 172, 54, GROUND, LINE, 10) + rect(30, 122, 60, 8, INK, 'none', 4) + rect(30, 138, 96, 6, DIM, 'none', 3) + rect(142, 122, 36, 30, VIOLET, 'none', 8)
    themes += text(18, 182, 'Light, dark, brand', 12, DIM, 400)

    components = rect(18, 48, 84, 30, CITRON, 'none', 15) + text(60, 68, 'Button', 13, GROUND, 600, 'middle')
    components += rect(110, 48, 80, 30, 'none', LINE, 8) + f'<path class="caret" d="M122 56v14" stroke="{CITRON}" stroke-width="2"/>'
    components += rect(18, 90, 18, 18, VIOLET, 'none', 5) + f'<path d="M22.5 99l3.5 3.5 6-7" fill="none" stroke="{GROUND}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>' + rect(46, 95, 70, 8, LINE, 'none', 4)
    components += rect(18, 120, 172, 40, RAISED_2, LINE, 10) + rect(30, 131, 70, 7, MUTED, 'none', 3.5) + rect(30, 145, 110, 6, DIM, 'none', 3) + f'<circle cx="170" cy="140" r="9" fill="{PINK}"/>'
    components += text(18, 182, 'Accessible React parts', 12, DIM, 400)

    products = ''
    for index, label in enumerate(('Annotation tools', 'Onboarding flows', 'Schema-driven forms', 'Assessments')):
        y = 46 + index * 36
        products += anim(rect(18, y, 172, 28, RAISED_2, LINE, 8) + f'<circle cx="34" cy="{y + 14}" r="4" fill="{SERIES[index]}"/>' + text(48, y + 19, label, 13, INK, 500), 'in', 1 + index * .12)

    stages = (('Tokens', tokens), ('Themes', themes), ('Components', components), ('Products', products))
    if mobile:
        pitch = 234
        for index, (title, inner) in enumerate(stages):
            body += group((width - 208) / 2, top + index * pitch, anim(stage(title, inner), 'in', index * .15))
            if index < len(stages) - 1:
                y = top + index * pitch + 200
                body += f'<path d="M250 {y}v34" stroke="{LINE}" stroke-width="2"/><path class="march" d="M250 {y}v34" stroke="{CITRON}" stroke-width="2.5" stroke-linecap="round" stroke-dasharray="5 19"/>'
        height = top + 3 * pitch + 200 + PAD
    else:
        pitch = 242.7
        for index, (title, inner) in enumerate(stages):
            body += group(PAD + index * pitch, top + 14, anim(stage(title, inner), 'in', index * .15))
            if index < len(stages) - 1:
                x, y = PAD + index * pitch + 208, top + 114
                body += f'<path d="M{x:g} {y}h34.7" stroke="{LINE}" stroke-width="2"/><path class="march" d="M{x:g} {y}h34.7" stroke="{CITRON}" stroke-width="2.5" stroke-linecap="round" stroke-dasharray="5 19"/>'
        height = top + 14 + 200 + PAD
    panel('craft-mobile.svg' if mobile else 'craft.svg', width, height, 'One design system feeding many products',
          'Flow diagram: design tokens for color, type and spacing feed light, dark and brand themes, which feed accessible React components, '
          'which feed annotation tools, onboarding flows, schema-driven forms and assessments.', body,
          '.caret{animation:caret 1.1s steps(1) infinite}@keyframes caret{50%{opacity:0}}')


# ── stack ────────────────────────────────────────────────────────────────────

def stack(mobile=False):
    width = 500 if mobile else 1000
    css = ''
    orbit = block_title('Frontend, in motion', 'The tools in daily rotation')
    centre_x, centre_y = 218, 252
    orbit += f'<circle cx="{centre_x}" cy="{centre_y}" r="200" fill="url(#glow)"/>'
    for angle in (-28, 28, 90):
        orbit += f'<ellipse cx="{centre_x}" cy="{centre_y}" rx="186" ry="74" transform="rotate({angle} {centre_x} {centre_y})" fill="none" stroke="{LINE}" stroke-width="1.2"/>'
    orbit += f'<circle cx="{centre_x}" cy="{centre_y}" r="44" fill="{RAISED_2}" stroke="{VIOLET}" stroke-opacity=".7"/>'
    orbit += f'<path d="M{centre_x - 14} {centre_y - 17}l-15 17 15 17M{centre_x + 14} {centre_y - 17}l15 17-15 17" fill="none" stroke="{CITRON}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
    names = ['typescript', 'nextdotjs', 'javascript', 'tailwindcss', 'git', 'redux', 'react']
    for index, name in enumerate(names):
        angle = math.radians((-28, 28, 90)[(index // 2) % 3])
        phase = index * math.tau / 7
        frames = []
        for step in range(25):
            a = phase + step * math.tau / 24
            x, y = 186 * math.cos(a), 74 * math.sin(a)
            frames.append(f'{step / 24 * 100:.3f}%{{transform:translate({centre_x + x * math.cos(angle) - y * math.sin(angle):.2f}px,{centre_y + x * math.sin(angle) + y * math.cos(angle):.2f}px)}}')
        css += f'@keyframes orbit{index}{{' + ''.join(frames) + '}'
        start = frames[0].split('{', 1)[1].rstrip('}')
        orbit += f'<g style="animation:orbit{index} {22 + index * 2}s linear infinite;{start}">'
        orbit += rect(-22, -22, 44, 44, RAISED, LINE, 12) + icon(name, -13, -13, 26, SERIES[index % 3]) + '</g>'
    grid = block_title('Tools I work with', 'Grouped by where they sit in the work')
    groups = (('Foundations', (('javascript', 'JavaScript'), ('typescript', 'TypeScript'), ('html5', 'HTML'), ('css', 'CSS'))),
              ('Interfaces', (('react', 'React'), ('nextdotjs', 'Next.js'), ('tailwindcss', 'Tailwind CSS'), ('sass', 'SCSS'))),
              ('State and workflow', (('redux', 'Redux Toolkit'), ('git', 'Git'))))
    y = 86
    order = 0
    for label, items in groups:
        grid += text(0, y, label, 13, MUTED, 500)
        for index, (name, title) in enumerate(items):
            x, row = (index % 2) * 222, y + 14 + (index // 2) * 44
            grid += anim(rect(x, row, 214, 36, RAISED, LINE, 10) + icon(name, x + 12, row + 9, 18, CITRON) + text(x + 42, row + 23, title, 14, INK, 500), 'in', .2 + order * .06)
            order += 1
        y += 14 + math.ceil(len(items) / 2) * 44 + 28
    if mobile:
        body = group(PAD, 40, orbit) + group(PAD, 40 + 470, grid)
        height = 40 + 470 + y - 14 + PAD
    else:
        body = group(PAD, 40, orbit) + group(532, 40, grid)
        height = 40 + 458 + PAD
    panel('stack-mobile.svg' if mobile else 'stack.svg', width, height, 'Frontend engineering stack',
          'React, Next.js, TypeScript, JavaScript, HTML, CSS, Tailwind CSS, SCSS, Redux Toolkit and Git. Technology icons travel around elliptical orbits.', body, css)


# ── connect ──────────────────────────────────────────────────────────────────

def connect(mobile=False):
    width = 500 if mobile else 1000
    left = text(PAD, 70, 'Good interfaces begin', 34, INK, 700, spacing=-.8) + text(PAD, 112, 'with good questions.', 34, INK, 700, spacing=-.8)
    left += text(PAD, 152, 'Open to conversations about frontend architecture,', 15, MUTED, 400)
    left += text(PAD, 174, 'design systems and product problems worth solving.', 15, MUTED, 400)
    rows = ''
    for index, (label, value) in enumerate((('LinkedIn', 'biswas-soubhik'), ('GitHub', PROFILE['username']))):
        y = 26 + index * 84
        rows += anim(rect(0, y, COLUMN, 68, RAISED, LINE, 14) + text(22, y + 28, label, 12, MUTED, 500) + text(22, y + 52, value, 19, INK, 600)
                     + group(COLUMN - 40, y + 34, f'<circle r="18" fill="none" stroke="{CITRON}" stroke-opacity=".6"/><g class="nudge" style="animation-delay:{index * .5:.1f}s">{arrow(0, 0)}</g>'), 'in', .2 + index * .12)
    if mobile:
        body = left + group(PAD, 196, rows)
        height = 196 + 178 + PAD
    else:
        body = left + group(532, 14, rows)
        height = 220
    panel('connect-mobile.svg' if mobile else 'connect.svg', width, height, f'Connect with {PROFILE["name"]}',
          f'Connect on LinkedIn at biswas-soubhik or on GitHub at {PROFILE["username"]}. Links follow this panel.', body)


# ── README sections ──────────────────────────────────────────────────────────

def picture(name, alt, link=None):
    def source(filename):
        return f'{RAW_ROOT}{filename}?v={hashlib.sha256((PANELS / filename).read_bytes()).hexdigest()[:12]}'
    markup = (f'<picture><source media="(max-width: 600px)" srcset="{source(name + "-mobile.svg")}" />'
              f'<img src="{source(name + ".svg")}" width="100%" alt="{escape(alt, quote=True)}" /></picture>')
    return f'<a href="{escape(link if link else source(name + ".svg"), quote=True)}">{markup}</a>'


def projects_section():
    return '\n'.join(
        picture(f'project-{project["art"]}', f'{project["name"]}, {project["kind"].lower()}. {project["summary"]} {project["detail"]}', project['url'])
        for project in PROJECTS)


def activity_summary():
    metrics = activity_metrics()
    days = DATA['days']
    latest, previous = days[-30:], days[-60:-30]
    return '\n'.join([
        '| Public GitHub activity | Contributions | Active days |',
        '| --- | ---: | ---: |',
        f'| {latest[0]["date"]} to {latest[-1]["date"]} | **{metrics["last30"]:,}** | **{metrics["active30"]} / 30** |',
        f'| {previous[0]["date"]} to {previous[-1]["date"]} | {metrics["previous30"]:,} | {metrics["previous_active30"]} / 30 |',
        '',
        f'**{DATA["contributions"]:,}** contributions across the calendar, **{metrics["active"]}** active days, '
        f'**{metrics["longest"]}**-day longest streak.',
    ])


def commit_cells(iso_dates):
    """Commit, added and removed totals for dates, or dashes when any date is outside the snapshot."""
    commits = COMMIT_ACTIVITY
    if not all(commits['from'] <= iso_date <= commits['to'] for iso_date in iso_dates):
        return ['—'] * 3
    rows = [commits['days'].get(iso_date, {}) for iso_date in iso_dates]
    return [f'{sum(row.get(key, 0) for row in rows):,}' for key in ('commits', 'additions', 'deletions')]


def monthly_table():
    rows = ['| Month | Contributions | Active days | Commits | Lines added | Lines removed |', '| --- | ---: | ---: | ---: | ---: | ---: |']
    grouped = [(key, list(days)) for key, days in groupby(DATA['days'], lambda day: day['date'][:7])]
    for key, days in reversed(grouped):
        month = date.fromisoformat(key + '-01')
        cells = commit_cells([day['date'] for day in days])
        rows.append(f'| {month:%B %Y} | {sum(day["count"] for day in days):,} | {sum(day["count"] > 0 for day in days)} | ' + ' | '.join(cells) + ' |')
    return '\n'.join(rows)


def daily_activity():
    """One expandable table per month that has activity, listing only its active days."""
    commits = COMMIT_ACTIVITY
    sections = [
        f'Days with no contributions are left out. Commit and line counts cover the default branches of {commits["repositories"]} '
        f'owned public repositories from {commits["from"]} through {commits["to"]} (UTC). A dash marks dates outside that snapshot.',
    ]
    grouped = [(key, list(days)) for key, days in groupby(DATA['days'], lambda day: day['date'][:7])]
    active = [(key, days) for key, days in reversed(grouped) if any(day['count'] for day in days)]
    for index, (key, days) in enumerate(active):
        month = date.fromisoformat(key + '-01')
        rows = [
            '<details open>' if index == 0 else '<details>',
            f'<summary>{month:%B %Y}: {sum(day["count"] for day in days):,} contributions</summary>',
            '',
            '| Date | Contributions | Commits | Lines added | Lines removed |',
            '| --- | ---: | ---: | ---: | ---: |',
        ]
        for day in days:
            if day['count']:
                rows.append('| ' + ' | '.join([short_date(day['date']), f'{day["count"]:,}', *commit_cells([day['date']])]) + ' |')
        rows.extend(['', '</details>'])
        sections.append('\n'.join(rows))
    return '\n\n'.join(sections)


def repository_summary():
    inventory = repository_inventory()
    repos = DATA['repos']
    line = f'**{len(repos):,}** public repositories in this snapshot, excluding forks.'
    if inventory:
        line = (f'**{inventory["total"]:,}** owned repositories as of {inventory["updated"]} IST: **{inventory["public"]:,}** public and '
                f'**{inventory["private"] + inventory["internal"]:,}** private. The charts above cover the public ones.')
    return line


SECTIONS = (
    ('hero', lambda: picture('hero', f'{PROFILE["name"]}, {PROFILE["role"]} at {PROFILE["company"]}. A design-tool view of the name with an inspect panel listing team, focus, location and stack, and a bar chart of GitHub contributions over the latest 13 weeks.')),
    ('projects', projects_section),
    ('pulse', lambda: picture('pulse', 'Engineering pulse. Four totals for the past 12 months, a bar chart of daily contributions over the latest 13 weeks with a 7-day average, and a comparison of the latest two 30-day periods.')
     + '\n' + picture('rhythm', 'Weekly rhythm and commit volume. A bubble chart of contributions by weekday across 13 weeks, and weekly lines added and removed on public default branches.')),
    ('months', lambda: picture('months', 'Bar chart of contributions in each month of the calendar.') + '\n\n' + monthly_table()),
    ('activity-data', activity_summary),
    ('daily-activity', daily_activity),
    ('codebase', lambda: picture('codebase', 'Code across public repositories. A treemap of repositories sized by code bytes, language shares, and a dot for every owned repository.')),
    ('repository-data', repository_summary),
    ('craft', lambda: picture('craft', 'Flow from design tokens to themes to React components to products: annotation tools, onboarding flows, schema-driven forms and assessments.')),
    ('stack', lambda: picture('stack', 'Frontend tools: React, Next.js, TypeScript, JavaScript, Redux Toolkit, SCSS, HTML, CSS, Tailwind CSS and Git. Icons travel around orbits.')),
    ('connect', lambda: picture('connect', f'Connect with {PROFILE["name"]} on LinkedIn or GitHub.', PROFILE['linkedin'])),
)
PANEL_NAMES = ('hero', 'pulse', 'rhythm', 'months', 'codebase', 'craft', 'stack', 'connect') + tuple(f'project-{name}' for name in ART)


def build_panels():
    for mobile in (False, True):
        for renderer in (hero, pulse, rhythm, months, codebase, craft, stack, connect):
            renderer(mobile)
        for project in PROJECTS:
            project_card(project, mobile)


def build_readme():
    readme = ROOT / 'README.md'
    content = readme.read_text()
    for section, build in SECTIONS:
        content, replaced = re.subn(
            rf'(?<=<!-- {section}:start -->).*?(?=<!-- {section}:end -->)',
            lambda _: '\n\n' + build() + '\n\n', content, flags=re.DOTALL,
        )
        if replaced != 1:
            raise RuntimeError(f'README must contain exactly one {section} section')
    readme.write_text(content)


if __name__ == '__main__':
    build_panels()
    build_readme()
    print(f'Built {len(PANEL_NAMES) * 2} self-contained profile panels')
