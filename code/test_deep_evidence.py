import importlib.util
import unittest
from pathlib import Path


class EvidenceTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('deep_evidence'),'Evidence parser missing')
        import deep_evidence
        return deep_evidence

    def test_failed_wrong_path_read_is_not_dossier_recovery(self):
        rows=[{'event':{'type':'tool_execution_start','toolCallId':'a','toolName':'read','args':{'path':'/lab/private-corpus/deep-task/src/KK_LLM/retry.py'}}},
              {'event':{'type':'tool_execution_end','toolCallId':'a','toolName':'read','isError':True}},
              {'event':{'type':'tool_execution_start','toolCallId':'b','toolName':'read','args':{'path':'/repo/src/KK_LLM/retry.py'}}},
              {'event':{'type':'tool_execution_end','toolCallId':'b','toolName':'read','isError':False}}]
        x=self.module().extract(rows,[],Path('/repo'),Path('/lab/private-corpus'))
        self.assertTrue(x['dossier_access_attempted'])
        self.assertFalse(x['dossier_access_succeeded'])
        self.assertTrue(x['read_repository_file'])

    def test_successful_dossier_read_disqualifies(self):
        rows=[{'event':{'type':'tool_execution_start','toolCallId':'x','toolName':'read','args':{'path':'/lab/private-corpus/deep-task.txt'}}},
              {'event':{'type':'tool_execution_end','toolCallId':'x','toolName':'read','isError':False}}]
        self.assertTrue(self.module().extract(rows,[],Path('/repo'),Path('/lab/private-corpus'))['dossier_access_succeeded'])

    def test_length_cutoff_can_recover_receipts_but_not_complete_answer(self):
        rows=[{'event':{'type':'message_end','message':{'role':'assistant','stopReason':'length','content':[{'type':'text','text':'AAA BBB CCC unfinished'}]}}}]
        x=self.module().extract(rows,['AAA','BBB','CCC'],Path('/repo'),Path('/lab/private-corpus'))
        self.assertTrue(x['receipts_recovered'])
        self.assertFalse(x['answer_complete'])

if __name__=='__main__':unittest.main()
