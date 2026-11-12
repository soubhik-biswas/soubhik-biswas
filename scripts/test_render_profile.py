"""Boundary contracts for public analytics and truthful chart output."""
import copy
import importlib.util
import unittest
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('render_profile', Path(__file__).with_name('render-profile.py'))
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)


def daily_rows(counts):
    first = date(2026, 1, 5)
    return [{'date': (first + timedelta(days=i)).isoformat(), 'count': count} for i, count in enumerate(counts)]


def marks(root, name):
    return [element for element in root.iter('rect') if element.get('class') == name]


class AnalyticsTests(unittest.TestCase):
    def capture_panel(self, renderer, data, **patches):
        with patch.object(render, 'DATA', data), patch.object(render, 'panel') as output:
            for name, value in patches.items():
                stack = patch.object(render, name, value)
                stack.start()
                self.addCleanup(stack.stop)
            renderer()
        return ET.fromstring('<svg>' + output.call_args.args[5] + '</svg>')

    # Value: protects=missing commit data stays distinct from zero and quiet days
    # stay out of the log; fails_when=dashes become zeros or empty rows return.
    def test_daily_activity_lists_active_days_and_keeps_unavailable_commit_data_distinct(self):
        days = [
            {'date': '2025-12-31', 'count': 0},
            {'date': '2026-01-31', 'count': 5},
            {'date': '2026-02-01', 'count': 0},
            {'date': '2026-02-02', 'count': 10},
            {'date': '2026-02-03', 'count': 4},
        ]
        commits = {
            'from': '2026-01-31',
            'to': '2026-02-02',
            'repositories': 1,
            'days': {'2026-01-31': {'commits': 2, 'additions': 14, 'deletions': 3}},
        }
        with patch.object(render, 'DATA', {'days': days}), patch.object(render, 'COMMIT_ACTIVITY', commits):
            activity = render.daily_activity()
            monthly = render.monthly_table()
        self.assertIn('<details open>\n<summary>February 2026: 14 contributions', activity)
        self.assertIn('<details>\n<summary>January 2026: 5 contributions', activity)
        self.assertNotIn('December 2025', activity)
        self.assertIn('| Jan 31 | 5 | 2 | 14 | 3 |', activity)
        self.assertIn('| Feb 2 | 10 | 0 | 0 | 0 |', activity)
        self.assertIn('| Feb 3 | 4 | — | — | — |', activity)
        self.assertNotIn('| Feb 1 |', activity)
        self.assertIn('| January 2026 | 5 | 1 | 2 | 14 | 3 |', monthly)
        self.assertIn('| February 2026 | 14 | 2 | — | — | — |', monthly)
        self.assertIn('| December 2025 | 0 | 0 | — | — | — |', monthly)

    # Value: protects=streak reset and 7/30/91-day boundaries; fails_when=zero days
    # extend streaks or older contributions enter recent windows.
    def test_interrupted_activity_and_window_boundaries(self):
        counts = [0] * 91
        counts[0], counts[60], counts[61] = 50, 90, 11
        counts[-9:] = [3, 4, 0, 1, 2, 3, 4, 5, 6]
        with patch.object(render, 'DATA', {'days': daily_rows(counts)}):
            metrics = render.activity_metrics()
        self.assertEqual(metrics, {
            'active': 11, 'longest': 6, 'last30': 39, 'previous30': 90,
            'active30': 9, 'previous_active30': 1,
            'weeks': [50, 0, 0, 0, 0, 0, 0, 0, 101, 0, 0, 7, 21],
            'weekdays': [1, 1, 1, 1, 2, 3, 2],
        })

    # Value: protects=zero activity remains visually zero; fails_when=minimum-height
    # bars or bubbles appear for days and weeks without contributions.
    def test_empty_periods_do_not_draw_marks(self):
        data = copy.deepcopy(render.DATA)
        data['days'] = daily_rows([0] * 90 + [8])
        data['contributions'] = 8
        root = self.capture_panel(render.hero, data)
        bars = marks(root, 'weekly-bar')
        self.assertEqual(len(bars), 1)
        self.assertEqual(float(bars[0].get('height')), 52)
        root = self.capture_panel(render.pulse, data)
        self.assertEqual(len(marks(root, 'day-bar')), 1)
        self.assertEqual(len(marks(root, 'period-bar')), 1)
        root = self.capture_panel(render.rhythm, data)
        self.assertEqual(len([e for e in root.iter('circle') if e.get('class') == 'bubble']), 1)

    # Value: protects=bar heights stay proportional to the round axis maximum;
    # fails_when=a bar is scaled to the peak instead of the labelled axis.
    def test_daily_bars_scale_to_the_labelled_axis(self):
        data = copy.deepcopy(render.DATA)
        data['days'] = daily_rows([0] * 89 + [50, 200])
        root = self.capture_panel(render.pulse, data)
        heights = sorted(float(bar.get('height')) for bar in marks(root, 'day-bar'))
        self.assertEqual(render.nice_ceiling(200), (200, 50))
        self.assertAlmostEqual(heights[1], 222)
        self.assertAlmostEqual(heights[0], 55.5)

    def test_axis_maximum_is_round_and_never_below_the_peak(self):
        self.assertEqual(render.nice_ceiling(941), (1000, 250))
        self.assertEqual(render.nice_ceiling(1976), (2000, 500))
        self.assertEqual(render.nice_ceiling(3), (3, 1))
        self.assertEqual(render.nice_ceiling(0), (1, 1))
        for peak in (1, 7, 99, 101, 629229, 12345678):
            ceiling, step = render.nice_ceiling(peak)
            self.assertGreaterEqual(ceiling, peak)
            self.assertLess(ceiling - peak, step)

    # Value: protects=no multiplier is claimed from a zero base;
    # fails_when=division by zero or an infinite ratio reaches the panel.
    def test_momentum_never_claims_a_ratio_from_zero(self):
        self.assertEqual(render.momentum(3383, 415), ('8.2×', 'the previous 30 days'))
        self.assertEqual(render.momentum(50, 100)[0], '0.5×')
        self.assertEqual(render.momentum(4150, 100)[0], '42×')
        self.assertEqual(render.momentum(12, 0)[0], 'New')
        self.assertEqual(render.momentum(0, 0)[0], '0')

    def test_rolling_average_uses_only_days_that_exist(self):
        self.assertEqual(render.rolling_average([7, 0, 0, 0, 0, 0, 0, 14]), [1, 1, 1, 1, 1, 1, 1, 2])
        self.assertEqual(len(render.rolling_average([1] * 200)), 91)

    # Value: protects=language shares retain all bytes and tolerate empty repositories;
    # fails_when=small languages disappear or zero bytes divide by zero.
    def test_language_composition_preserves_other_and_zero_bytes(self):
        data = copy.deepcopy(render.DATA)
        data['languages'] = {'TypeScript': 50, 'CSS': 20, 'HTML': 10, 'JavaScript': 10, 'Astro': 5, 'Python': 3, 'Shell': 2}
        root = self.capture_panel(render.codebase, data)
        labels = [e.text for e in root.iter('text')]
        self.assertEqual(labels[labels.index('Other') + 1], '5.0%')
        widths = [float(bar.get('width')) for bar in marks(root, 'language-bar')]
        self.assertEqual(len(widths), 6)
        self.assertAlmostEqual(widths[0], 240 * .5)
        for languages in ({}, {'TypeScript': 0}):
            data['languages'] = languages
            data['repos'] = [{'name': 'empty', 'languages': languages}]
            root = self.capture_panel(render.codebase, data)
            self.assertEqual(marks(root, 'language-bar'), [])
            self.assertEqual(marks(root, 'cell'), [])

    # Value: protects=treemap blocks stay proportional to bytes and inside the plot;
    # fails_when=a block is dropped, overlaps the edge or changes relative area.
    def test_treemap_areas_are_proportional_and_fill_the_plot(self):
        items = [('a', 46), ('b', 33), ('c', 12), ('d', 4), ('e', 3), ('f', 2)]
        cells = render.squarify(items, 0, 62, 436, 258)
        self.assertEqual([key for key, *_ in cells], [key for key, _ in items])
        for (key, x, y, w, h), (_, value) in zip(cells, items):
            self.assertAlmostEqual(w * h, 436 * 258 * value / 100, places=6)
            self.assertGreaterEqual(x, -1e-9)
            self.assertGreaterEqual(y, 62 - 1e-9)
            self.assertLessEqual(x + w, 436 + 1e-9)
            self.assertLessEqual(y + h, 62 + 258 + 1e-9)
        self.assertEqual(render.squarify([], 0, 0, 10, 10), [])

    def test_weekly_commit_bars_match_the_snapshot(self):
        data = {'days': daily_rows([1] * 91)}
        commits = {'from': '2026-01-05', 'to': '2026-04-05', 'repositories': 2, 'days': {
            '2026-01-05': {'commits': 2, 'additions': 300, 'deletions': 100},
            '2026-01-11': {'commits': 1, 'additions': 100, 'deletions': 0},
            '2026-01-12': {'commits': 4, 'additions': 0, 'deletions': 800},
        }}
        with patch.object(render, 'DATA', data), patch.object(render, 'COMMIT_ACTIVITY', commits):
            weeks = render.weekly_commits()
            self.assertEqual(render.commit_totals(), {'commits': 7, 'additions': 400, 'deletions': 900})
        self.assertEqual(len(weeks), 13)
        self.assertEqual((weeks[0]['commits'], weeks[0]['additions'], weeks[0]['deletions']), (3, 400, 100))
        self.assertEqual((weeks[1]['commits'], weeks[1]['additions'], weeks[1]['deletions']), (4, 0, 800))
        root = self.capture_panel(render.rhythm, data, COMMIT_ACTIVITY=commits)
        added, removed = marks(root, 'added-bar'), marks(root, 'removed-bar')
        self.assertEqual((len(added), len(removed)), (1, 2))
        self.assertAlmostEqual(float(added[0].get('height')) * 2, max(float(bar.get('height')) for bar in removed))

    def test_readme_sections_are_replaced_exactly_once(self):
        names = [name for name, _ in render.SECTIONS]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(len(render.PANEL_NAMES), 8 + len(render.ART))


if __name__ == '__main__':
    unittest.main()
