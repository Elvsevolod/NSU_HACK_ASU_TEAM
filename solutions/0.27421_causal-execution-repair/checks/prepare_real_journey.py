"""Source-only skeleton adapter. The expected execution oracle is never read."""
from pathlib import Path
from copy import deepcopy
import argparse
import hashlib
import json
import shutil
import sys

VARIANT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(VARIANT/'code'),str(VARIANT/'checks')]
from prepare_public_corpus import fixture
from analyzer.project import text,walk,declaration_matches
from builders import annotations


def flatten_yaml(path):
    stack=[]
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith('#') or ':' not in line:continue
        indentation=len(line)-len(line.lstrip())
        key,value=line.strip().split(':',1)
        while stack and stack[-1][0]>=indentation:stack.pop()
        name='.'.join([part for _,part in stack]+[key])
        if value.strip():yield name,value.strip().strip('"\'')
        else:stack.append((indentation,key))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--repository',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();assert not args.output.exists()
    args.output.mkdir(parents=True)
    nodes,edges,manifest={},[],{}
    for module in ('account-service','auth-service','statistics-service'):
        local=args.output/module
        fixture(args.repository,local,module,[module+'/src/main/java'],{},'6bb2cf9ddbca980b664d3edbb6ff775d75369278')
        graph=json.loads((local/'skeleton.json').read_text())
        # The small public-fixture builder predates enum method declarations.
        # Supply every missing source method in those enum bodies, without
        # consulting the journey or its expected execution.
        from tree_sitter import Language,Parser
        import tree_sitter_java
        java=Parser(Language(tree_sitter_java.language()))
        for tid,info in list(graph['nodes'].items()):
            if info['kind']!='type':continue
            tree=java.parse((local/info['file']).read_bytes())
            declarations=[node for node in walk(tree.root_node) if node.type=='enum_declaration' and declaration_matches(node,info['fqn'])]
            if len(declarations)!=1:continue
            for node in walk(declarations[0].child_by_field_name('body')):
                if node.type!='method_declaration':continue
                name=text(node.child_by_field_name('name'));parameters=[text(p.child_by_field_name('type')) for p in node.child_by_field_name('parameters').named_children if p.type=='formal_parameter']
                key='method:'+module+':'+info['fqn'].rsplit('.',1)[-1]+'#'+name+'('+','.join(parameters)+')'
                graph['nodes'].setdefault(key,{'kind':'method','name':name,'owner':tid,'module':module,'file':info['file'],
                    'line':node.start_point.row+1,'end':node.end_point.row+1,'params_as_written':parameters,
                    'abstract':False,'annotations':annotations(node),'return_raw':text(node.child_by_field_name('type'))})
        for key,node in graph['nodes'].items():
            if node.get('file'):node['file']=module+'/'+node['file']
            for origin in node.get('origin',[]):
                if origin.get('file'):origin['file']=module+'/'+origin['file']
            nodes[key]=node
        edges.extend(graph['edges'])
        for name,value in flatten_yaml(args.repository/'config/src/main/resources/shared'/f'{module}.yml'):
            nodes['config:'+module+':'+name]={'kind':'config_entry','module':module,'key':name,'value':value,
                'origin':[{'file':'config/src/main/resources/shared/'+module+'.yml'}]}
        for source in local.rglob('*.java'):manifest[source.relative_to(args.output).as_posix()]=hashlib.sha256(source.read_bytes()).hexdigest()
    graph={'project':'piggymetrics-real-journey','nodes':nodes,'edges':edges}
    (args.output/'skeleton.json').write_text(json.dumps(graph,indent=2)+'\n')
    # Initial business rows are supplied input facts, not expected outputs.
    (args.output/'initial.sql').write_text('''USE `account-service`;
CREATE TABLE `accounts` (
 `name` varchar(80),
 `last_seen` varchar(80),
 `incomes` varchar(80),
 `expenses` varchar(80),
 `saving` varchar(80),
 `note` varchar(80)
) ENGINE=InnoDB;
USE `auth-service`;
CREATE TABLE `users` (
 `username` varchar(80),
 `password` varchar(80)
) ENGINE=InnoDB;
INSERT INTO `users` VALUES ('occupied','initial-hash');
USE `statistics-service`;
CREATE TABLE `datapoints` (
 `id` varchar(80)
) ENGINE=InnoDB;
''')
    (args.output/'source-manifest.json').write_text(json.dumps({'sources':manifest,'oracle_read':False,
        'targets_started':False,'commit':'6bb2cf9ddbca980b664d3edbb6ff775d75369278'},indent=2)+'\n')
    print(json.dumps({'source_files':len(manifest),'nodes':len(nodes),'output':str(args.output)}))


if __name__=='__main__':main()
