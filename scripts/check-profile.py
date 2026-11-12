"""Verify public data, local links and the offline SVG contract."""
import importlib.util
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = 'https://raw.githubusercontent.com/soubhik-biswas/soubhik-biswas/main/'
SVG = '{http://www.w3.org/2000/svg}'
data = json.loads((ROOT / 'assets/public-data.json').read_text())
assert 300 <= len(data['days']) <= 372
assert all(isinstance(d['count'], int) and d['count'] >= 0 and d['level'] in range(5) for d in data['days'])
assert data['contributions'] == sum(d['count'] for d in data['days'])
dates = [date.fromisoformat(day['date']) for day in data['days']]
assert all((right-left).days == 1 for left, right in zip(dates, dates[1:]))
assert len({r['name'] for r in data['repos']}) == len(data['repos'])
assert set(data['account']) == {'id', 'followers', 'following', 'created_at'}
assert data['account']['id'] == 54506603
assert all(type(data['account'][key]) is int and data['account'][key] >= 0 for key in ('followers','following'))
assert all(type(amount) is int and amount >= 0 for amount in data['languages'].values())
if all('languages' in repo for repo in data['repos']):
    totals = {}
    for repo in data['repos']:
        for language, amount in repo['languages'].items():
            assert type(amount) is int and amount >= 0
            totals[language] = totals.get(language, 0) + amount
    assert totals == data['languages']
files = list(ROOT.glob('*.svg'))
panels = ['profile-overview', 'about-life', 'stack', 'activity', 'codebase', 'connect', 'contribution-calendar']
expected = {name+suffix+'.svg' for name in panels for suffix in ('', '-mobile')}
assert {path.name for path in files} == expected, 'Missing or unexpected portfolio panels'
for path in files:
    source = path.read_text()
    root = ET.fromstring(source)
    assert root.tag == SVG + 'svg'
    assert root.find(SVG + 'title') is not None and root.find(SVG + 'desc') is not None
    assert 'prefers-reduced-motion' in source
    assert 'data:font/woff2;base64,' in source
    assert root.find('.//' + SVG + 'image') is None, f'Unexpected raster in {path.name}'
    ids = [e.attrib['id'] for e in root.iter() if 'id' in e.attrib]
    assert len(set(ids)) == len(ids), f'Duplicate identifiers in {path.name}'
    for element in root.iter():
        assert element.tag not in (SVG + 'script', SVG + 'foreignObject')
        for key, value in element.attrib.items():
            assert not key.lower().startswith('on')
            if key.endswith('href'):
                assert value.startswith(('data:', '#')), f'External asset in {path.name}'
    for target in re.findall(r'url\(#([^)]+)\)', source):
        assert target in ids, f'Missing definition {target} in {path.name}'
readme = (ROOT / 'README.md').read_text()
images = re.findall(rf'(?:src|srcset)="{re.escape(RAW_ROOT)}([\w-]+\.svg)\?v=([\da-f]{{12}})"', readme)
assert {name for name, _ in images} == expected, 'README must link every graphic through its versioned raw URL'
for filename, version in images:
    assert version == hashlib.sha256((ROOT / filename).read_bytes()).hexdigest()[:12], f'Stale image cache key: {filename}'
assert readme.count('<picture>') == len(panels)
assert readme.count('<!-- activity-data:start -->') == 1
assert readme.count('<!-- activity-data:end -->') == 1
assert f'{sum(day["count"] for day in data["days"][-30:]):,}' in readme
assert readme.count('<!-- repository-inventory:start -->') == 1
assert readme.count('<!-- repository-inventory:end -->') == 1
inventory_section = readme.split('<!-- repository-inventory:start -->')[1].split('<!-- repository-inventory:end -->')[0]
inventory_path = ROOT / 'docs/repository-inventory.json'
if inventory_path.is_file():
    inventory = json.loads(inventory_path.read_text())
    assert set(inventory) == {'updated', 'total', 'public', 'private', 'internal', 'forks'}
    assert date.fromisoformat(inventory['updated']).isoformat() == inventory['updated']
    keys = ('total', 'public', 'private', 'internal', 'forks')
    assert all(type(inventory[key]) is int and inventory[key] >= 0 for key in keys)
    assert inventory['total'] == sum(inventory[key] for key in ('public', 'private', 'internal'))
    assert inventory['forks'] <= inventory['total']
    displayed = keys if inventory['internal'] else ('total', 'public', 'private', 'forks')
    assert re.findall(r'\*\*([\d,]+)\*\*', inventory_section) == [f'{inventory[key]:,}' for key in displayed]
    assert inventory['updated'] in inventory_section
else:
    assert not inventory_section.strip()
repository_data = readme.split('<!-- repository-data:start -->')[1].split('<!-- repository-data:end -->')[0]
assert re.findall(r'\*\*([\d,]+)\*\*', repository_data) == [
    f'{len(data["repos"]):,}',
    f'{sum(repo["stars"] for repo in data["repos"]):,}',
    f'{sum(repo["forks"] for repo in data["repos"]):,}',
    f'{data["account"]["followers"]:,}',
]
assert 'id-dashboard' not in readme and 'avatar.jpg' not in readme
assert 'mailto:' not in readme
assert 'email' not in json.loads((ROOT / 'profile.json').read_text())
for path in [ROOT/'README.md', ROOT/'profile.json', ROOT/'assets/public-data.json', *files]:
    assert not re.search(r'@(?:gmail|outlook|yahoo)\.',path.read_text(), re.I), f'Personal contact address in {path.name}'
assert 'https://www.linkedin.com/in/biswas-soubhik/' in readme
projects = json.loads((ROOT / 'docs/projects.json').read_text())
feature_rows = readme.split('<!-- featured-projects:start -->')[1].split('<!-- featured-projects:end -->')[0]
assert re.findall(r'^\| \[([^\]]+)\]\((https://[^)]+)\)', feature_rows, re.M) == [
    (project['name'], project['url']) for project in projects
]
assert 'https://soubhik-biswas.github.io/soubhik-biswas/' not in readme
daily = readme.split('<!-- daily-activity:start -->')[1].split('<!-- daily-activity:end -->')[0]
assert daily.count('<details open>') == 1
assert daily.count('</details>') == len({day['date'][:7] for day in data['days']})
assert len(re.findall(r'^\| [A-Z][a-z]{2} \d+ \|', daily, re.M)) == len(data['days'])
spec = importlib.util.spec_from_file_location('refresh', ROOT / 'scripts/update-data.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
parser = module.Calendar()
parser.feed('<td id="d1" data-date="2026-10-30" data-level="2"></td><tool-tip for="d1">1,234 contributions on October 30th.</tool-tip><td id="d2" data-date="2026-10-31" data-level="0"></td><tool-tip for="d2">No contributions on October 31st.</tool-tip>')
assert parser.days['d1']['count'] == 1234 and parser.days['d2']['count'] == 0
assert parser.days['d1']['date'] == '2026-10-30'
print(f'PASS: {len(files)} self-contained graphics, mobile pairs, links, data integrity and calendar parsing')
