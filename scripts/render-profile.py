"""Build self-contained profile graphics from public data and local artwork."""
import base64
import json
import math
import mimetypes
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
    return f'<image x="{x}" y="{y}" width="{w}" height="{h}" href="{inline(path, mimetypes.guess_type(path)[0])}" preserveAspectRatio="xMidYMid meet" {extra}/>'


def icon(name, x, y, size=24, color=CYAN):
    root = ET.fromstring((ROOT / f'assets/icons/{name}.svg').read_text())
    paths = ''.join(f'<path d="{p.attrib["d"]}"/>' for p in root.iter() if p.tag.endswith('path'))
    return f'<g transform="translate({x} {y}) scale({size / 24})" fill="{color}">{paths}</g>'


CSS = '''
text{font-weight:600}.count-final{animation:count-final .54s linear both}.count-step{opacity:0;animation:count-step .18s linear}@keyframes count-final{0%,99%{opacity:0}100%{opacity:1}}@keyframes count-step{0%,99%{opacity:1}100%{opacity:0}} .muted{fill:#aab4cc}
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
@media(prefers-reduced-motion:reduce){*{animation:none!important}.count-step{display:none}.role,.story{display:none}.r1,.s1{display:inline;opacity:1}}
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
    w, h = (500, 890) if mobile else (1000, 544)
    body = text(34, 51, PROFILE['role'], 20, CYAN)
    body += '<g class="name-reveal">'+text(29, 148, 'Soubhik', 84, extra='letter-spacing="-3"')+text(29, 235, 'Biswas', 84, extra='letter-spacing="-3"')+'</g>'
    body += '<path d="M35 263h70" stroke="#22d3ee" stroke-width="3" class="line-reveal"/>'
    body += text(34, 311, 'I build the systems', 27) + text(34, 347, 'behind product interfaces.', 27)
    body += text(34, 391, 'React · Next.js · TypeScript', 17, MUTED)
    body += text(34, 447, PROFILE['company'], 19, CYAN)
    body += text(34, 474, 'Company office · '+PROFILE['company_location'], 13, MUTED)
    body += text(34, 507, PROFILE['home'], 13, MUTED)
    px, py, size = (78, 542, 332) if mobile else (590, 93, 366)
    body += '<defs><clipPath id="portrait-crop">'+rect(px,py,size,size,'white','none',8)+'</clipPath></defs>'
    body += f'<g clip-path="url(#portrait-crop)">'+image('assets/avatar.jpg',px,py,size,size)+'</g>'
    body += f'<path d="M{px-14} {py+45}v-59h59 M{px+size+14} {py+size-45}v59h-59" stroke="{CYAN}" fill="none" stroke-width="1.5"/>'
    if not mobile:
        body += text(px, 496, 'Frontend architecture / Design systems', 12, MUTED, True)
    svg('hero-mobile.svg' if mobile else 'hero.svg',w,h,'Soubhik Biswas — Lead Frontend Engineer', 'Frontend architecture, React design systems and complex product interfaces. Lead Frontend Engineer at Deccan AI. Home: Kolkata / Krishnanagar, India. Company office: Hyderabad, Telangana.',body,'.name-reveal{animation:name-reveal 1.2s cubic-bezier(.16,1,.3,1) both}@keyframes name-reveal{from{clip-path:inset(0 100% 0 0)}to{clip-path:inset(0 0 0 0)}}.line-reveal{stroke-dasharray:70;animation:trace 1.6s cubic-bezier(.16,1,.3,1) both}@keyframes trace{from{stroke-dashoffset:70}to{stroke-dashoffset:0}}')


def about(mobile=False):
    left = text(30,54,'One foundation.',32)+text(30,93,'Many product experiences.',30)
    left += text(30,132,'Shared primitives, with room for product detail.',15,MUTED)
    left += text(30,188,'DESIGN SYSTEM',12,CYAN,True)
    for i,label in enumerate(['Tokens','Themes','Components']):
        x=30+i*154
        left+=rect(x,207,140,48,'#14202b','#315064',8)+text(x+15,237,label,15)
    left+='<path d="M100 255v33h308v-33 M254 255v33 M254 288v39 M100 327h308" stroke="#42536a" fill="none" stroke-width="1.5"/>'
    left+='<path d="M254 255v33h154v39" stroke="#22d3ee" fill="none" stroke-width="2" stroke-dasharray="8 160" class="packet"/>'
    left+=text(30,311,'PRODUCT LAYER',12,VIOLET,True)
    for i,label in enumerate(['Onboarding','Forms','Assessments']):
        x=30+i*154
        left+=f'<path d="M{x+70} 327v12" stroke="#42536a"/>'+rect(x,339,140,48,'#1b1930','#4b4165',8)+text(x+12,369,label,15)
    left+=text(30,437,'Architecture · validation · reusable React interfaces',13,MUTED)
    right=text(28,54,'Curiosity, in practice.',28)
    right+=text(28,87,'Outside the day job.',15,MUTED)
    for i in range(3):
        right+=rect(28+i*131,110,119,3,'#34384d','none',1)
    stories=[('Make the idea tangible.','A small prototype is a good first question.','PROTOTYPE / LEARN / REFINE'),('Follow the unfamiliar.','Build, understand it, then share the details.','EXPLORE / UNDERSTAND / SHARE'),('A little space to reset.','Music, a pause, and another perspective.','LISTEN / RESET')]
    for i,(title,caption,detail) in enumerate(stories):
        art=''
        if i==0:
            for j,(label,width) in enumerate([('idea',96),('prototype',224),('iteration',328)]):
                y=173+j*52
                art+=text(28,y,label,13,MUTED,True)+rect(28,y+12,width,7,[CYAN,VIOLET,PINK][j],'none',2,'class="bar"')
        elif i==1:
            for j,label in enumerate(['Explore the API','Build a working version','Write down the tradeoffs']):
                y=171+j*54
                art+=f'<circle cx="38" cy="{y-5}" r="7" fill="none" stroke="{CYAN}"/>'+text(62,y,label,17)
                if j<2:art+=f'<path d="M38 {y+5}v29" stroke="#3a4257"/>'
        else:
            for j in range(30):
                height=10+56*abs(math.sin(j*.62))
                art+=rect(28+j*12,225-height/2,4,height,VIOLET if j%3 else CYAN,'none',2,f'class="wave" style="animation-delay:{j*.07}s"')
        right+=f'<g class="story s{i+1}">'+art+rect(28+i*131,110,119,3,CYAN,'none',1,'class="progress"')+text(28,347,title,23)+text(28,380,caption,14,MUTED)+text(28,429,detail,11,CYAN,True)+'</g>'
    body=left+group(0,478,right) if mobile else left+group(550,0,right)
    css='.packet{animation:packet 4s linear infinite}.wave{transform-box:fill-box;transform-origin:center;animation:wave 2s ease-in-out infinite}@keyframes packet{to{stroke-dashoffset:-336}}@keyframes wave{50%{transform:scaleY(.45)}}'
    svg('about-life-mobile.svg' if mobile else 'about-life.svg',500 if mobile else 1000,954 if mobile else 478,'Shared frontend foundations and personal curiosity','System diagram: tokens, themes and components support onboarding, forms and assessments. Outside work: prototyping, learning and music.',body,css)


def stack(mobile=False):
    css=''
    orbit=text(26,38,'Frontend, in motion.',24)
    orbit+='<ellipse cx="245" cy="233" rx="210" ry="174" fill="url(#halo)"/>'
    for angle in [-28,28,90]:
        orbit+=f'<ellipse cx="245" cy="233" rx="190" ry="75" transform="rotate({angle} 245 233)" fill="none" stroke="#34405a" stroke-width="1.2"/>'
    orbit+='<circle cx="245" cy="233" r="47" fill="#162439" stroke="#3b7490"/>'
    orbit+='<path d="M230 215l-15 18 15 18 M260 215l15 18-15 18" fill="none" stroke="#22d3ee" stroke-width="3"/>'+text(224,308,'UI',12,CYAN,True)
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
        orbit+=rect(-22,-22,44,44,'#182033','#536080',12)+icon(name,-13,-13,26,[CYAN,VIOLET,PINK][i%3])
        if name=='react':
            orbit+='<g class="satellites">'
            for mx,moon in [(34,'html5'),(-34,'css')]:
                orbit+=f'<g transform="translate({mx} 0)"><g class="moon-icon">'+rect(-9,-9,18,18,'#14202b','#536080',4)+icon(moon,-6,-6,12,CYAN)+'</g></g>'
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
            grid+=rect(x,yy,200,29,'#161d2d','#303d58',8)+icon(name,x+9,yy+6,17,CYAN)+text(x+36,yy+20,label,13)
    grid+=text(26,430,'ARCHITECTURE / SYSTEMS / PRODUCT',11,VIOLET,True)
    body=group(0,0,orbit)+group(0,450,grid) if mobile else orbit+group(500,0,grid)
    svg('stack-mobile.svg' if mobile else 'stack.svg',500 if mobile else 1000,910 if mobile else 468,'Frontend engineering stack','React, Next.js, TypeScript, JavaScript, HTML, CSS, Tailwind CSS, SCSS, Redux Toolkit and Git. Animated elliptical technology orbits.',body,css)


def countup(x,y,value,size,color):
    result=text(x,y,f'{value:,}',size,color,extra='class="count-final"')
    for i in range(3):
        result+=text(x,y,f'{round(value*(i+1)/4):,}',size,color,extra=f'class="count-step" style="animation-delay:{i*.18}s"')
    return result


def activity_metrics():
    counts=[d['count'] for d in DATA['days']]
    longest=run=0
    for count in counts:
        run=run+1 if count else 0
        longest=max(longest,run)
    return {'active':sum(c>0 for c in counts),'longest':longest,'last30':sum(counts[-30:]),'last7':sum(counts[-7:]),'weeks':[sum(counts[-91:][i:i+7]) for i in range(0,91,7)]}


def dashboard(mobile=False):
    metrics=activity_metrics()
    card=text(30,54,'Behind the work.',26)
    card+='<path d="M160 84h40l-6 66h-28z" fill="#263449" stroke="#556179"/>'
    card+=rect(54,148,252,376,'#151c2c','#47536b',14)+rect(146,140,68,17,'#7b8799','none',4)
    card+=text(75,182,'PUBLIC PROFILE',10,CYAN,True)
    card+=image('assets/avatar.jpg',76,198,208,208)
    card+=text(76,439,PROFILE['name'],23)+text(76,465,'Lead Frontend Engineer',13,CYAN)
    card+=text(76,492,PROFILE['company'],14,MUTED)
    card+='<defs><clipPath id="badgeclip"><rect x="55" y="149" width="250" height="374" rx="13"/></clipPath></defs><g clip-path="url(#badgeclip)"><rect x="58" y="152" width="110" height="368" fill="url(#foil)" class="scan"/></g>'
    card+=text(30,575,'Kolkata / Krishnanagar',16)+text(30,600,'India',14,MUTED)
    dash=text(0,54,'Public activity, measured.',30)
    dash+=text(0,83,DATA['days'][0]['date']+' — '+DATA['days'][-1]['date'],11,MUTED,True)
    dash+=countup(0,153,DATA['contributions'],61,CYAN)+text(217,142,'contributions',18)+text(217,165,'Publicly visible calendar',12,MUTED)
    stats=[(metrics['last30'],'LAST 30 DAYS'),(metrics['last7'],'LAST 7 DAYS'),(metrics['active'],'ACTIVE DAYS'),(metrics['longest'],'LONGEST STREAK / DAYS')]
    for i,(value,label) in enumerate(stats):
        x=(i%2)*225;y=214+(i//2)*78
        dash+=countup(x,y,value,31,VIOLET if i%2 else '#edf1ff')+text(x,y+23,label,10,MUTED,True)
    dash+=text(0,389,'WEEKLY CONTRIBUTIONS / LAST 13 WEEKS',10,MUTED,True)
    maximum=max(1,max(metrics['weeks']))
    for i,count in enumerate(metrics['weeks']):
        height=78*count/maximum;x=i*34
        if count:
            dash+=f'<g><title>{count} contributions in week {i+1} of the displayed 13 weeks</title>'+rect(x,491-max(2,height),23,max(2,height),CYAN if i==12 else '#577fba','none',3,'class="vertical-bar"')+'</g>'
    dash+=text(0,511,'13 weeks ago',10,MUTED,True)+text(374,511,'Latest',10,CYAN,True)
    dash+=text(0,559,f'{len(DATA["repos"])} repos   {sum(r["stars"] for r in DATA["repos"])} stars   {sum(r["forks"] for r in DATA["repos"])} forks',14)
    dash+=text(0,585,f'{DATA["account"]["followers"]} followers   {DATA["account"]["following"]} following',13,MUTED)
    ranked=sorted(DATA['languages'].items(),key=lambda pair:-pair[1])
    languages=ranked[:5]
    if len(ranked)>5:
        languages.append(('Other',sum(amount for _,amount in ranked[5:])))
    total=sum(DATA['languages'].values()) or 1
    lang=text(30,39,'Language composition',24)+text(30,67,'Share of code bytes across owned public repositories',12,MUTED)
    offset=30
    for i,(name,amount) in enumerate(languages):
        width=440*amount/total
        lang+=rect(offset,88,width,11,[CYAN,VIOLET,PINK,'#80c5a8','#ddbb77','#adb5ca'][i],'none',0)
        offset+=width
    for i,(name,amount) in enumerate(languages):
        x=30+(i%2)*225;y=129+(i//2)*29
        lang+=f'<circle cx="{x+3}" cy="{y-4}" r="3" fill="{[CYAN,VIOLET,PINK,"#80c5a8","#ddbb77","#adb5ca"][i]}"/>'+text(x+13,y,name,12)+text(x+155,y,f'{amount/total:.1%}',11,MUTED,True)
    footer=text(30,34,'PUBLIC SNAPSHOT / '+DATA['updated'],10,CYAN,True)+text(30,58,'Daily refresh · GitHub public API + contribution calendar',11,MUTED)
    if mobile:
        body=group(70,0,card)+group(30,650,dash)+group(0,1270,lang)+group(0,1480,footer)
        w,h=500,1558
    else:
        body=card+group(385,0,dash)+group(355,610,lang)+group(0,805,footer)
        w,h=1000,884
    svg('id-dashboard-mobile.svg' if mobile else 'id-dashboard.svg',w,h,'Soubhik Biswas public GitHub analytics',f'Snapshot {DATA["updated"]}. {DATA["contributions"]} contributions, {metrics["active"]} active days, {metrics["longest"]}-day longest streak, {metrics["last30"]} contributions in the last 30 displayed days, {len(DATA["repos"])} public repositories. Languages measure public repository bytes, not proficiency. All numbers are public snapshots.',body,'.vertical-bar{transform-box:fill-box;transform-origin:bottom;animation:rise 1.6s cubic-bezier(.16,1,.3,1) both}@keyframes rise{from{transform:scaleY(.02)}to{transform:scaleY(1)}}')


def projects(mobile=False):
    cases=[('awaketab','AwakeTab','A screen that stays awake.','Browser state is the source of truth.','Screen Wake Lock lifecycle handling,','clock faces and an embeddable widget.','Astro / React / TypeScript',CYAN),('bucketpeek','BucketPeek','Storage, made navigable.','An S3 browser with a media pipeline.','Search, previews, timed sharing links','and on-demand video repair paths.','Next.js / TypeScript / AWS SDK',VIOLET),('prismwink','Prismwink','A gesture becomes an effect.','Camera frames, processed locally.','Gesture-triggered vanish and return,','with microphone state kept intentional.','React / MediaPipe / Canvas',PINK)]
    for slug,name,title,lead,line1,line2,stack_label,color in cases:
        visual=rect(26,27,448,316,'#121b29','#354459',10)
        if slug!='bucketpeek':
            source='assets/projects/awaketab.jpg' if slug=='awaketab' else 'assets/projects/prismwink.png'
            visual+=image(source,35,37,430,296)
            visual+=text(30,369,'ACTUAL PRODUCT / PUBLIC REPOSITORY',10,MUTED,True)
        else:
            visual+=text(49,62,'REQUEST → PREVIEW',12,VIOLET,True)
            nodes=[(49,94,174,'S3 objects'),(260,94,187,'Signed access'),(49,184,174,'Media inspection'),(260,184,187,'Repair / convert')]
            for x,y,width,label in nodes:
                visual+=rect(x,y,width,47,'#1b2134','#4e4b6a',8)+text(x+12,y+29,label,15)
            visual+='<path d="M223 117h37 M136 141v43 M353 141v43 M223 207h37 M353 231v46H136v-46" fill="none" stroke="#a78bfa" stroke-width="1.5"/>'
            visual+=rect(170,259,160,42,'#172b34','#356576',8)+text(191,286,'Browser preview',15,CYAN)
            visual+=text(30,369,'ARCHITECTURE / SOURCE-DERIVED DIAGRAM',10,MUTED,True)
        content=text(26,52,name,32,color)+text(26,102,title,27)
        content+=text(26,142,lead,17)+text(26,188,line1,15,MUTED)+text(26,212,line2,15,MUTED)
        content+=text(26,273,stack_label,12,color,True)
        content+='<path d="M26 307h401" stroke="#30394d"/>'+text(26,345,'Explore the source',15)+text(407,346,'↗',23,color)
        if slug=='awaketab':
            visual+='<circle cx="445" cy="52" r="7" fill="#22d3ee" class="pulse"/>'
        if slug=='prismwink':
            visual+='<path d="M40 325h420" stroke="#f472b6" stroke-width="2" stroke-dasharray="18 30" class="effect-line"/>'
        body=visual+group(0,391,content) if mobile else visual+group(500,0,content)
        svg('project-'+slug+('-mobile' if mobile else '')+'.svg',500 if mobile else 1000,780 if mobile else 400,name+' — public project',title+' '+lead+' '+line1+' '+line2+' '+stack_label+'. Read the linked public repository for implementation and limitations.',body,'.effect-line{animation:effect 3s linear infinite}@keyframes effect{to{stroke-dashoffset:-96}}')


def connect(mobile=False):
    left=text(30,63,'Good interfaces begin',33)+text(30,107,'with good questions.',33)
    left+=text(30,156,'Frontend architecture. Design systems.',17,MUTED)+text(30,184,'Product problems worth working through.',17,MUTED)
    right=text(30,63,'Soubhik Biswas',27)
    for i,(label,value) in enumerate([('LinkedIn','biswas-soubhik'),('GitHub',PROFILE['username'])]):
        y=112+i*79
        right+=text(30,y,label,13,CYAN)+text(30,y+28,value,22)
        right+=f'<path d="M30 {y+44}h400" stroke="#30394d"/>'+text(405,y+25,'↗',24,CYAN)
    body=left+group(0,240,right) if mobile else left+group(535,0,right)
    svg('connect-mobile.svg' if mobile else 'connect.svg',500 if mobile else 1000,535 if mobile else 296,'Connect with Soubhik Biswas','Connect on LinkedIn at biswas-soubhik or on GitHub at soubhik-biswas. Clickable links follow this panel.',body)


def city():
    body=text(30,43,'A year, built one day at a time.',26,CYAN)+text(30,78,'My contribution city.',30)
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
        for renderer in (hero,about,stack,dashboard,projects,connect):
            renderer(mobile)
    city()
    readme = ROOT / 'README.md'
    content = readme.read_text()
    content = re.sub(r'(\./[\w-]+\.svg)\?v=[\w-]+', lambda m: m[1] + '?v=' + hashlib.sha256((ROOT / m[1]).read_bytes()).hexdigest()[:12], content)
    readme.write_text(content)
    print('Built 17 self-contained profile graphics')
