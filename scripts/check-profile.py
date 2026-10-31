"""Verify public data, local links and the offline SVG contract."""
import importlib.util
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SVG = '{http://www.w3.org/2000/svg}'
data = json.loads((ROOT / 'assets/public-data.json').read_text())
assert 300 <= len(data['days']) <= 372
assert all(isinstance(d['count'], int) and d['count'] >= 0 and d['level'] in range(5) for d in data['days'])
assert data['contributions'] == sum(d['count'] for d in data['days'])
assert len({r['name'] for r in data['repos']}) == len(data['repos'])
assert set(data['account']) == {'id', 'followers', 'following', 'created_at'}
assert data['account']['id'] == 54506603
assert all(type(data['account'][key]) is int and data['account'][key] >= 0 for key in ('followers','following'))
assert all(type(amount) is int and amount >= 0 for amount in data['languages'].values())
files = list(ROOT.glob('*.svg'))
panels = ['hero', 'about-life', 'stack', 'id-dashboard', 'connect', 'project-awaketab', 'project-bucketpeek', 'project-prismwink']
expected = {name+suffix+'.svg' for name in panels for suffix in ('', '-mobile')} | {'contribution-city.svg'}
assert {path.name for path in files} == expected, 'Missing or unexpected portfolio panels'
for path in files:
    source = path.read_text()
    root = ET.fromstring(source)
    assert root.tag == SVG + 'svg'
    assert root.find(SVG + 'title') is not None and root.find(SVG + 'desc') is not None
    assert 'prefers-reduced-motion' in source
    assert 'data:font/woff2;base64,' in source
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
for image in re.findall(r'(?:src|srcset)="(\./[^"?]+)', readme):
    assert (ROOT / image).is_file(), f'Broken README image {image}'
assert readme.count('<picture>') == 8
for filename, version in re.findall(r'\./([\w-]+\.svg)\?v=([\w-]+)', readme):
    assert version == hashlib.sha256((ROOT / filename).read_bytes()).hexdigest()[:12], f'Stale image cache key: {filename}'
assert 'mailto:' not in readme
assert 'email' not in json.loads((ROOT / 'profile.json').read_text())
for path in [ROOT/'README.md', ROOT/'profile.json', ROOT/'assets/public-data.json', *files]:
    assert not re.search(r'@(?:gmail|outlook|yahoo)\.',path.read_text(), re.I), f'Personal contact address in {path.name}'
assert 'https://www.linkedin.com/in/biswas-soubhik/' in readme
for project in re.findall(r'https://github.com/soubhik-biswas/([\w-]+)\)', readme):
    if project != 'soubhik-biswas':
        assert project in {r['name'] for r in data['repos']}, f'Project is not public: {project}'
spec = importlib.util.spec_from_file_location('refresh', ROOT / 'scripts/update-data.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
parser = module.Calendar()
parser.feed('<td id="d1" data-date="2026-10-30" data-level="2"></td><tool-tip for="d1">1,234 contributions on October 30th.</tool-tip><td id="d2" data-date="2026-10-31" data-level="0"></td><tool-tip for="d2">No contributions on October 31st.</tool-tip>')
assert parser.days['d1']['count'] == 1234 and parser.days['d2']['count'] == 0
assert parser.days['d1']['date'] == '2026-10-30'
print(f'PASS: {len(files)} self-contained graphics, mobile pairs, links, data integrity and calendar parsing')
