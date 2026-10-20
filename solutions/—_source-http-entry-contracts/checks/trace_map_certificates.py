"""Diagnostic-only refusal locations; no change to proof or path decisions."""
import argparse
import json
from pathlib import Path
import runpy
import sys


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--diagnostics',type=Path,required=True)
    args,forwarded=parser.parse_known_args()
    rows=[];calls=[];seen=set()
    def trace(frame,event,value):
        if frame.f_code.co_name=='call' and frame.f_code.co_filename.endswith('/analyzer/engine.py'):
            if event=='return':
                local=frame.f_locals;engine=local['self'];node=local.get('node')
                if (local.get('name') in ('contains','indexOf') and node is not None and
                        'BasicServiceImpl#queryForTravels' in str(engine.method)):
                    obj=local.get('obj');key=(node.start_point.row,type(obj).__name__,repr(obj)[:200])
                    if key not in seen:
                        seen.add(key);calls.append({'method':engine.method,'line':node.start_point.row+1,
                            'name':local['name'],'runtime_carrier':type(obj).__name__,
                            'receiver_type':local.get('receiver_type'),'runtime_attributes':list(getattr(obj,'__dict__',{})),
                            'value_preview':repr(obj)[:260]})
            return trace
        if frame.f_code.co_name!='certify' or not frame.f_code.co_filename.endswith('/map_filter_proof.py'):
            return None
        if event=='return':
            local=frame.f_locals;engine=local['engine'];node=local['node'];probe=local.get('probe')
            row={'method':engine.method,'loop_line':node.start_point.row+1,
                 'proof_return_line':frame.f_lineno,'accepted':value is True,
                 'target':local.get('target_name'),'before_context_complete':local.get('before') is not None,
                 'state_context_complete':local.get('state_before') is not None}
            if probe is not None:
                row.update(probe_warnings=sorted(probe.warnings),probe_approximate=probe.approximate,
                           probe_conditions=probe.conditions,probe_source_invocations=probe.calls)
            rows.append(row)
        return trace
    sys.argv=[str(Path(__file__).with_name('run_tt_causal_probes.py')),*forwarded]
    sys.settrace(trace)
    try:
        runpy.run_path(sys.argv[0],run_name='__main__')
    finally:
        sys.settrace(None)
        args.diagnostics.write_text(json.dumps({'schema':'map-certificate-refusals/1',
            'observations':rows,'call_observations':calls},indent=2)+'\n')


if __name__=='__main__':main()
