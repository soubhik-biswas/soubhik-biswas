"""Boundary contracts for public analytics and truthful chart output."""
import copy
import importlib.util
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('render_profile', Path(__file__).with_name('render-profile.py'))
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)


class AnalyticsTests(unittest.TestCase):
    def capture_dashboard(self, data):
        with patch.object(render, 'DATA', data), patch.object(render, 'svg') as output:
            render.dashboard()
        return ET.fromstring('<svg>'+output.call_args.args[5]+'</svg>')

    # Value: protects=streak reset and 7/30/91-day boundaries; fails_when=zero days
    # extend streaks or older contributions enter recent windows; why_new=derived
    # metrics had no fixtures; seam=none; no_claim=upstream calendar accuracy.
    def test_interrupted_activity_and_window_boundaries(self):
        counts=[0]*91
        counts[0],counts[60],counts[61]=50,90,11
        counts[-9:]=[3,4,0,1,2,3,4,5,6]
        with patch.object(render,'DATA',{'days':[{'count':n} for n in counts]}):
            metrics=render.activity_metrics()
        self.assertEqual(metrics,{'active':11,'longest':6,'last30':39,'last7':21,
                                 'weeks':[50,0,0,0,0,0,0,0,101,0,0,7,21]})

    # Value: protects=zero activity remains visually zero; fails_when=minimum-height
    # bars create recorded activity in empty weeks; why_new=review found that defect;
    # seam=existing SVG output boundary; no_claim=pixel appearance or live counts.
    def test_empty_weeks_do_not_draw_activity_bars(self):
        data=copy.deepcopy(render.DATA)
        data['days']=[{'date':'2026-01-01','count':0} for _ in range(91)]
        data['days'][-1]['count']=8
        data['contributions']=8
        root=self.capture_dashboard(data)
        bars=[e for e in root.iter('rect') if e.get('class')=='vertical-bar']
        self.assertEqual(len(bars),1)
        self.assertEqual(float(bars[0].get('height')),78)

    # Value: protects=language shares retain all bytes and tolerate empty repositories;
    # fails_when=small languages disappear or zero bytes divide by zero; why_new=the
    # composition chart is new; seam=existing output boundary; no_claim=proficiency.
    def test_language_composition_preserves_other_and_zero_bytes(self):
        data=copy.deepcopy(render.DATA)
        data['languages']={'TypeScript':50,'CSS':20,'HTML':10,'JavaScript':10,'Astro':5,'Python':3,'Shell':2}
        root=self.capture_dashboard(data)
        labels=[e.text for e in root.iter('text')]
        self.assertEqual(labels[labels.index('Other')+1],'5.0%')
        segments=[e for e in root.iter('rect') if e.get('y')=='88' and e.get('height')=='11']
        self.assertAlmostEqual(sum(float(e.get('width')) for e in segments),440)
        for languages in ({},{'TypeScript':0}):
            data['languages']=languages
            root=self.capture_dashboard(data)
            segments=[e for e in root.iter('rect') if e.get('y')=='88' and e.get('height')=='11']
            self.assertEqual(sum(float(e.get('width')) for e in segments),0)


if __name__=='__main__':
    unittest.main()
