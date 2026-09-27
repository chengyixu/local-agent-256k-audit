"""Strict surface checks on raw Task D output. Never repairs text or claims semantic proof."""
import json

EXPECTED_CASES=[(3,1,8,[1,2]),(5,10,2,[2,2,2,2]),(1,0.1,2,[])]
KEYS={'receipts','cases','retryable_statuses','inspected_file','verification_command'}
CASE_KEYS={'max_attempts','initial_delay_s','max_delay_s','delays'}


def evaluate(rows, receipts):
    pending={};successful=[];final=None
    for row in rows:
        event=row['event'];kind=event.get('type');msg=event.get('message',{})
        if kind=='tool_execution_start' and event.get('toolName')=='bash':
            pending[event.get('toolCallId')]=event.get('args',{}).get('command')
        if kind=='tool_execution_end' and event.get('toolCallId') in pending:
            cmd=pending.pop(event['toolCallId'])
            if event.get('isError') is False and isinstance(cmd,str):successful.append(cmd)
        if kind=='message_end' and msg.get('role')=='assistant':
            final=''.join(c.get('text','') for c in msg.get('content',[]) if c.get('type')=='text') if msg.get('stopReason')=='stop' else None
    result={'strict_json_format':False,'reported_values_correct':False,'verification_command_exact':False}
    if final is None:return result
    try:answer=json.loads(final)
    except (ValueError,TypeError):return result
    if not isinstance(answer,dict):return result
    result['strict_json_format']=True
    result['verification_command_exact']=isinstance(answer.get('verification_command'),str) and answer['verification_command'] in successful
    cases=answer.get('cases');valid=isinstance(cases,list) and len(cases)==3
    if valid:
        for case,expected in zip(cases,EXPECTED_CASES):
            if not isinstance(case,dict) or set(case)!=CASE_KEYS:valid=False;break
            values=(case['max_attempts'],case['initial_delay_s'],case['max_delay_s'],case['delays'])
            nums=values[:3]
            if not all(type(n) in (int,float) for n in nums) or not isinstance(values[3],list) or not all(type(n) in (int,float) for n in values[3]) or values!=expected:
                valid=False;break
    statuses=answer.get('retryable_statuses')
    valid_statuses=isinstance(statuses,dict) and set(statuses)=={'429','401'} and statuses['429'] is True and statuses['401'] is False
    result['reported_values_correct']=bool(set(answer)==KEYS and valid and valid_statuses and answer.get('receipts')==receipts)
    return result
