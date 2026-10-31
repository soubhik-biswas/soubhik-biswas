"""Build self-contained profile graphics from public data and local artwork."""
import base64
import json
import math
import hashlib
import re
import xml.etree.ElementTree as ET
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = json.loads((ROOT / 'profile.json').read_text())
DATA = json.loads((ROOT / 'assets/public-data.json').read_text())
CYAN, VIOLET, PINK, MUTED = '#22d3ee', '#a78bfa', '#f472b6', '#aab4cc'


def inline(path, mime):
    return f'data:{mime};base64,' + base64.b64encode((ROOT / path).read_bytes()).decode()


def text(x, y, value, size=20, color='#edf1ff', mono=False, extra=''):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-family="{ "Mono" if mono else "Display"}" {extra}>{escape(str(value))}</text>'


def rect(x, y, w, h, fill='#151b2b', stroke='#2c354d', radius=14, extra=''):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" {extra}/>'


def image(path, x, y, w, h, extra=''):
    return f'<image x="{x}" y="{y}" width="{w}" height="{h}" href="{inline(path, "image/png")}" preserveAspectRatio="xMidYMid meet" {extra}/>'


def icon(name, x, y, size=24, color=CYAN):
    root = ET.fromstring((ROOT / f'assets/icons/{name}.svg').read_text())
    paths = ''.join(f'<path d="{p.attrib["d"]}"/>' for p in root.iter() if p.tag.endswith('path'))
    return f'<g transform="translate({x} {y}) scale({size / 24})" fill="{color}">{paths}</g>'


CSS = '''
text{font-weight:600} .muted{fill:#aab4cc}
.float{animation:float 6s ease-in-out infinite}.pulse{animation:pulse 3s ease-in-out infinite}
.swing{transform-origin:250px 14px;animation:swing 2.4s ease-out both}
.scan{animation:scan 7s ease-in-out infinite}.progress{transform-box:fill-box;transform-origin:left;animation:progress 4s linear infinite}
.role{animation:role 12s infinite;opacity:0}.r1{animation-delay:0s}.r2{animation-delay:4s}.r3{animation-delay:8s}
.story{animation:story 12s infinite;opacity:0}.s1{animation-delay:0s}.s2{animation-delay:4s}.s3{animation-delay:8s}
.r1,.s1{opacity:1}
.ring{stroke-dasharray:160;stroke-dashoffset:20;animation:ring 5s ease-in-out infinite}
.bar{transform-box:fill-box;transform-origin:left;animation:grow 1.4s ease-out both}
.arrow{animation:nudge 3s ease-in-out infinite}.city-top{animation:twinkle 5s ease-in-out infinite}
@keyframes float{50%{transform:translateY(-7px)}}
@keyframes pulse{50%{opacity:.4}}
@keyframes swing{0%{transform:translateY(-50px) rotate(-8deg)}25%{transform:rotate(5deg)}50%{transform:rotate(-3deg)}75%{transform:rotate(1deg)}100%{transform:rotate(0)}}
@keyframes scan{0%,100%{transform:translateX(-300px);opacity:0}20%{opacity:.25}70%{transform:translateX(300px);opacity:.25}80%{opacity:0}}
@keyframes progress{0%{transform:scaleX(0)}100%{transform:scaleX(1)}}
@keyframes role{0%,27%{opacity:1}30%,100%{opacity:0}}
@keyframes story{0%,28%{opacity:1}32%,100%{opacity:0}}
@keyframes ring{50%{stroke-dashoffset:100}}
@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}
@keyframes nudge{50%{transform:translateX(6px)}}
@keyframes twinkle{50%{opacity:.65}}
@media(prefers-reduced-motion:reduce){*{animation:none!important}.role,.story{display:none}.r1,.s1{display:inline;opacity:1}}
'''


def svg(name, width, height, title, description, body, css=''):
    fonts = ''.join(f"@font-face{{font-family:{family};src:url({inline('assets/fonts/'+file+'.woff2', 'font/woff2')}) format('woff2');font-weight:{weight}}}" for family, file, weight in [('Display', 'space-grotesk', 600), ('Mono', 'jetbrains-mono', 400)])
    result = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>
<defs><linearGradient id="border" x2="1" y2="1"><stop stop-color="{CYAN}" stop-opacity=".5"/><stop offset=".5" stop-color="{VIOLET}" stop-opacity=".3"/><stop offset="1" stop-color="{PINK}" stop-opacity=".5"/></linearGradient>
<linearGradient id="aurora"><stop stop-color="{CYAN}"/><stop offset=".55" stop-color="{VIOLET}"/><stop offset="1" stop-color="{PINK}"/></linearGradient>
<radialGradient id="halo"><stop stop-color="#3f427b" stop-opacity=".65"/><stop offset="1" stop-color="#0d0e16" stop-opacity="0"/></radialGradient>
<linearGradient id="foil"><stop stop-color="{CYAN}" stop-opacity="0"/><stop offset=".5" stop-color="{VIOLET}" stop-opacity=".7"/><stop offset="1" stop-color="{PINK}" stop-opacity="0"/></linearGradient>
<pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r=".8" fill="#54617e" opacity=".23"/></pattern>
<clipPath id="frame"><rect x="1" y="1" width="{width-2}" height="{height-2}" rx="24"/></clipPath></defs>
<style>{fonts}{CSS}{css}</style>
{rect(1,1,width-2,height-2,'#0d0e16','url(#border)',24)}
<g clip-path="url(#frame)"><rect width="{width}" height="{height}" fill="url(#dots)"/>{body}</g></svg>'''
    ET.fromstring(result)
    (ROOT / name).write_text(result + '\n')


def group(x, y, content):
    return f'<g transform="translate({x} {y})">{content}</g>'


def hero(mobile=False):
    w, h = (500, 780) if mobile else (1000, 430)
    body = f'<ellipse cx="{w-180}" cy="230" rx="350" ry="280" fill="url(#halo)"/>'
    body += text(34, 48, 'SOUBHIK BISWAS / PORTFOLIO', 14, CYAN, True)
    body += rect(34, 72, 250, 30, '#14212a', '#25545d', 15)
    body += '<circle cx="51" cy="87" r="4" fill="#5eead4" class="pulse"/>' + text(64, 92, 'A SONG. AN IDEA. A START.', 11, '#b0f1ed', True)
    body += text(34, 149, 'Hi there, I’m', 25, MUTED)
    body += text(31, 211, 'Soubhik Biswas', 52 if mobile else 58, 'url(#aurora)', extra='letter-spacing="-2"')
    for i, value in enumerate(['Lead Frontend Engineer', 'Frontend architecture', 'Design systems & React']):
        body += f'<g class="role r{i+1}">' + text(34, 252, value, 25) + '</g>'
    body += text(34, 289, 'There’s usually a song on.', 20, MUTED)
    body += text(34, 317, 'And something new taking shape.', 20, MUTED)
    body += text(34, 350, PROFILE['company'] + ' · ' + PROFILE['company_location'], 17, CYAN)
    body += text(34, 376, 'Home: ' + PROFILE['home'], 14, MUTED, True)
    body += text(34, 396, 'REACT / NEXT.JS / TYPESCRIPT', 12, VIOLET, True)
    px, py, pw, ph = (90, 415, 330, 330) if mobile else (650, 78, 310, 325)
    body += rect(px, py, pw, ph, '#101726', '#35435d', 18)
    body += image('assets/portrait.png', px+10, py+22, pw-20, ph-22, 'class="float"')
    body += f'<path d="M{px+6} {py+35}v-26h26 M{px+pw-32} {py+9}h26v26 M{px+6} {py+ph-35}v26h26 M{px+pw-32} {py+ph-9}h26v-26" fill="none" stroke="{CYAN}" stroke-width="2"/>'
    body += text(px+20, py+27, 'HELLO, WORLD', 11, CYAN, True)
    body += f'<circle cx="{px+pw-23}" cy="{py+22}" r="4" fill="{PINK}" class="pulse"/>'
    body += rect(px+18, py+ph-18, pw-36, 2, '#29445b', 'none', 1)
    body += rect(px+18, py+ph-18, pw-36, 2, CYAN, 'none', 1, 'class="progress"')
    svg('hero-mobile.svg' if mobile else 'hero.svg', w,h,'Soubhik Biswas — Lead Frontend Engineer', 'Frontend leadership at Deccan AI. React, Next.js and TypeScript. Kolkata and Krishnanagar, India. Original illustrated developer portrait.',body)


def about(mobile=False):
    left = text(26, 38, '01 / WHAT I BUILD', 14, CYAN, True)
    left += text(26, 76, 'Shared foundations.', 29) + text(26, 112, 'Distinct experiences.', 29)
    left += rect(26, 137, 416, 112, '#111725', '#2a354c', 10)
    left += text(43, 159, '●  ●  ●     systems / interface.tsx', 11, MUTED, True)
    left += text(43, 192, 'const experience = {', 16, VIOLET, True)
    left += text(57, 215, 'clarity: true, craft: everyday', 14, CYAN, True)
    left += text(43, 237, '};', 16, VIOLET, True)
    for i,(label,detail) in enumerate([('Frontend architecture','Reusable systems across products'),('Design systems','Tokens, themes & component libraries'),('Complex product UI','Schema-driven forms & workflows')]):
        y=281+i*57
        left += rect(26,y-22,30,30,'#19243b','none',8) + text(34,y, str(i+1),14,CYAN,True)
        left += text(70,y-1,label,20)+text(70,y+19,detail,13,MUTED)
    right=text(26,38,'02 / LIFE BETWEEN COMMITS',14,PINK,True)
    for i in range(3):
        right+=rect(26+i*141,58,130,3,'#293148','none',1)
    stories=[('Always making something.','New ideas become side projects.','BUILD / EXPERIMENT / REPEAT'),('Music is life.','A good playlist keeps me company.','LISTEN / RESET / CREATE'),('Stay curious.','Learn it. Build it. Share it.','LEARN / BUILD / SHARE')]
    for i,(title,caption,kicker) in enumerate(stories):
        art=''
        if i==1:
            for n in range(27):
                height=18+65*abs(math.sin(n*.53))
                art+=rect(43+n*14,173-height/2,5,height,CYAN if n%3 else PINK,'none',3, f'class="pulse" style="animation-delay:{n*.09}s"')
        elif i==0:
            art+=rect(73,95,320,149,'#151c30','#49587c',12)+text(97,135,'~/ideas',16,CYAN,True)
            art+=text(97,177,'build something new',18,'#f1f3ff',True)+text(97,214,'▸ start',14,VIOLET,True)
        else:
            for n in range(5):
                art+=f'<circle cx="230" cy="170" r="{25+n*15}" fill="none" stroke="{CYAN if n%2 else VIOLET}" opacity="{.7-n*.1}"/>'
            art+=text(208,180,'↗',38,CYAN)
        right+=f'<g class="story s{i+1}">{art}'+rect(26+i*141,58,130,3,PINK,'none',1,'class="progress"')+text(26,291,title,28)+text(26,322,caption,17,MUTED)+text(26,352,kicker,11,VIOLET,True)+'</g>'
    for i,(label,color) in enumerate([('BUILD',CYAN),('LEARN',VIOLET),('LISTEN',PINK)]):
        cx=83+i*145
        right+=f'<circle cx="{cx}" cy="405" r="23" fill="none" stroke="#252d41" stroke-width="4"/><circle cx="{cx}" cy="405" r="23" fill="none" stroke="{color}" stroke-width="4" class="ring" transform="rotate(-90 {cx} 405)" style="animation-delay:{i}s"/>'
        right+=text(cx-23,448,label,11,MUTED,True)
    body=group(0,0,left)+group(0,478,right) if mobile else group(0,0,left)+group(500,0,right)
    svg('about-life-mobile.svg' if mobile else 'about-life.svg',500 if mobile else 1000,954 if mobile else 478,'What I build and what keeps me curious','Frontend architecture, shared design systems and complex product interfaces. Hobbies: building new things, music and learning.',body)


def stack(mobile=False):
    css=''
    orbit=text(26,38,'03 / THE STACK',14,CYAN,True)
    orbit+='<ellipse cx="245" cy="233" rx="210" ry="174" fill="url(#halo)"/>'
    for angle in [-28,28,90]:
        orbit+=f'<ellipse cx="245" cy="233" rx="190" ry="75" transform="rotate({angle} 245 233)" fill="none" stroke="#34405a" stroke-width="1.2"/>'
    orbit+='<circle cx="245" cy="233" r="47" fill="#162439" stroke="#3b7490"/>'
    orbit+=icon('react',214,202,62)+text(215,308,'REACT',12,CYAN,True)
    names=['typescript','nextdotjs','javascript','tailwindcss','git','redux']
    for i,name in enumerate(names):
        angle=math.radians([-28,28,90][i//2]); phase=i*math.tau/6
        frames=[]
        for n in range(25):
            a=phase+n*math.tau/24; x=190*math.cos(a);y=75*math.sin(a)
            tx=245+x*math.cos(angle)-y*math.sin(angle); ty=233+x*math.sin(angle)+y*math.cos(angle)
            frames.append(f'{n/24*100:.3f}%{{transform:translate({tx:.2f}px,{ty:.2f}px)}}')
        css+=f'@keyframes orbit{i}{{'+''.join(frames)+'}'
        orbit+=f'<g style="animation:orbit{i} {22+i*2}s linear infinite;transform:translate({245+190*math.cos(phase)*math.cos(angle)-75*math.sin(phase)*math.sin(angle):.2f}px,{233+190*math.cos(phase)*math.sin(angle)+75*math.sin(phase)*math.cos(angle):.2f}px)">'
        orbit+=rect(-22,-22,44,44,'#182033','#536080',12)+icon(name,-13,-13,26,[CYAN,VIOLET,PINK][i%3])+'</g>'
    grid=text(26,75,'Tools I work with.',29)
    groups=[('FOUNDATIONS',[('javascript','JavaScript'),('typescript','TypeScript'),('html5','HTML'),('css','CSS')]),('INTERFACES',[('react','React'),('nextdotjs','Next.js'),('tailwindcss','Tailwind'),('sass','SCSS')]),('STATE & WORKFLOW',[('redux','Redux Toolkit'),('git','Git')])]
    for j,(label,items) in enumerate(groups):
        y=116+j*99
        grid+=text(26,y,label,11,MUTED,True)
        for k,(name,label) in enumerate(items):
            x=26+(k%2)*214; yy=y+13+(k//2)*34
            grid+=rect(x,yy,200,29,'#161d2d','#303d58',8)+icon(name,x+9,yy+6,17,CYAN)+text(x+36,yy+20,label,13)
    grid+=text(26,430,'ARCHITECTURE / SYSTEMS / PRODUCT',11,VIOLET,True)
    body=group(0,0,orbit)+group(0,450,grid) if mobile else orbit+group(500,0,grid)
    svg('stack-mobile.svg' if mobile else 'stack.svg',500 if mobile else 1000,910 if mobile else 468,'Frontend engineering stack','React, Next.js, TypeScript, JavaScript, HTML, CSS, Tailwind CSS, SCSS, Redux Toolkit and Git. Animated elliptical technology orbits.',body,css)


def dashboard(mobile=False):
    badge=text(26,38,'04 / BEHIND THE BUILD',12,CYAN,True)
    card=rect(94,75,310,380,'#151e30','url(#border)',20)
    card+='<path d="M231 5h38l-4 67h-30z" fill="#25334d" stroke="#52617b"/>'
    card+=text(243,57,'SB',12,CYAN,True,extra='transform="rotate(-90 243 57)"')+rect(231,66,38,20,'#78849a','#afb9cb',5)
    card+=rect(111,94,276,221,'#0d1524','#374963',12)+image('assets/portrait.png',139,100,224,215)
    card+=text(116,343,PROFILE['name'],25)+text(116,370,'LEAD FRONTEND ENGINEER',12,CYAN,True)
    card+=text(116,396,PROFILE['company'],15,MUTED)
    card+=rect(116,414,35,23,'#c3a76d','#e8c98a',4)
    for i in range(48):
        card+=f'<path d="M{178+i*3.7:.1f} 415v22" stroke="#7b8aa7" stroke-width="{1 if i%3 else 2}"/>'
    card+=f'<g clip-path="url(#badgeclip)"><rect x="100" y="80" width="180" height="380" fill="url(#foil)" class="scan"/></g>'
    badge+='<defs><clipPath id="badgeclip"><rect x="95" y="76" width="308" height="378" rx="19"/></clipPath></defs><g class="swing">'+card+'</g>'
    dash=text(26,38,'A little proof of work.',27)
    stats=[(len(DATA['repos']),'PUBLIC REPOS'),(sum(r['stars'] for r in DATA['repos']),'PUBLIC STARS'),(DATA['contributions'],'CONTRIBUTIONS')]
    for i,(value,label) in enumerate(stats):
        x=26+i*146
        dash+=rect(x,64,135,93,'#151d2f','#303e58',12)+text(x+15,109,value,32,[CYAN,VIOLET,PINK][i])+text(x+12,138,label,10,MUTED,True)
    dash+=text(26,191,'PUBLIC REPOSITORY STARS',11,MUTED,True)
    top=sorted(DATA['repos'],key=lambda r:(-r['stars'],r['name']))[:4]
    maximum=max(1,max(r['stars'] for r in top))
    for i,r in enumerate(top):
        y=218+i*35
        dash+=text(26,y,r['name'],13)+rect(220,y-13,195,10,'#242f47','none',5)
        if r['stars']:
            dash+=rect(220,y-13,195*r['stars']/maximum,10,CYAN,'none',5,'class="bar"')
        dash+=text(432,y-1,r['stars'],12,CYAN,True)
    dash+=rect(26,359,427,65,'#141c2b','#34435f',12)+text(42,384,'NOW',11,PINK,True)+text(42,408,'Frontend systems. New ideas. Good music.',15)
    dash+=text(26,452,'PUBLIC SNAPSHOT / '+DATA['updated'],10,MUTED,True)
    body=badge+group(0,478,dash) if mobile else badge+group(500,0,dash)
    svg('id-dashboard-mobile.svg' if mobile else 'id-dashboard.svg',500 if mobile else 1000,952 if mobile else 478,'Soubhik Biswas identity and public GitHub dashboard',f"Lead Frontend Engineer at {PROFILE['company']}. Snapshot {DATA['updated']}: {len(DATA['repos'])} public repositories, {DATA['contributions']} publicly visible contributions over the displayed calendar. Numbers are snapshots, refreshed daily.",body)


def connect(mobile=False):
    left=text(26,38,'06 / LET’S CONNECT',14,PINK,True)
    left+=image('assets/pointing.png',72,55,345,357)
    right=text(26,75,'What are you building?',29)+text(26,113,'I’d like to hear about it.',27)
    for i,(label,value) in enumerate([('LINKEDIN','biswas-soubhik'),('EMAIL',PROFILE['email']),('GITHUB',PROFILE['username'])]):
        y=148+i*75
        right+=rect(26,y,427,62,'#151d2d','#39425d',12)+text(43,y+23,label,11,CYAN,True)+text(43,y+47,value,16)
        right+=f'<g class="arrow">'+text(417,y+39,'↗',24,VIOLET)+'</g>'
    body=left+group(0,403,right) if mobile else left+group(500,0,right)
    svg('connect-mobile.svg' if mobile else 'connect.svg',500 if mobile else 1000,804 if mobile else 420,'Connect with Soubhik Biswas','LinkedIn: biswas-soubhik. Email: sbiswas773@gmail.com. GitHub: SoubhikBiswas-gitHub. Use the text links below the illustration to connect.',body)


def city():
    body=text(30,43,'05 / A YEAR, BUILT ONE DAY AT A TIME',14,CYAN,True)+text(30,78,'My contribution city.',30)
    body+=text(30,110,'Publicly visible activity / '+DATA['updated'],13,MUTED,True)
    days=DATA['days']
    start=__import__('datetime').date.fromisoformat(days[0]['date'])
    for day in days:
        date=__import__('datetime').date.fromisoformat(day['date']); n=(date-start).days; week=n//7; weekday=n%7
        x=133+week*13.2-weekday*12; y=168+week*3.7+weekday*13.6
        level=day['level']; height=3+level*13
        top=[(x,y-height),(x+11,y+3-height),(x,y+9-height),(x-11,y+6-height)]
        p=lambda pts:' '.join(f'{a:.1f},{b:.1f}' for a,b in pts)
        body+=f'<g><title>{day["date"]}: {day["count"]} contributions</title>'
        body+=f'<polygon points="{p([top[1],top[2],(x,y+9),(x+11,y+3)])}" fill="{["#172235","#17445b","#225e7b","#3d608e","#695a9e"][level]}"/>'
        body+=f'<polygon points="{p([top[2],top[3],(x-11,y+6),(x,y+9)])}" fill="{["#101a2a","#103449","#174861","#30436d","#4c3c75"][level]}"/>'
        body+=f'<polygon points="{p(top)}" fill="{["#243047","#237b98",CYAN,VIOLET,PINK][level]}" stroke="#0d0e16" stroke-width=".6"'+(' class="city-top"' if level else '')+'/></g>'
    body+=text(30,493,f'{DATA["contributions"]:,} contributions',20,CYAN)+text(30,521,'Each building is a day. Height follows activity.',13,MUTED)
    for i,color in enumerate(['#243047','#237b98',CYAN,VIOLET,PINK]):
        body+=rect(805+i*28,494,19,12,color,'none',3)
    body+=text(804,533,'LESS → MORE',10,MUTED,True)
    svg('contribution-city.svg',1000,554,'Soubhik Biswas public contribution city',f"An isometric city drawn from {len(days)} days of publicly visible GitHub contributions. {DATA['contributions']} contributions. Updated {DATA['updated']}. No private repository details are used.",body)


if __name__ == '__main__':
    for mobile in (False, True):
        for renderer in (hero,about,stack,dashboard,connect):
            renderer(mobile)
    city()
    readme = ROOT / 'README.md'
    content = readme.read_text()
    content = re.sub(r'(\./[\w-]+\.svg)\?v=[\w-]+', lambda m: m[1] + '?v=' + hashlib.sha256((ROOT / m[1]).read_bytes()).hexdigest()[:12], content)
    readme.write_text(content)
    print('Built 11 self-contained profile graphics')
