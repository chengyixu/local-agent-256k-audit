"""Measure timestamped Pi JSON events without conflating chunks with tokens."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import time


def summarize(rows, elapsed, returncode, timed_out):
    turns, current = [], None
    turn_start = None
    tool_calls, tool_errors, compactions, retries = 0, 0, 0, 0
    settled = False
    for row in rows:
        t, e = row['t_s'], row['event']
        kind = e.get('type')
        if kind == 'turn_start':
            turn_start = t
        elif kind == 'message_start' and e.get('message', {}).get('role') == 'assistant':
            current = {'start_s': t, 'turn_start_s': turn_start, 'first_delta_s': None, 'text_chars': 0,
                       'thinking_chars': 0, 'tool_chars': 0}
        elif kind == 'message_update' and current is not None:
            part = e.get('assistantMessageEvent', {})
            delta = part.get('delta')
            tag = part.get('type')
            field = {'text_delta':'text_chars','thinking_delta':'thinking_chars','toolcall_delta':'tool_chars'}.get(tag)
            if field and isinstance(delta, str) and delta:
                if current['first_delta_s'] is None: current['first_delta_s'] = t
                current[field] += len(delta)
        elif kind == 'message_end' and e.get('message', {}).get('role') == 'assistant':
            msg = e['message']
            if current is None:
                current = {'start_s':None, 'first_delta_s':None}
            usage = msg.get('usage', {})
            tokens = usage.get('output')
            tokens = tokens if isinstance(tokens,(int,float)) and tokens > 0 else None
            first, start = current['first_delta_s'], current['start_s']
            decode = t-first if first is not None else None
            duration = t-start if start is not None else None
            cycle_start = current.get('turn_start_s')
            cycle = t-cycle_start if cycle_start is not None else None
            current.update(end_s=t, usage=usage, output_tokens=tokens, stop_reason=msg.get('stopReason'),
                           inference_cycle_s=cycle,
                           inference_cycle_tps=tokens/cycle if tokens and cycle and cycle>0 else None,
                           request_scope='assistant stream start to end; inference_cycle includes earlier turn/preflight',
                           ttft_s=first-start if first is not None and start is not None else None,
                           request_s=duration, decode_s=decode,
                           decode_tps=tokens/decode if tokens and decode is not None and decode>=.1 and msg.get('stopReason')!='toolUse' else None,
                           request_tps=tokens/duration if tokens and duration and duration>0 else None,
                           decode_timing_warning=('tool_parser_timing_not_backend_decode' if msg.get('stopReason')=='toolUse'
                                                  else 'burst_or_buffered' if decode is not None and decode < .1 else None))
            turns.append(current); current = None
        elif kind == 'tool_execution_start': tool_calls += 1
        elif kind == 'tool_execution_end' and e.get('isError'): tool_errors += 1
        elif kind == 'compaction_start': compactions += 1
        elif kind == 'auto_retry_start': retries += 1
        elif kind == 'agent_settled': settled = True
    all_known = bool(turns) and all(t['output_tokens'] is not None for t in turns)
    total = sum(t['output_tokens'] for t in turns) if all_known else None
    return {'turns':turns, 'elapsed_s':elapsed, 'returncode':returncode, 'timed_out':timed_out,
            'tool_calls':tool_calls,'tool_errors':tool_errors,'compactions':compactions,'retries':retries,
            'incomplete_turns':int(current is not None),
            'total_output_tokens':total,
            'task_generated_tps':total/elapsed if total is not None and elapsed>0 and current is None else None,
            'visible_text_tps':None,
            'token_scope':'provider-reported completion tokens (may include reasoning and tool syntax); not visible-text TPS',
            'completed':settled and returncode==0 and not timed_out and current is None and bool(turns)
                        and turns[-1]['stop_reason'] not in ('error','aborted','length')}


def command_args(args):
    prompt = ('@'+str(Path(args.prompt).resolve())) if args.prompt_file else Path(args.prompt).read_text()
    return ['pi','--offline',
            *([] if getattr(args,'enable_extensions',False) else ['--no-extensions']),
            '--mode','json','--no-session',
            *([] if getattr(args,'default_tools',False) else ['--tools',args.tools]),
            '--provider',args.provider,'--model',args.model,'--thinking',args.thinking,
            *(['--approve'] if getattr(args,'approve',False) else []),prompt,
            *([args.task_instruction] if getattr(args,'task_instruction',None) else [])]


def run(args):
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True,exist_ok=True)
    cmd = command_args(args)
    env = os.environ.copy()
    env.update(NO_PROXY='127.0.0.1,localhost',no_proxy='127.0.0.1,localhost',PI_TELEMETRY='0')
    if args.agent_dir: env['PI_CODING_AGENT_DIR'] = str(Path(args.agent_dir).resolve())
    start = time.monotonic(); rows = []; timed_out=False
    with output.with_suffix('.stderr').open('wb') as err, output.with_suffix('.events.jsonl').open('w') as raw:
        proc = subprocess.Popen(cmd,cwd=args.workspace,env=env,stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE,stderr=err,start_new_session=True)
        sel = selectors.DefaultSelector(); sel.register(proc.stdout,selectors.EVENT_READ); buf=b''
        try:
            while True:
                if time.monotonic()-start > args.timeout:
                    timed_out=True; os.killpg(proc.pid,signal.SIGTERM); break
                for key,_ in sel.select(1):
                    data=os.read(key.fd,65536)
                    if not data: sel.unregister(key.fileobj); continue
                    buf+=data
                    while b'\n' in buf:
                        line,buf=buf.split(b'\n',1)
                        if not line: continue
                        try: event=json.loads(line)
                        except ValueError: event={'type':'non_json','line':line.decode(errors='replace')}
                        row={'t_s':time.monotonic()-start,'event':event}; rows.append(row)
                        raw.write(json.dumps(row,ensure_ascii=False)+'\n'); raw.flush()
                        if event.get('type') in ('tool_execution_start','tool_execution_end','agent_settled'):
                            print(f"{row['t_s']:.3f} {event['type']} {event.get('toolName','')}",flush=True)
                        if event.get('type')=='message_end' and event.get('message',{}).get('role')=='assistant':
                            print(f"{row['t_s']:.3f} assistant_end {event['message'].get('usage')} {event['message'].get('stopReason')}",flush=True)
                if proc.poll() is not None and not sel.get_map(): break
        finally:
            sel.close()
            try:proc.wait(timeout=10)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
    result=summarize(rows,time.monotonic()-start,proc.returncode,timed_out)
    result.update(provider=args.provider,model=args.model,workspace=str(Path(args.workspace).resolve()),
                  thinking=args.thinking,
                  tools=('normal Pi discovery; actual request tools require trace review'
                         if getattr(args,'default_tools',False) else args.tools),
                  extensions=('enabled via normal Pi discovery; actual loading requires trace review'
                              if getattr(args,'enable_extensions',False) else 'disabled for controlled comparison'),
                  task_quality_verified=False)
    output.with_suffix('.summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='turns'},indent=2))
    return 0 if result['completed'] else 1


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('workspace','provider','model','prompt','output'):p.add_argument('--'+name,required=True)
    p.add_argument('--timeout',type=float,default=600)
    p.add_argument('--thinking',default='off')
    p.add_argument('--tools',default='read,grep,find,ls')
    p.add_argument('--agent-dir')
    p.add_argument('--default-tools',action='store_true',
                   help='Do not restrict Pi tool discovery with an explicit --tools list')
    p.add_argument('--enable-extensions',action='store_true',
                   help='Use normal Pi extension discovery; controlled runs disable extensions by default')
    p.add_argument('--prompt-file',action='store_true',help='Pass large prompts as Pi file attachments')
    p.add_argument('--approve',action='store_true',help='Trust this isolated benchmark project configuration')
    p.add_argument('--task-instruction',help='Direct user instruction after a reference-file attachment')
    raise SystemExit(run(p.parse_args()))
