"""Refresh only information available on the public GitHub profile."""
import json
import re
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USER = json.loads((ROOT / 'profile.json').read_text())['username']


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'profile-portfolio', 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read().decode()


class Calendar(HTMLParser):
    def __init__(self):
        super().__init__()
        self.days = {}
        self.tooltip = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'data-date' in attrs:
            self.days[attrs['id']] = {'date': attrs['data-date'], 'level': int(attrs['data-level']), 'count': None}
        if tag == 'tool-tip':
            self.tooltip = attrs.get('for')

    def handle_data(self, text):
        if self.tooltip in self.days:
            match = re.match(r'(No|[\d,]+) contributions? on ', text.strip())
            if match:
                self.days[self.tooltip]['count'] = 0 if match[1] == 'No' else int(match[1].replace(',', ''))

    def handle_endtag(self, tag):
        if tag == 'tool-tip':
            self.tooltip = None


def main():
    repos = []
    for page in range(1, 20):
        batch = json.loads(fetch(f'https://api.github.com/users/{USER}/repos?type=owner&per_page=100&page={page}'))
        repos.extend(r for r in batch if not r['fork'])
        if len(batch) < 100:
            break
    else:
        raise RuntimeError('Repository pagination limit reached')
    calendar = Calendar()
    calendar.feed(fetch(f'https://github.com/users/{USER}/contributions'))
    days = sorted(calendar.days.values(), key=lambda day: day['date'])
    if len(days) < 300 or any(day['count'] is None for day in days):
        raise RuntimeError('Public calendar format changed; keeping the previous snapshot')
    snapshot = {
        'updated': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
        'source': f'https://github.com/{USER}',
        'repos': [{'name': r['name'], 'url': r['html_url'], 'stars': r['stargazers_count'], 'language': r['language']} for r in repos],
        'days': days,
        'contributions': sum(day['count'] for day in days),
    }
    path = ROOT / 'assets/public-data.json'
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(snapshot, indent=2) + '\n')
    temporary.replace(path)
    print(f"Refreshed {len(repos)} public repositories and {len(days)} calendar days")


if __name__ == '__main__':
    main()
