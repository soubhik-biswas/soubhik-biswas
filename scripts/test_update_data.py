"""Public-data refresh contracts, exercised without live network access."""
import importlib.util
import io
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

spec = importlib.util.spec_from_file_location('update_data', Path(__file__).with_name('update-data.py'))
refresh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(refresh)


def calendar_html(length=300, missing_count=False):
    days = []
    for i in reversed(range(length)):
        day = date(2026, 1, 1) + timedelta(days=i)
        count = i % 5
        label = f'{count} contribution' + ('' if count == 1 else 's') if count else 'No contributions'
        tooltip = '' if missing_count and i == 0 else f'<tool-tip for="d{i}">{label} on {day}.</tool-tip>'
        days.append(f'<td id="d{i}" data-date="{day}" data-level="{count}"></td>{tooltip}')
    return ''.join(days)


def repository(name, fork=False):
    return {'name': name, 'fork': fork, 'html_url': f'https://github.com/{refresh.USER}/{name}',
            'stargazers_count': 2, 'language': 'TypeScript', 'unused_field': 'not published'}


class RefreshTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / 'assets').mkdir()
        self.snapshot = self.root / 'assets/public-data.json'
        self.previous = b'{"previous": "keep this snapshot"}\n'
        self.snapshot.write_bytes(self.previous)
        root_patch = patch.object(refresh, 'ROOT', self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)

    def assert_preserved(self):
        self.assertEqual(self.snapshot.read_bytes(), self.previous)
        self.assertFalse(self.snapshot.with_suffix('.tmp').exists())

    # Value: protects=public pagination, filtering, transport and complete snapshot output;
    # fails_when=authentication is sent, pagination stops early or unrelated fields leak;
    # why_new=the existing parser check does not execute the refresh entry point;
    # seam=none; no_claim=upstream availability or remote workflow execution (HTTP fixtures).
    def test_refresh_paginates_and_writes_only_public_fields(self):
        first = [repository(f'project-{i}', fork=i == 0) for i in range(100)]
        second = [repository('last-project')]
        seen = []

        def respond(request, timeout):
            url = request.full_url
            seen.append(url)
            self.assertEqual(timeout, 45)
            self.assertFalse(any(key.lower() == 'authorization' for key in request.headers))
            if url.endswith('repos?type=owner&per_page=100&page=1'):
                body = json.dumps(first)
            elif url.endswith('repos?type=owner&per_page=100&page=2'):
                body = json.dumps(second)
            elif url == f'https://github.com/users/{refresh.USER}/contributions':
                body = calendar_html()
            elif url == f'https://api.github.com/users/{refresh.USER}':
                body = json.dumps({'id': 54506603, 'followers': 4, 'following': 12, 'created_at': '2019-08-24T00:00:00Z', 'email': 'private-value'})
            elif url.startswith(f'https://api.github.com/repos/{refresh.USER}/') and url.endswith('/languages'):
                body = json.dumps({'TypeScript': 20, 'CSS': 5})
            else:
                self.fail(f'Unexpected public-data URL: {url}')
            return io.BytesIO(body.encode())

        with patch.object(refresh.urllib.request, 'urlopen', side_effect=respond):
            refresh.main()
        result = json.loads(self.snapshot.read_text())
        self.assertEqual(len(seen), 104)
        self.assertEqual(len(result['repos']), 100)
        self.assertNotIn('project-0', [repo['name'] for repo in result['repos']])
        self.assertEqual(result['repos'][-1]['name'], 'last-project')
        self.assertEqual(set(result['repos'][0]), {'name', 'url', 'stars', 'forks', 'language'})
        self.assertEqual(result['account'], {'id': 54506603, 'followers': 4, 'following': 12, 'created_at': '2019-08-24T00:00:00Z'})
        self.assertEqual(result['languages'], {'TypeScript': 2000, 'CSS': 500})
        self.assertEqual(result['days'][0], {'date': '2026-01-01', 'level': 0, 'count': 0})
        self.assertEqual(result['days'][-1]['date'], (date(2026, 1, 1) + timedelta(days=299)).isoformat())
        self.assertEqual(result['contributions'], 600)
        self.assertEqual(result['source'], f'https://github.com/{refresh.USER}')
        self.assertFalse(self.snapshot.with_suffix('.tmp').exists())

    # Value: protects=the last usable snapshot survives a failed upstream request;
    # fails_when=a fetch failure truncates or replaces the existing snapshot;
    # why_new=only successful parsing was checked previously;
    # seam=none; no_claim=live network behavior (deterministic transport failures).
    def test_network_failure_keeps_previous_snapshot(self):
        for failure_stage in ('repositories', 'calendar'):
            with self.subTest(stage=failure_stage):
                responses = [URLError('offline')] if failure_stage == 'repositories' else [json.dumps([repository('one')]), URLError('offline')]
                with patch.object(refresh, 'fetch', side_effect=responses):
                    with self.assertRaises(URLError):
                        refresh.main()
                self.assert_preserved()

    # Value: protects=an incomplete calendar never replaces a valid existing snapshot;
    # fails_when=the minimum-calendar guard is removed or bypassed;
    # why_new=the existing parser sample has no persistence or partial-page assertion;
    # seam=none; no_claim=all possible upstream markup changes (short-page fixture).
    def test_short_calendar_keeps_previous_snapshot(self):
        with patch.object(refresh, 'fetch', side_effect=[json.dumps([]), calendar_html(length=299)]):
            with self.assertRaisesRegex(RuntimeError, 'Public calendar format changed'):
                refresh.main()
        self.assert_preserved()

    # Value: protects=the account identity before publication; fails_when=a different
    # account replaces the last valid snapshot; why_new=identity guard was added;
    # seam=none; no_claim=live identity-provider availability.
    def test_wrong_account_keeps_previous_snapshot(self):
        responses = [json.dumps([]), calendar_html(), json.dumps({'id': 100})]
        with patch.object(refresh, 'fetch', side_effect=responses):
            with self.assertRaisesRegex(RuntimeError, 'identity changed'):
                refresh.main()
        self.assert_preserved()

    # Value: protects=complete public language data and atomic snapshot preservation;
    # fails_when=rate limits or invalid byte counts publish partial totals;
    # why_new=language endpoints are new; seam=none; no_claim=live API reliability.
    def test_incomplete_language_data_keeps_previous_snapshot(self):
        prefix = [json.dumps([repository('one')]), calendar_html(), json.dumps({'id': 54506603})]
        for failure in (URLError('rate limit'), json.dumps({'TypeScript': -1})):
            with self.subTest(failure=str(failure)):
                with patch.object(refresh, 'fetch', side_effect=prefix+[failure]):
                    with self.assertRaises((URLError, ValueError)):
                        refresh.main()
                self.assert_preserved()

    # Value: protects=missing daily counts cannot silently become a partial snapshot;
    # fails_when=missing tooltips are ignored and incomplete totals are saved;
    # why_new=the existing parser check never exercises a missing tooltip;
    # seam=none; no_claim=live GitHub parsing (one missing-tooltip fixture).
    def test_calendar_with_missing_count_keeps_previous_snapshot(self):
        with patch.object(refresh, 'fetch', side_effect=[json.dumps([]), calendar_html(missing_count=True)]):
            with self.assertRaisesRegex(RuntimeError, 'Public calendar format changed'):
                refresh.main()
        self.assert_preserved()

    # Value: protects=the pagination cap fails closed without publishing partial totals;
    # fails_when=cap exhaustion is treated as successful repository enumeration;
    # why_new=no previous check covers capped API pagination;
    # seam=none; no_claim=live repository availability (full-page fixture).
    def test_pagination_exhaustion_keeps_previous_snapshot(self):
        page = json.dumps([repository(f'project-{i}') for i in range(100)])
        with patch.object(refresh, 'fetch', return_value=page) as fetch:
            with self.assertRaisesRegex(RuntimeError, 'Repository pagination limit reached'):
                refresh.main()
        self.assertEqual(fetch.call_count, 19)
        self.assertTrue(all('/repos?' in call.args[0] for call in fetch.call_args_list))
        self.assert_preserved()


if __name__ == '__main__':
    unittest.main()
