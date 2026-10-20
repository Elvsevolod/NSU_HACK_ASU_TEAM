"""Source-only retrieval documents. No scenarios, traces or answer inputs."""
import hashlib
import json
import re
import unicodedata
from .project import text
from .state import U

CHUNK_TOKENS=192
MAX_CHUNKS=8


def unicode_tokens(value):
    value=unicodedata.normalize('NFKC',str(value))
    pieces=[]
    for word in re.findall(r'[^\W_]+',value):
        start=0
        for i in range(1,len(word)):
            if (word[i].isupper() and (word[i-1].islower() or word[i-1].isdigit()) or
                word[i-1].isupper() and word[i].isupper() and i+1<len(word) and word[i+1].islower()):
                pieces.append(word[start:i].casefold());start=i
        pieces.append(word[start:].casefold())
    return pieces


def source_chunks(project,mid):
    meta=project.methods[mid];node=project.ast.get(mid)
    if node is None:return []
    data=project.sources[meta['file']];digest=hashlib.sha256(data).hexdigest()
    pending=[node];result=[]
    while pending and len(result)<MAX_CHUNKS:
        current=pending.pop(0);content=text(current)
        if len(unicode_tokens(content))>CHUNK_TOKENS:
            pending[0:0]=list(current.named_children)
            continue
        result.append({'id':f'chunk:{mid}:{current.start_byte}:{current.end_byte}',
            'entry':mid,'file':meta['file'],'line':current.start_point.row+1,
            'end_line':current.end_point.row+1,'start_byte':current.start_byte,'end_byte':current.end_byte,
            'source_sha256':digest,'sha256':hashlib.sha256(content.encode()).hexdigest(),'text':content})
    return result


def documents(project,contracts):
    result={};chunks={}
    for key,contract in sorted(contracts.items()):
        mid=contract['entry'];meta=project.methods[mid];site=contract['site']
        if mid not in chunks:chunks[mid]=source_chunks(project,mid)
        facts={'entry':mid,'method':meta['name'],'owner':project.nodes[meta['owner']]['fqn'],
            'http_method':contract['verb'],'route':contract['route'],
            'annotations':meta.get('annotations',[]),'parameters':project.http_parameters(mid),
            'request_fields':project.request_fields(mid),'return_type':meta.get('return_raw',''),
            'ui':{name:site.get(name) for name in ('id','file','page','action_label','body_fields','conditions')} if site else None}
        # Unsupported/absent source metadata remains explicitly unknown.
        facts=json.loads(json.dumps(facts,ensure_ascii=False,default=lambda value:{'knowledge':'unknown'} if value is U else sorted(value) if isinstance(value,set) else str(value)))
        data=project.sources.get(meta['file'],b'')
        result[key]={'contract_id':key,'entry':mid,'facts':facts,'file':meta['file'],
            'line':meta.get('line'),'source_sha256':hashlib.sha256(data).hexdigest(),
            'fact_text':json.dumps(facts,ensure_ascii=False,sort_keys=True), 'chunks':chunks[mid]}
    return result
