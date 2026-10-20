import argparse,json
from copy import deepcopy
from pathlib import Path
from check_document_journey import check


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);args=p.parse_args()
    oracle=json.loads((args.input/'oracle.json').read_text());trace=json.loads((args.input/'nl.json').read_text())
    rows=[s['alternatives'][0] for s in trace['steps']];assert check(rows,oracle,'nl')['passed']
    def modify(path,value):
        def apply(rows):
            root=rows
            for key in path[:-1]:root=root[key]
            root[path[-1]]=value
        return apply
    mutations={
      'boolean_result_as_int':modify([1,'result','approved'],1),
      'integer_revision_as_boolean':modify([1,'result','revision'],True),
      'integer_revision_as_float':modify([1,'result','revision'],8.0),
      'wire_boolean_as_int':modify([1,'request','body','approved'],1),
      'wire_wrong_identity':modify([1,'request','body','id'],'D9'),
      'remote_wrong_identity':modify([1,'requests',1,'request','url'],'http://docs/documents/D9/approve'),
      'actual_dto_boolean_as_int':modify([1,'requests',0,'bound_arguments',0,'value','approved'],1),
      'actual_dto_wrong_runtime_type':modify([1,'requests',0,'bound_arguments',0,'value','__type__'],'OtherApproval'),
      'missing_actual_arguments':modify([1,'requests',1,'bound_arguments'],[]),
      'wrong_saved_revision':modify([1,'state_after','tables','docs.documents',0,'revision'],9),
      'saved_boolean_as_int':modify([1,'state_after','tables','docs.documents',0,'approved'],1),
      'extra_saved_row':modify([1,'state_after','tables','docs.documents'],[{'id':'D7','revision':8,'approved':True},{'id':'D8','revision':8,'approved':True}]),
      'browser_retains_stale_value':modify([2,'state_after','browser','form','documents',0,'approved'],False),
      'unknown_table':modify([1,'state_after','unknown_tables'],['docs.documents']),
      'deleted_codec_diagnostic':modify([0,'unresolved'],[]),
      'lost_remote_failure':modify([1,'responses',0,'status'],200),
      'lost_edges':modify([1,'edges'],[]),
    }
    results=[]
    for name,mutate in mutations.items():
        changed=deepcopy(rows);mutate(changed);strong=check(changed,oracle,'nl')
        weak=all(row['result']==expected['result'] for row,expected in zip(changed,oracle['steps']))
        results.append({'mutation':name,'rejected':not strong['passed'],'legacy_value_only_check_accepts':weak,
                        'failed_checks':[key for row in strong['steps'] for key,value in row.items() if key!='n' and not value]})
    result={'passed':all(r['rejected'] for r in results),'mutations':results,
            'checker_executes_target':False,'python_true_equals_one_is_not_used':True}
    (args.input/'mutation-checks.json').write_text(json.dumps(result,indent=2)+'\n');assert result['passed'],result


if __name__=='__main__':main()
