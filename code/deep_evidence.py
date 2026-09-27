"""Separate attempted tool use, successful disclosure, retrieval and completion."""
from pathlib import Path
import json
import os


def extract(rows, receipts: list[str], workspace: Path, dossier: Path) -> dict:
    calls={};text='';stop=None;attempted=False;accessed=False;read_repo=False
    target=os.path.normpath(str(workspace/'src/KK_LLM/retry.py'))
    for row in rows:
        e=row['event'];kind=e.get('type')
        if kind=='message_end' and e.get('message',{}).get('role')=='assistant':
            m=e['message']
            if m.get('stopReason') in ('stop','length'):
                text='\n'.join(c.get('text','') for c in m.get('content',[]) if c.get('type')=='text')
                stop=m.get('stopReason')
        elif kind=='tool_execution_start':
            calls[e['toolCallId']]={'name':e.get('toolName'),'args':e.get('args') or {}}
            if str(dossier) in json.dumps(e.get('args') or {}):attempted=True
        elif kind=='tool_execution_end' and not e.get('isError'):
            call=calls.get(e.get('toolCallId'),{})
            args=call.get('args',{})
            if str(dossier) in json.dumps(args) or 'deep-task.txt' in json.dumps(args):accessed=True
            if call.get('name')=='read':
                path=Path(str(args.get('path','')))
                if not path.is_absolute():path=workspace/path
                if os.path.normpath(str(path))==target:read_repo=True
    positions=[text.find(s) for s in receipts]
    return {'receipts_recovered':bool(receipts) and all(i>=0 for i in positions) and positions==sorted(positions),
            'answer_complete':stop=='stop','dossier_access_attempted':attempted,
            'dossier_access_succeeded':accessed,'read_repository_file':read_repo}
