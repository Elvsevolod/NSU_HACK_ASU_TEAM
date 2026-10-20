"""Source-only, bounded neighbouring DTO/callee context; no query or label reads."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
V=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(V/'code'))
from analyzer.project import Project,text,walk
from analyzer.retrieval_sources import source_chunks,unicode_tokens
from analyzer.generic_types import type_parts


def main():
    p=argparse.ArgumentParser();p.add_argument('--frozen',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    corpus=json.loads((a.frozen/'corpus.json').read_text());changes=[]
    for name,group in corpus.items():
        root=V/group['root_relative_to_variant'];project=Project(root/'skeleton.json',root)
        for mid,doc in group['documents'].items():
            meta=project.methods[mid];neighbours=[]
            def types(written):
                base,args=type_parts(written);yield base
                for arg in args or ():yield from types(arg)
            written=[raw for _,raw in project.parameters(mid)]+[meta.get('return_raw','')]
            for typ in dict.fromkeys(t for value in written for t in types(value)):
                owner=project.resolve_type(typ,meta['module'],meta['file'])
                if not owner:continue
                node=project.nodes[owner];tree=project.trees.get(node['file'])
                if tree is None:continue
                declaration=next((n for n in walk(tree.root_node) if n.type in ('class_declaration','record_declaration','enum_declaration','interface_declaration')
                    and text(n.child_by_field_name('name'))==node['fqn'].rsplit('.',1)[-1]),None)
                pending=[declaration] if declaration else []
                while pending:
                    current=pending.pop(0);content=text(current)
                    if len(unicode_tokens(content))>192:pending[0:0]=list(current.named_children);continue
                    neighbours.append({'text':node['fqn']+'\n'+content,'file':node['file'],'line':current.start_point.row+1,
                        'source_sha256':hashlib.sha256(project.sources[node['file']]).hexdigest(),'role':'DTO source'})
            for site in sorted(project.sites.get(mid,())):
                for target in sorted(project.targets(mid,site)):
                    neighbours.extend({**c,'role':'direct source callee'} for c in source_chunks(project,target))
            selected=[]
            for chunk in neighbours:
                if chunk['text'] in doc['text'] or any(c['text']==chunk['text'] for c in selected):continue
                selected.append(chunk)
                if len(selected)==4:break
            doc['context_text']=doc['text']+('\nSource context:\n'+'\n'.join(c['text'] for c in selected) if selected else '')
            doc['context_chunks']=selected;changes.append({'project':name,'entry':mid,'chunks':len(selected)})
    for file in ('protocol.json','actions.json'):(a.output/file).write_bytes((a.frozen/file).read_bytes())
    (a.output/'corpus.json').write_text(json.dumps(corpus,ensure_ascii=False,indent=2)+'\n')
    (a.output/'sha256.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(a.output.iterdir()) if p.is_file()},indent=2)+'\n')
    (a.output/'context-provenance.json').write_text(json.dumps({'base_corpus_sha256':hashlib.sha256((a.frozen/'corpus.json').read_bytes()).hexdigest(),
        'selection':'Fixed DTO-then-callee source order, max four AST chunks, 192 Unicode lexical tokens per chunk; no label/query-dependent selection',
        'pre_test_disclosure':'Original same-method context was identical to base; retained as no-op run. This source-only extension was frozen before reading test outcomes.',
        'changes':changes},ensure_ascii=False,indent=2)+'\n')
    print(sum(r['chunks']>0 for r in changes))


if __name__=='__main__':main()
