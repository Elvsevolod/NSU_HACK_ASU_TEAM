"""Run reviewed own Python analyzers/checkers serially into a new evidence directory."""
import argparse,json,subprocess,sys,time
from pathlib import Path
V=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    output=args.output;assert not output.exists();output.mkdir(parents=True);rows=[]
    def run(label,script,*arguments):
        command=[sys.executable,'-B','checks/'+script,*map(str,arguments)];started=time.perf_counter()
        with (output/(label+'.stdout.txt')).open('w') as out,(output/(label+'.stderr.txt')).open('w') as err:
            try:completed=subprocess.run(command,cwd=V,stdout=out,stderr=err,timeout=180);status=completed.returncode
            except subprocess.TimeoutExpired:status=None
        rows.append({'label':label,'command':command,'returncode':status,'elapsed_seconds':time.perf_counter()-started})
        print(json.dumps(rows[-1]),flush=True)
        (output/'results.json').write_text(json.dumps({'passed':all(r['returncode']==0 for r in rows),'runs':rows,'targets_started':False},indent=2)+'\n')
        return status==0
    legacy=output/'legacy'
    if run('legacy-analysis','compare_public_corpus.py','--fixtures','validation_inputs/legacy-real','--output',legacy,'--candidate-only'):
        run('legacy-state','check_legacy_state.py','--reports',legacy,'--output',legacy/'checks.json')
    source='validation_inputs/piggymetrics'
    for profile,runner,checker,mutations in [('main','run_real_journey.py','check_real_journey.py','check_journey_mutations.py'),
                                            ('additional','run_additional_journey.py','check_additional_journey.py','check_additional_mutations.py')]:
        target=output/profile;oracle='development/oracles/parent29/piggymetrics-'+profile+'.oracle-v3.json'
        extra=['--path-limit','4'] if profile=='main' else []
        if run(profile,runner,'--input',source,'--output',target,*extra):
            valid=run(profile+'-values',checker,'--input',source,'--oracle',oracle,'--trace',target/'trace.json','--output',target/'checks.json')
            run(profile+'-semantic','check_semantic_projection.py','--input',source,'--oracle',oracle,'--trace',target/'trace.json','--output',target/'semantic-checks.json')
            if valid:run(profile+'-mutations',mutations,'--input',source,'--oracle',oracle,'--trace',target/'trace.json','--output',target/'mutations')
    target=output/'document'
    if run('document','run_document_journey.py','--output',target):
        run('document-mutations','check_document_mutations.py','--input',target)
    run('actor-singleton-http','check_boundary_wires.py','--output',output/'boundary-wires')
    run('flow-witnesses','export_flow_witnesses.py','--output',output/'flow-witnesses')
    target=output/'cart'
    if run('cart','run_cart_profile.py','--output',target):
        if run('cart-check','check_cart_profile.py','--trace',target,'--output',target/'checks.json'):
            run('cart-mutations','check_cart_mutations.py','--trace',target,'--output',target/'mutations')
    raise SystemExit(0 if all(r['returncode']==0 for r in rows) else 1)


if __name__=='__main__':main()
