"""Whitelist-only metrics export. Private transcripts and source are never copied."""
import math
import re


def number(value):
    if value is None:return None
    if type(value) not in (int,float) or not math.isfinite(value):
        raise ValueError('Metric must be a finite number or null')
    return value


def flag(value):
    if value is not None and type(value) is not bool:raise ValueError('Flag must be boolean or null')
    return value


def public_row(run_id,summary):
    if not isinstance(run_id,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',run_id):
        raise ValueError('Invalid public run identifier')
    turns=summary.get('turns',[])
    counts=[number(t.get('usage',{}).get('input',0))+number(t.get('usage',{}).get('cacheRead',0)) for t in turns]
    return {
        'run_id':run_id,
        'completed':flag(summary.get('completed')),
        'timed_out':flag(summary.get('timed_out')),
        'bounded_quality_pass':flag(summary.get('task_quality_verified')),
        'elapsed_s':number(summary.get('elapsed_s')),
        'initial_input_tokens':counts[0] if counts else None,
        'max_input_tokens':max(counts) if counts else None,
        'initial_cache_read_tokens':number(turns[0].get('usage',{}).get('cacheRead')) if turns else None,
        'first_ttft_s':number(turns[0].get('ttft_s')) if turns else None,
        'tool_calls':number(summary.get('tool_calls')),
        'tool_errors':number(summary.get('tool_errors')),
        'compactions':number(summary.get('compactions')),
        'visible_final_tokens':number(summary.get('final_visible_text_tokens')),
        'visible_stream_tps':number(summary.get('final_visible_stream_tps')),
        'visible_cycle_tps':number(summary.get('final_visible_cycle_tps')),
        'visible_assistant_request_tps':number(summary.get('final_visible_request_tps')),
        'task_completion_tps_including_reasoning_and_tools':number(summary.get('task_generated_tps')),
    }
