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


class AnalyticsTests(unittest.TestCase):
    def capture_panel(self, renderer, data):
        with patch.object(render, 'DATA', data), patch.object(render, 'svg') as output:
            renderer()
        return ET.fromstring('<svg>'+output.call_args.args[5]+'</svg>')

    # Value: protects=streak reset and 7/30/91-day boundaries; fails_when=zero days
    # extend streaks or older contributions enter recent windows; why_new=derived
    # metrics had no fixtures; seam=none; no_claim=upstream calendar accuracy.
    def test_interrupted_activity_and_window_boundaries(self):
        counts=[0]*91
        counts[0],counts[60],counts[61]=50,90,11
        counts[-9:]=[3,4,0,1,2,3,4,5,6]
        with patch.object(render, 'DATA', {'days': daily_rows(counts)}):
            metrics=render.activity_metrics()
        self.assertEqual(metrics, {
            'active': 11, 'longest': 6, 'last30': 39, 'previous30': 90,
            'active30': 9, 'previous_active30': 1,
            'weeks': [50, 0, 0, 0, 0, 0, 0, 0, 101, 0, 0, 7, 21],
            'weekdays': [1, 1, 1, 1, 2, 3, 2],
        })

    # Value: protects=zero activity remains visually zero; fails_when=minimum-height
    # bars create recorded activity in empty weeks; why_new=review found that defect;
    # seam=existing SVG output boundary; no_claim=pixel appearance or live counts.
    def test_empty_weeks_do_not_draw_activity_bars(self):
        data=copy.deepcopy(render.DATA)
        data['days']=daily_rows([0]*90+[8])
        data['contributions']=8
        root=self.capture_panel(render.hero, data)
        bars=[e for e in root.iter('rect') if e.get('class')=='weekly-bar']
        self.assertEqual(len(bars),1)
        self.assertEqual(float(bars[0].get('height')),92)

    # Value: protects=language shares retain all bytes and tolerate empty repositories;
    # fails_when=small languages disappear or zero bytes divide by zero; why_new=the
    # composition chart is new; seam=existing output boundary; no_claim=proficiency.
    def test_language_composition_preserves_other_and_zero_bytes(self):
        data=copy.deepcopy(render.DATA)
        data['languages']={'TypeScript':50,'CSS':20,'HTML':10,'JavaScript':10,'Astro':5,'Python':3,'Shell':2}
        root=self.capture_panel(render.codebase, data)
        labels=[e.text for e in root.iter('text')]
        self.assertEqual(labels[labels.index('Other')+1],'5.0%')
        segments=[e for e in root.iter('rect') if e.get('y')=='80' and e.get('height')=='12']
        self.assertAlmostEqual(sum(float(e.get('width')) for e in segments),435)
        for languages in ({},{'TypeScript':0}):
            data['languages']=languages
            root=self.capture_panel(render.codebase, data)
            segments=[e for e in root.iter('rect') if e.get('y')=='80' and e.get('height')=='12']
            self.assertEqual(sum(float(e.get('width')) for e in segments),0)

    def test_featured_language_strips_use_their_own_repository_totals(self):
        data = copy.deepcopy(render.DATA)
        data['languages'] = {'TypeScript': 900, 'CSS': 100}
        data['repos'] = [
            {'name': 'passlore', 'languages': {'TypeScript': 3, 'CSS': 2}},
            {'name': 'awaketab', 'languages': {}},
            {'name': 'bucketpeek', 'languages': {'TypeScript': 10}},
        ]
        root = self.capture_panel(render.codebase, data)
        labels = [element.text for element in root.iter('text')]
        self.assertIn('Passlore', labels)
        self.assertIn('TypeScript 60%', labels)
        self.assertNotIn('AwakeTab', labels)
        self.assertNotIn('Shareroom', labels)
        self.assertNotIn('BucketPeek', labels)
        self.assertNotIn('TypeScript 100%', labels)
        segments = [float(element.get('width')) for element in root.iter('rect') if element.get('y') == '107']
        self.assertEqual(segments, [261.0, 174.0])


if __name__=='__main__':
    unittest.main()
