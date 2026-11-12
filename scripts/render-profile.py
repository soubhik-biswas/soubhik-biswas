"""Build self-contained profile graphics from public data and local artwork."""
import base64
import json
import math
import hashlib
import re
import xml.etree.ElementTree as ET
from html import escape
from pathlib import Path
from datetime import date, timedelta

ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = 'https://raw.githubusercontent.com/soubhik-biswas/soubhik-biswas/main/'
PROFILE = json.loads((ROOT / 'profile.json').read_text())
DATA = json.loads((ROOT / 'assets/public-data.json').read_text())
FEATURED = json.loads((ROOT / 'docs/projects.json').read_text())
GROUND, INK, MUTED, TRACK = '#17162e', '#f7f5ff', '#c2bedc', '#39365a'
CITRON, PERIWINKLE, BLUSH = '#d8f36b', '#ada9ff', '#f4a6d0'
LANGUAGE_COLORS = (CITRON, PERIWINKLE, BLUSH, '#f6bf78', '#82d4eb', '#ada9c8')


def inline(path, mime):
    return f'data:{mime};base64,' + base64.b64encode((ROOT / path).read_bytes()).decode()


def text(x, y, value, size=20, color=INK, mono=False, extra=''):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-family="{ "Mono" if mono else "Display"}" {extra}>{escape(str(value))}</text>'


def rect(x, y, w, h, fill='#272447', stroke='#48436b', radius=14, extra=''):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" {extra}/>'


def icon(name, x, y, size=24, color=CITRON):
    root = ET.fromstring((ROOT / f'assets/icons/{name}.svg').read_text())
    paths = ''.join(f'<path d="{p.attrib["d"]}"/>' for p in root.iter() if p.tag.endswith('path'))
    return f'<g transform="translate({x} {y}) scale({size / 24})" fill="{color}">{paths}</g>'


CSS = '''
text{font-weight:600}
.float{animation:float 6s ease-in-out infinite}.pulse{animation:pulse 3s ease-in-out infinite}
.progress{transform-box:fill-box;transform-origin:left;animation:progress 4s linear infinite}
.role{animation:role 12s infinite;opacity:0}.r1{animation-delay:0s}.r2{animation-delay:4s}.r3{animation-delay:8s}
.story{animation:story 12s infinite;opacity:0}.s1{animation-delay:0s}.s2{animation-delay:4s}.s3{animation-delay:8s}
.r1,.s1{opacity:1}
.ring{stroke-dasharray:160;stroke-dashoffset:20;animation:ring 5s ease-in-out infinite}
.bar{transform-box:fill-box;transform-origin:left;animation:grow 1.4s ease-out both}
.arrow{animation:nudge 3s ease-in-out infinite}
@keyframes float{50%{transform:translateY(-7px)}}
@keyframes pulse{50%{opacity:.4}}
@keyframes progress{0%{transform:scaleX(0)}100%{transform:scaleX(1)}}
@keyframes role{0%,27%{opacity:1}30%,100%{opacity:0}}
@keyframes story{0%,28%{opacity:1}32%,100%{opacity:0}}
@keyframes ring{50%{stroke-dashoffset:100}}
@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}
@keyframes nudge{50%{transform:translateX(6px)}}
@media(prefers-reduced-motion:reduce){*{animation:none!important}.role,.story{display:none}.r1,.s1{display:inline;opacity:1}}
'''


def svg(name, width, height, title, description, body, css=''):
    fonts = ''.join(f"@font-face{{font-family:{family};src:url({inline('assets/fonts/'+file+'.woff2', 'font/woff2')}) format('woff2');font-weight:{weight}}}" for family, file, weight in [('Display', 'space-grotesk', 600), ('Mono', 'jetbrains-mono', 400)])
    result = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>
<defs><linearGradient id="border" x2="1" y2="1"><stop stop-color="{CITRON}" stop-opacity=".5"/><stop offset=".5" stop-color="{PERIWINKLE}" stop-opacity=".3"/><stop offset="1" stop-color="{BLUSH}" stop-opacity=".5"/></linearGradient>
<linearGradient id="aurora"><stop stop-color="{CITRON}"/><stop offset=".55" stop-color="{PERIWINKLE}"/><stop offset="1" stop-color="{BLUSH}"/></linearGradient>
<radialGradient id="halo"><stop stop-color="#4b438b" stop-opacity=".65"/><stop offset="1" stop-color="{GROUND}" stop-opacity="0"/></radialGradient>
<pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r=".8" fill="#7972a3" opacity=".23"/></pattern>
<clipPath id="frame"><rect x="1" y="1" width="{width-2}" height="{height-2}" rx="24"/></clipPath></defs>
<style>{fonts}{CSS}{css}</style>
{rect(1,1,width-2,height-2,GROUND,'url(#border)',24)}
<g clip-path="url(#frame)"><rect width="{width}" height="{height}" fill="url(#dots)"/>{body}</g></svg>'''
    ET.fromstring(result)
    (ROOT / name).write_text(result + '\n')


def group(x, y, content):
    return f'<g transform="translate({x} {y})">{content}</g>'


def short_date(value):
    day = date.fromisoformat(value)
    return f'{day:%b} {day.day}'


def hero(mobile=False):
    w, h = (500, 586) if mobile else (1000, 344)
    body = text(32, 53, PROFILE['role'], 19, CITRON)
    body += text(29, 123, 'Soubhik', 72, extra='letter-spacing="-2"')
    body += text(29, 190, 'Biswas', 72, extra='letter-spacing="-2"')
    body += text(32, 231, 'Frontend architecture & design systems', 19)
    body += text(32, 263, 'React · Next.js · TypeScript', 16, MUTED)
    if not mobile:
        body += text(32, 310, PROFILE['home'], 13, MUTED)

    days = DATA['days'][-91:]
    weeks = activity_metrics()['weeks']
    peak = max(weeks)
    step = 10 ** int(math.log10(max(1, peak)))
    ceiling = max(1, math.ceil(peak / step) * step)
    weekly = text(0, 28, '13 weeks of GitHub activity', 24)
    weekly += text(0, 90, f'{sum(weeks):,}', 55, CITRON)
    weekly += text(0, 116, 'Publicly visible contributions', 13, MUTED)
    for value in (0, ceiling):
        y = 236 - value / ceiling * 92
        weekly += f'<path d="M0 {y}H395" stroke="#625a86"/>'
        weekly += text(438, y+4, f'{value:,}', 11, MUTED, True, 'text-anchor="end"')
    for index, count in enumerate(weeks):
        if count:
            height = 92 * count / ceiling
            dates = f'{short_date(days[index*7]["date"])}–{short_date(days[index*7+6]["date"])}'
            color = CITRON if index == len(weeks)-1 else '#8178bb'
            weekly += f'<g><title>{dates}: {count:,} contributions</title>'
            weekly += rect(index*30.5, 236-height, 22, height, color, 'none', 3, 'class="weekly-bar"')+'</g>'
    weekly += text(0, 261, short_date(days[0]['date']), 12, MUTED, True)
    weekly += text(395, 261, short_date(days[-1]['date']), 12, CITRON, True, 'text-anchor="end"')
    if mobile:
        body += '<path d="M32 294H468" stroke="#625a86"/>'+group(32, 308, weekly)
    else:
        body += '<path d="M486 32V312" stroke="#625a86"/>'+group(525, 31, weekly)
    svg('profile-overview-mobile.svg' if mobile else 'profile-overview.svg', w, h, 'Soubhik Biswas — Lead Frontend Engineer',
        f'Frontend architecture and design systems. {sum(weeks):,} publicly visible contributions over 13 weeks ending {days[-1]["date"]}. Peak week: {peak:,} contributions.', body)


def about(mobile=False):
    left = text(30,54,'One foundation.',32)+text(30,93,'Many product experiences.',30)
    left += text(30,132,'Shared primitives, with room for product detail.',15,MUTED)
    left += text(30,188,'DESIGN SYSTEM',12,CITRON,True)
    for i,label in enumerate(['Tokens','Themes','Components']):
        x=30+i*154
        left+=rect(x,207,140,48,'#282449','#5a5082',8)+text(x+15,237,label,15)
    left+='<path d="M100 255v33h308v-33 M254 255v33 M254 288v39 M100 327h308" stroke="#756996" fill="none" stroke-width="1.5"/>'
    left+='<path d="M254 255v33h154v39" stroke="#d8f36b" fill="none" stroke-width="2" stroke-dasharray="8 160" class="packet"/>'
    left+=text(30,311,'PRODUCT LAYER',12,PERIWINKLE,True)
    for i,label in enumerate(['Onboarding','Forms','Assessments']):
        x=30+i*154
        left+=f'<path d="M{x+70} 327v12" stroke="#756996"/>'+rect(x,339,140,48,'#242945','#505e82',8)+text(x+12,369,label,15)
    left+=text(30,437,'Architecture · validation · reusable React interfaces',13,MUTED)
    right=text(28,54,'Curiosity, in practice.',28)
    right+=text(28,87,'Outside the day job.',15,MUTED)
    for i in range(3):
        right+=rect(28+i*131,110,119,3,'#48436b','none',1)
    stories=[('Make the idea tangible.','A small prototype is a good first question.','PROTOTYPE / LEARN / REFINE'),('Follow the unfamiliar.','Build, understand it, then share the details.','EXPLORE / UNDERSTAND / SHARE'),('A little space to reset.','Music, a pause, and another perspective.','LISTEN / RESET')]
    for i,(title,caption,detail) in enumerate(stories):
        art=''
        if i==0:
            for j,(label,width) in enumerate([('idea',96),('prototype',224),('iteration',328)]):
                y=173+j*52
                art+=text(28,y,label,13,MUTED,True)+rect(28,y+12,width,7,[CITRON,PERIWINKLE,BLUSH][j],'none',2,'class="bar"')
        elif i==1:
            for j,label in enumerate(['Explore the API','Build a working version','Write down the tradeoffs']):
                y=171+j*54
                art+=f'<circle cx="38" cy="{y-5}" r="7" fill="none" stroke="{CITRON}"/>'+text(62,y,label,17)
                if j<2:art+=f'<path d="M38 {y+5}v29" stroke="#494267"/>'
        else:
            for j in range(30):
                height=10+56*abs(math.sin(j*.62))
                art+=rect(28+j*12,225-height/2,4,height,PERIWINKLE if j%3 else CITRON,'none',2,f'class="wave" style="animation-delay:{j*.07}s"')
        right+=f'<g class="story s{i+1}">'+art+rect(28+i*131,110,119,3,CITRON,'none',1,'class="progress"')+text(28,347,title,23)+text(28,380,caption,14,MUTED)+text(28,429,detail,11,CITRON,True)+'</g>'
    body=left+group(0,478,right) if mobile else left+group(550,0,right)
    css='.packet{animation:packet 4s linear infinite}.wave{transform-box:fill-box;transform-origin:center;animation:wave 2s ease-in-out infinite}@keyframes packet{to{stroke-dashoffset:-336}}@keyframes wave{50%{transform:scaleY(.45)}}'
    svg('about-life-mobile.svg' if mobile else 'about-life.svg',500 if mobile else 1000,954 if mobile else 478,'Shared frontend foundations and personal curiosity','System diagram: tokens, themes and components support onboarding, forms and assessments. Outside work: prototyping, learning and music.',body,css)


def stack(mobile=False):
    css=''
    orbit=text(26,38,'Frontend, in motion.',24)
    orbit+='<ellipse cx="245" cy="233" rx="210" ry="174" fill="url(#halo)"/>'
    for angle in [-28,28,90]:
        orbit+=f'<ellipse cx="245" cy="233" rx="190" ry="75" transform="rotate({angle} 245 233)" fill="none" stroke="#514a78" stroke-width="1.2"/>'
    orbit+='<circle cx="245" cy="233" r="47" fill="#312856" stroke="#8375ab"/>'
    orbit+='<path d="M230 215l-15 18 15 18 M260 215l15 18-15 18" fill="none" stroke="#d8f36b" stroke-width="3"/>'+text(224,308,'UI',12,CITRON,True)
    names=['typescript','nextdotjs','javascript','tailwindcss','git','redux','react']
    for i,name in enumerate(names):
        angle=math.radians([-28,28,90][(i//2)%3]); phase=i*math.tau/7
        rx,ry=(172,100) if name=='react' else (190,75)
        frames=[]
        for n in range(25):
            a=phase+n*math.tau/24; x=rx*math.cos(a);y=ry*math.sin(a)
            tx=245+x*math.cos(angle)-y*math.sin(angle); ty=233+x*math.sin(angle)+y*math.cos(angle)
            frames.append(f'{n/24*100:.3f}%{{transform:translate({tx:.2f}px,{ty:.2f}px)}}')
        css+=f'@keyframes orbit{i}{{'+''.join(frames)+'}'
        orbit+=f'<g style="animation:orbit{i} {22+i*2}s linear infinite;transform:translate({245+rx*math.cos(phase)*math.cos(angle)-ry*math.sin(phase)*math.sin(angle):.2f}px,{233+rx*math.cos(phase)*math.sin(angle)+ry*math.sin(phase)*math.cos(angle):.2f}px)">'
        orbit+=rect(-22,-22,44,44,'#2a274b','#655c8c',12)+icon(name,-13,-13,26,[CITRON,PERIWINKLE,BLUSH][i%3])
        if name=='react':
            orbit+='<g class="satellites">'
            for mx,moon in [(34,'html5'),(-34,'css')]:
                orbit+=f'<g transform="translate({mx} 0)"><g class="moon-icon">'+rect(-9,-9,18,18,'#282449','#655c8c',4)+icon(moon,-6,-6,12,CITRON)+'</g></g>'
            orbit+='</g>'
        orbit+='</g>'
    css+='.satellites{animation:moons 12s linear infinite}.moon-icon{animation:moons 12s linear infinite reverse}@keyframes moons{to{transform:rotate(360deg)}}'
    grid=text(26,75,'Tools I work with.',29)
    groups=[('FOUNDATIONS',[('javascript','JavaScript'),('typescript','TypeScript'),('html5','HTML'),('css','CSS')]),('INTERFACES',[('react','React'),('nextdotjs','Next.js'),('tailwindcss','Tailwind'),('sass','SCSS')]),('STATE & WORKFLOW',[('redux','Redux Toolkit'),('git','Git')])]
    for j,(label,items) in enumerate(groups):
        y=116+j*99
        grid+=text(26,y,label,11,MUTED,True)
        for k,(name,label) in enumerate(items):
            x=26+(k%2)*214; yy=y+13+(k//2)*34
            grid+=rect(x,yy,200,29,'#282446','#4d466e',8)+icon(name,x+9,yy+6,17,CITRON)+text(x+36,yy+20,label,13)
    grid+=text(26,430,'ARCHITECTURE / SYSTEMS / PRODUCT',11,PERIWINKLE,True)
    body=group(0,0,orbit)+group(0,450,grid) if mobile else orbit+group(500,0,grid)
    svg('stack-mobile.svg' if mobile else 'stack.svg',500 if mobile else 1000,910 if mobile else 468,'Frontend engineering stack','React, Next.js, TypeScript, JavaScript, HTML, CSS, Tailwind CSS, SCSS, Redux Toolkit and Git. Animated elliptical technology orbits.',body,css)


def activity_metrics():
    days = DATA['days']
    counts = [day['count'] for day in days]
    longest = run = 0
    for count in counts:
        run = run+1 if count else 0
        longest = max(longest, run)
    recent = counts[-91:]
    weekdays = [0] * 7
    for day in days[-91:]:
        if day['count']:
            weekdays[date.fromisoformat(day['date']).weekday()] += 1
    return {
        'active': sum(count > 0 for count in counts),
        'longest': longest,
        'last30': sum(counts[-30:]),
        'previous30': sum(counts[-60:-30]),
        'active30': sum(count > 0 for count in counts[-30:]),
        'previous_active30': sum(count > 0 for count in counts[-60:-30]),
        'weeks': [sum(recent[i:i+7]) for i in range(0, len(recent), 7)],
        'weekdays': weekdays,
    }


def activity(mobile=False):
    metrics = activity_metrics()
    days = DATA['days']
    comparison = text(0, 28, 'Two 30-day windows', 25, INK)
    comparison += text(0, 55, 'Contributions and days with activity', 13, MUTED)
    peak = max(1, metrics['last30'], metrics['previous30'])
    periods = (
        (days[-30], days[-1], metrics['last30'], metrics['active30'], CITRON),
        (days[-60], days[-31], metrics['previous30'], metrics['previous_active30'], PERIWINKLE),
    )
    for index, (start, end, count, active, color) in enumerate(periods):
        y = 100 + index*100
        period = f'{short_date(start["date"])}–{short_date(end["date"])}'
        comparison += text(0, y, period, 15, INK)
        comparison += text(435, y+1, f'{count:,}', 26, color, extra='text-anchor="end"')
        comparison += rect(0, y+13, 435, 10, TRACK, 'none', 4)
        if count:
            comparison += rect(0, y+13, 435*count/peak, 10, color, 'none', 4)
        comparison += text(0, y+46, f'{active} of 30 days active', 13, MUTED)
    busiest = max(days[-91:], key=lambda day: day['count'])
    if busiest['count']:
        peak_label = f'{short_date(busiest["date"])} was the busiest day in the 13-week window'
        peak_count = f'{busiest["count"]:,} contributions'
        comparison += text(0, 278, peak_label, 13, MUTED)
        comparison += text(0, 303, peak_count, 18, BLUSH)

    cadence = text(0, 28, 'Weekly rhythm', 25, INK)
    cadence += text(0, 55, 'Active days by weekday in the same 13 weeks', 13, MUTED)
    for index, (name, count) in enumerate(zip(('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'), metrics['weekdays'])):
        y = 96 + index*27
        cadence += text(0, y+4, name, 13, MUTED)
        cadence += rect(47, y-6, 322, 10, TRACK, 'none', 3)
        if count:
            cadence += rect(47, y-6, 322*count/13, 10, PERIWINKLE, 'none', 3)
        cadence += text(435, y+4, f'{count} / 13', 13, INK, extra='text-anchor="end"')
    cadence += text(0, 303, f'{sum(metrics["weekdays"])} active days in the 91-day window', 13, MUTED)

    if mobile:
        body = group(32, 29, comparison)+group(32, 380, cadence)
    else:
        body = group(32, 29, comparison)+group(532, 29, cadence)
    svg('activity-mobile.svg' if mobile else 'activity.svg', 500 if mobile else 1000, 721 if mobile else 368,
        'Public GitHub contribution volume and cadence',
        f'Latest 30 days: {metrics["last30"]:,} contributions over {metrics["active30"]} active days. Previous 30 days: {metrics["previous30"]:,} contributions over {metrics["previous_active30"]} active days. Active days by weekday over 13 weeks starting Monday: {", ".join(map(str, metrics["weekdays"]))}.', body)


def language_categories():
    ranked = sorted(DATA['languages'], key=lambda name: (-DATA['languages'][name], name))
    return [name for name in ranked[:5] if DATA['languages'][name] > 0]


def language_segments(breakdown, categories):
    segments = [(name, breakdown.get(name, 0), LANGUAGE_COLORS[index])
                for index, name in enumerate(categories)]
    other = sum(amount for name, amount in breakdown.items() if name not in categories)
    if other:
        segments.append(('Other', other, LANGUAGE_COLORS[-1]))
    return [(name, amount, color) for name, amount, color in segments if amount]


def language_strip(segments, y):
    total = sum(amount for _, amount, _ in segments)
    if not total:
        return ''
    body = ''
    x = 0
    for name, amount, color in segments:
        width = 435 * amount/total
        body += f'<g><title>{escape(name)} · {amount/total:.1%}</title>'
        body += rect(x, y, width, 12, color, 'none', 0)+'</g>'
        x += width
    return body


def codebase(mobile=False):
    categories = language_categories()
    aggregate = language_segments(DATA['languages'], categories)
    count = len(DATA['repos'])
    total = sum(amount for _, amount, _ in aggregate)
    composition = text(0, 28, 'The public codebase', 25, INK)
    composition += text(0, 55, f'Language share across {count} owned repositories', 13, MUTED)
    composition += language_strip(aggregate, 80)
    for index, (name, amount, color) in enumerate(aggregate):
        y = 127 + index*27
        composition += f'<circle cx="5" cy="{y-4}" r="4" fill="{color}"/>'
        composition += text(18, y, name, 14, INK)
        composition += text(435, y, f'{amount/total:.1%}', 14, INK, extra='text-anchor="end"')
    if not aggregate:
        composition += text(0, 127, 'No language bytes in this snapshot', 14, MUTED)

    repositories = {repo['name']: repo.get('languages', {}) for repo in DATA['repos']}
    projects = text(0, 28, 'Featured repository languages', 25, INK)
    projects += text(0, 55, 'Share of detected code bytes in each repository', 13, MUTED)
    descriptions = []
    for project in FEATURED:
        breakdown = repositories.get(project['slug'], {})
        size = sum(breakdown.values())
        if not size:
            continue
        label = project['name']
        y = 92 + len(descriptions)*72
        leader = max(breakdown, key=breakdown.get)
        detail = f'{leader} {breakdown[leader]/size:.0%}'
        projects += text(0, y, label, 17, INK)
        projects += text(435, y, detail, 12, MUTED, extra='text-anchor="end"')
        projects += language_strip(language_segments(breakdown, categories), y+15)
        descriptions.append(f'{label}: {detail}')

    width = 500 if mobile else 1000
    composition_height = max(127, 127 + (len(aggregate)-1)*27) + 50
    projects_height = 92 + max(0, len(descriptions)-1)*72 + 52
    if not descriptions:
        body = group((width-436)//2, 28, composition)
        height = composition_height
    elif mobile:
        body = group(32, 28, composition) + group(32, composition_height+10, projects)
        height = composition_height + projects_height + 10
    else:
        projects_top = 28 + (composition_height-projects_height)//2
        body = group(32, 28, composition) + group(532, max(28, projects_top), projects)
        height = max(composition_height, projects_height)

    summary = '; '.join(f'{name} {amount/total:.1%}' for name, amount, _ in aggregate)
    description = f'{count} owned public repositories, excluding forks. Share of code bytes: {summary or "no language bytes in this snapshot"}.'
    if descriptions:
        description += ' Featured repositories: ' + '; '.join(descriptions) + '.'
    svg('codebase-mobile.svg' if mobile else 'codebase.svg', width, height,
        'Language composition across public repositories', description, body)


def activity_table():
    metrics = activity_metrics()
    days = DATA['days']
    latest, previous = days[-30:], days[-60:-30]
    return '\n'.join([
        '| Public GitHub activity | Contributions | Active days |',
        '| --- | ---: | ---: |',
        f'| {latest[0]["date"]} to {latest[-1]["date"]} | **{metrics["last30"]:,}** | **{metrics["active30"]} / 30** |',
        f'| {previous[0]["date"]} to {previous[-1]["date"]} | {metrics["previous30"]:,} | {metrics["previous_active30"]} / 30 |',
        '',
        f'**{DATA["contributions"]:,}** contributions across the displayed calendar · **{metrics["active"]}** active days · **{metrics["longest"]}**-day longest streak',
    ])


def repository_summary():
    repos = DATA['repos']
    stars = sum(repo['stars'] for repo in repos)
    forks = sum(repo['forks'] for repo in repos)
    followers = DATA['account']['followers']
    return '\n'.join([
        '| Owned public repos | Stars | Forks | Followers |',
        '| ---: | ---: | ---: | ---: |',
        f'| **{len(repos):,}** | **{stars:,}** | **{forks:,}** | **{followers:,}** |',
    ])


def projects_table():
    rows = ['| Project | What it does |', '| --- | --- |']
    rows.extend(f'| [{project["name"]}]({project["url"]}) | {project["summary"]} {project["detail"]} |'
                for project in FEATURED)
    return '\n'.join(rows)


def connect(mobile=False):
    left=text(30,63,'Good interfaces begin',33)+text(30,107,'with good questions.',33)
    left+=text(30,156,'Frontend architecture. Design systems.',17,MUTED)+text(30,184,'Product problems worth working through.',17,MUTED)
    right=text(30,63,'Soubhik Biswas',27)
    for i,(label,value) in enumerate([('LinkedIn','biswas-soubhik'),('GitHub',PROFILE['username'])]):
        y=112+i*79
        right+=text(30,y,label,13,CITRON)+text(30,y+28,value,22)
        right+=f'<path d="M30 {y+44}h400" stroke="#4d446c"/>'+text(405,y+25,'↗',24,CITRON)
    body=left+group(0,240,right) if mobile else left+group(535,0,right)
    svg('connect-mobile.svg' if mobile else 'connect.svg',500 if mobile else 1000,535 if mobile else 296,'Connect with Soubhik Biswas','Connect on LinkedIn at biswas-soubhik or on GitHub at soubhik-biswas. Clickable links follow this panel.',body)


def calendar(mobile=False):
    days = DATA['days']
    first, last = [date.fromisoformat(day['date']) for day in (days[0], days[-1])]
    first_week = first - timedelta(days=first.weekday())
    week_count = (last-first_week).days//7 + 1
    weeks_per_band = (week_count+1)//2 if mobile else week_count
    bands = [[] for _ in range(2 if mobile else 1)]
    for day in days:
        day_date = date.fromisoformat(day['date'])
        week, weekday = divmod((day_date-first_week).days, 7)
        band, column = divmod(week, weeks_per_band)
        bands[band].append((day_date, column, weekday, day))

    colors = ('#383554', '#58517e', '#8178bb', PERIWINKLE, CITRON)
    body = text(32, 53, 'Contribution calendar', 32)
    body += text(32, 84, f'{first:%b} {first.day}, {first.year} – {last:%b} {last.day}, {last.year}', 14, MUTED)
    step = 15 if mobile else 16
    for band_index, band in enumerate(bands):
        if not band:
            continue
        top = 142 + band_index*182
        month_labels = [(day_date, column) for day_date, column, _, _ in band if day_date.day == 1]
        first_day, first_column, _, _ = band[0]
        if not month_labels or month_labels[0][1]-first_column >= 3:
            month_labels.insert(0, (first_day, first_column))
        for day_date, column in month_labels:
            body += text(64+column*step, top-14, f'{day_date:%b}', 12, MUTED)
        for weekday, label in ((0, 'Mon'), (2, 'Wed'), (4, 'Fri'), (6, 'Sun')):
            body += text(32, top+10+weekday*17, label, 11, MUTED)
        for day_date, column, weekday, day in band:
            body += f'<g><title>{day_date}: {day["count"]:,} contributions</title>'
            body += rect(64+column*step, top+weekday*17, 12, 12, colors[day['level']], 'none', 2)
            body += '</g>'

    active = sum(day['count'] > 0 for day in days)
    total = DATA['contributions']
    summary_y = 484 if mobile else 303
    body += text(32, summary_y, f'{total:,} contributions · {active:,} active days', 18)
    legend_x, legend_y = (32, 513) if mobile else (763, 292)
    body += text(legend_x, legend_y+11, 'Less', 12, MUTED)
    for index, color in enumerate(colors):
        body += rect(legend_x+36+index*18, legend_y, 13, 13, color, 'none', 2)
    body += text(legend_x+130, legend_y+11, 'More', 12, MUTED)
    svg('contribution-calendar-mobile.svg' if mobile else 'contribution-calendar.svg',
        500 if mobile else 1000, 552 if mobile else 339,
        'Soubhik Biswas public GitHub contribution calendar',
        f'Daily contributions from {first} to {last}. Colors encode five activity levels. {total:,} contributions on {active:,} active days.', body)


if __name__ == '__main__':
    for mobile in (False, True):
        for renderer in (hero, about, stack, activity, codebase, connect, calendar):
            renderer(mobile)
    readme = ROOT / 'README.md'
    content = readme.read_text()
    content = re.sub(
        rf'{re.escape(RAW_ROOT)}([\w-]+\.svg)\?v=[\w-]+',
        lambda match: f'{RAW_ROOT}{match[1]}?v={hashlib.sha256((ROOT / match[1]).read_bytes()).hexdigest()[:12]}',
        content,
    )
    sections = (
        ('activity-data', activity_table),
        ('repository-data', repository_summary),
        ('featured-projects', projects_table),
    )
    for section, build in sections:
        content = re.sub(
            rf'(?<=<!-- {section}:start -->).*?(?=<!-- {section}:end -->)',
            lambda _: '\n\n' + build() + '\n\n', content, flags=re.DOTALL,
        )
    readme.write_text(content)
    print('Built 14 self-contained profile graphics')
