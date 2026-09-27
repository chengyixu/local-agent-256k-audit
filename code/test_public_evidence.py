import importlib.util
import unittest
import json

def export(summary):
    assert importlib.util.find_spec('public_evidence') is not None, 'Missing whitelist-only public evidence exporter'
    return importlib.import_module('public_evidence').public_row('fixture',summary)

class PublicEvidenceTests(unittest.TestCase):
    def test_omits_private_text_paths_credentials_and_unknown_fields(self):
        row=export({'completed':True,'elapsed_s':10.5,'workspace':'/private/secret/repo',
                    'api_key':'SECRET','task_quality_evidence':'PRIVATE SOURCE','arbitrary':'SECRET',
                    'turns':[{'usage':{'input':256222,'cacheRead':0},'ttft_s':5.0}],
                    'final_visible_stream_tps':30.0})
        encoded=json.dumps(row)
        self.assertNotIn('SECRET',encoded);self.assertNotIn('/private',encoded);self.assertNotIn('PRIVATE SOURCE',encoded)
        self.assertEqual(row['initial_input_tokens'],256222);self.assertEqual(row['visible_stream_tps'],30.0)
        self.assertIsNone(row['visible_cycle_tps'])

    def test_rejects_non_numeric_metrics_instead_of_exporting_arbitrary_text(self):
        with self.assertRaises(ValueError):export({'elapsed_s':'SECRET'})
        with self.assertRaises(ValueError):export({'elapsed_s':float('nan')})
        with self.assertRaises(ValueError):export({'elapsed_s':True})

    def test_failure_and_unknown_quality_never_become_a_pass(self):
        row=export({'completed':False,'timed_out':True,'elapsed_s':3600,'task_quality_verified':False})
        self.assertFalse(row['completed']);self.assertFalse(row['bounded_quality_pass'])
        self.assertIsNone(row['visible_stream_tps']);self.assertTrue(row['timed_out'])
        self.assertIsNone(export({})['bounded_quality_pass'])
