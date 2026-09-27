import unittest
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import pi_measure
from pi_measure import summarize


def event(t, kind, **data):
    return {'t_s': t, 'event': {'type': kind, **data}}


class MeasureTests(unittest.TestCase):
    def test_reports_prefill_and_task_time_not_just_decode(self):
        rows = [event(0, 'message_start', message={'role':'assistant'}),
                event(10, 'message_update', assistantMessageEvent={'type':'text_delta','delta':'abc'}),
                event(15, 'message_end', message={'role':'assistant','usage':{'input':123,'output':100},'stopReason':'stop'}),
                event(17, 'agent_settled')]
        out = summarize(rows, 20, 0, False)
        self.assertEqual(out['turns'][0]['ttft_s'], 10)
        self.assertEqual(out['turns'][0]['decode_tps'], 20)
        self.assertAlmostEqual(out['turns'][0]['request_tps'],100/15)
        self.assertEqual(out['task_generated_tps'],5)
        self.assertIsNone(out['visible_text_tps'])

    def test_full_turn_timing_includes_request_preflight_before_stream_start(self):
        rows=[event(0,'turn_start'),event(2,'message_start',message={'role':'assistant'}),
              event(3,'message_update',assistantMessageEvent={'type':'text_delta','delta':'answer'}),
              event(5,'message_end',message={'role':'assistant','usage':{'output':40},'stopReason':'stop'})]
        turn=summarize(rows,6,0,False)['turns'][0]
        self.assertEqual(turn.get('turn_start_s'),0)
        self.assertEqual(turn.get('inference_cycle_s'),5)
        self.assertEqual(turn.get('inference_cycle_tps'),8)
        self.assertEqual(turn['request_s'],3)

    def test_does_not_count_empty_tool_delta_as_first_token(self):
        rows = [event(0,'message_start',message={'role':'assistant'}),
                event(1,'message_update',assistantMessageEvent={'type':'toolcall_delta','delta':''}),
                event(2,'message_update',assistantMessageEvent={'type':'toolcall_delta','delta':'{"path"'}),
                event(3,'message_end',message={'role':'assistant','usage':{'output':10},'stopReason':'toolUse'})]
        self.assertEqual(summarize(rows,4,0,False)['turns'][0]['ttft_s'],2)

    def test_tool_only_chunks_do_not_prove_backend_decode_speed(self):
        rows = [event(0,'message_start',message={'role':'assistant'}),
                event(10,'message_update',assistantMessageEvent={'type':'toolcall_delta','delta':'{"path":"src"}'}),
                event(10.2,'message_end',message={'role':'assistant','usage':{'output':100},'stopReason':'toolUse'})]
        out=summarize(rows,11,0,False)
        self.assertIsNone(out['turns'][0]['decode_tps'])
        self.assertAlmostEqual(out['turns'][0]['request_tps'],100/10.2)

    def test_one_token_length_cutoff_burst_is_not_decode_speed_evidence(self):
        rows=[event(0,'message_start',message={'role':'assistant'}),
              event(8,'message_update',assistantMessageEvent={'type':'thinking_delta','delta':'Now'}),
              event(8.005,'message_end',message={'role':'assistant','usage':{'output':1,'reasoning':1},'stopReason':'length'})]
        out=summarize(rows,8.1,0,False)
        self.assertIsNone(out['turns'][0]['decode_tps'])
        self.assertEqual(out['turns'][0]['decode_timing_warning'],'burst_or_buffered')
        self.assertEqual(out['turns'][0]['output_tokens'],1)
        self.assertFalse(out['completed'])

    def test_unknown_usage_never_becomes_zero_or_chunk_token_count(self):
        rows = [event(0,'message_start',message={'role':'assistant'}),
                event(1,'message_update',assistantMessageEvent={'type':'text_delta','delta':'hello'}),
                event(2,'message_end',message={'role':'assistant','stopReason':'stop'})]
        out=summarize(rows,3,0,False)
        self.assertIsNone(out['turns'][0]['decode_tps'])
        self.assertIsNone(out['total_output_tokens'])

    def test_timeout_or_compaction_cannot_pass(self):
        out=summarize([event(0,'compaction_start'), event(1,'agent_settled')], 2,143,True)
        self.assertFalse(out['completed'])
        self.assertEqual(out['compactions'],1)
        self.assertEqual(out['incomplete_turns'],0)

    def test_runner_closes_child_stdin_when_parent_input_is_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); script=root/'pi'
            script.write_text('#!'+sys.executable+'\nimport sys,json\nfrom pathlib import Path\nsys.stdin.read()\n'
                'Path("child-args.json").write_text(json.dumps(sys.argv[1:]))\n'
                'events=[{"type":"message_start","message":{"role":"assistant"}},'
                '{"type":"message_end","message":{"role":"assistant","usage":{"output":1},"stopReason":"stop"}},'
                '{"type":"agent_settled"}]\n'
                'for e in events: print(json.dumps(e),flush=True)\n')
            script.chmod(0o755); (root/'prompt.txt').write_text('fixture task')
            env={**os.environ,'PATH':str(root)+os.pathsep+os.environ['PATH']}
            cmd=[sys.executable,str(Path(__file__).with_name('pi_measure.py')),
                 '--workspace',tmp,'--provider','fixture','--model','fixture',
                 '--prompt',str(root/'prompt.txt'),'--output',str(root/'result'),'--timeout','10']
            p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
            try:
                p.wait(timeout=25)
                result=json.loads((root/'result.summary.json').read_text())
                self.assertTrue(result['completed'],'Child inherited open stdin and never began its task')
                self.assertEqual(result['extensions'],'disabled for controlled comparison')
                self.assertIn('--no-extensions',json.loads((root/'child-args.json').read_text()))
                enabled=subprocess.run(cmd+['--enable-extensions'],stdin=subprocess.DEVNULL,
                                       capture_output=True,env=env,timeout=25)
                self.assertEqual(enabled.returncode,0,enabled.stderr.decode())
                enabled_result=json.loads((root/'result.summary.json').read_text())
                self.assertTrue(enabled_result['completed'])
                self.assertEqual(enabled_result['extensions'],
                                 'enabled via normal Pi discovery; actual loading requires trace review')
                self.assertNotIn('--no-extensions',json.loads((root/'child-args.json').read_text()))
            finally:
                if p.poll() is None:p.kill();p.wait()
                p.stdin.close();p.stdout.close();p.stderr.close()

    def test_large_prompt_uses_pi_attachment_not_os_argument_payload(self):
        self.assertTrue(hasattr(pi_measure,'command_args'),'Runner needs a file-attachment command path')
        with tempfile.TemporaryDirectory() as tmp:
            prompt=Path(tmp)/'corpus.txt';prompt.write_text('x'*1000000)
            args=SimpleNamespace(tools='read,bash,edit,write',provider='local',model='model',thinking='low',prompt=str(prompt),prompt_file=True)
            cmd=pi_measure.command_args(args)
            self.assertEqual(cmd[-1],'@'+str(prompt.resolve()))
            self.assertLess(sum(map(len,cmd)),10000)
            self.assertIn('read,bash,edit,write',cmd)
            self.assertNotIn('--approve',cmd)
            args.approve=True
            self.assertIn('--approve',pi_measure.command_args(args))
            args.task_instruction='Use the current repository, not the attachment directory.'
            self.assertEqual(pi_measure.command_args(args)[-2:],['@'+str(prompt.resolve()),args.task_instruction])
            args.task_instruction=None
            args.prompt_file=False; prompt.write_text('small task')
            self.assertEqual(pi_measure.command_args(args)[-1],'small task')

    def test_full_extensions_are_explicit_opt_in_without_changing_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            prompt=Path(tmp)/'prompt.txt';prompt.write_text('Read the isolated checkout')
            args=SimpleNamespace(tools='read,bash,edit,write',provider='local',model='model',
                                 thinking='low',prompt=str(prompt),prompt_file=True)
            controlled=pi_measure.command_args(args)
            self.assertIn('--no-extensions',controlled)
            args.enable_extensions=True
            production=pi_measure.command_args(args)
            self.assertNotIn('--no-extensions',production)
            self.assertEqual(production,[v for v in controlled if v!='--no-extensions'])
            args.enable_extensions=False
            self.assertEqual(pi_measure.command_args(args),controlled)
            args.enable_extensions=True
            args.default_tools=True
            discovered=pi_measure.command_args(args)
            self.assertNotIn('--tools',discovered)
            self.assertNotIn('read,bash,edit,write',discovered)
            self.assertNotIn('--no-extensions',discovered)

    def test_incomplete_generation_reported(self):
        out=summarize([event(0,'message_start',message={'role':'assistant'})],5,143,True)
        self.assertEqual(out['incomplete_turns'],1)
        self.assertIsNone(out['task_generated_tps'])


if __name__ == '__main__': unittest.main()
