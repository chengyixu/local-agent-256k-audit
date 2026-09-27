import unittest
import importlib.util

def evaluate(*args):
    assert importlib.util.find_spec('task_d_quality') is not None, 'Missing Task D evidence evaluator'
    return importlib.import_module('task_d_quality').evaluate(*args)

CASES=[{'max_attempts':3,'initial_delay_s':1,'max_delay_s':8,'delays':[1,2]},
       {'max_attempts':5,'initial_delay_s':10,'max_delay_s':2,'delays':[2,2,2,2]},
       {'max_attempts':1,'initial_delay_s':0.1,'max_delay_s':2,'delays':[]}]

class QualityTests(unittest.TestCase):
    def fixture(self):
        import json
        command='cd /checkout && .venv/bin/python -c "print(123)"\n'
        answer={'receipts':['A','B','C'],'cases':json.loads(json.dumps(CASES)),'retryable_statuses':{'429':True,'401':False},'inspected_file':'src/KK_LLM/retry.py','verification_command':command}
        rows=[{'event':{'type':'tool_execution_start','toolName':'bash','toolCallId':'x','args':{'command':command}}},
              {'event':{'type':'tool_execution_end','toolName':'bash','toolCallId':'x','isError':False}},
              {'event':{'type':'message_end','message':{'role':'assistant','stopReason':'stop','content':[{'type':'text','text':json.dumps(answer)}]}}}]
        return rows,answer

    def test_validates_unmodified_final_json_and_exact_successful_command(self):
        rows,_=self.fixture();out=evaluate(rows,['A','B','C'])
        self.assertTrue(out['strict_json_format']);self.assertTrue(out['reported_values_correct']);self.assertTrue(out['verification_command_exact'])
        self.assertNotIn('task_quality_verified',out) # actual execution semantics require independent source review

    def test_rejects_fences_rewritten_command_and_wrong_values(self):
        import json
        rows,answer=self.fixture();rows[-1]['event']['message']['content'][0]['text']='```json\n'+json.dumps(answer)+'\n```'
        self.assertFalse(evaluate(rows,['A','B','C'])['strict_json_format'])
        answer['verification_command']='equivalent but never executed';answer['cases']=[{'delays':[1,2,4]}]
        rows[-1]['event']['message']['content'][0]['text']=json.dumps(answer)
        out=evaluate(rows,['A','B','C']);self.assertFalse(out['verification_command_exact']);self.assertFalse(out['reported_values_correct'])

    def test_failed_command_and_missing_answer_cannot_pass(self):
        rows,_=self.fixture();rows[1]['event']['isError']=True
        self.assertFalse(evaluate(rows,['A','B','C'])['verification_command_exact'])
        rows[-1]['event']['message']['stopReason']='length'
        self.assertFalse(evaluate(rows,['A','B','C'])['strict_json_format'])

    def test_boolean_numbers_and_extra_keys_not_accepted(self):
        import json
        rows,answer=self.fixture();answer['cases'][0]['initial_delay_s']=True
        rows[-1]['event']['message']['content'][0]['text']=json.dumps(answer)
        self.assertFalse(evaluate(rows,['A','B','C'])['reported_values_correct'])
