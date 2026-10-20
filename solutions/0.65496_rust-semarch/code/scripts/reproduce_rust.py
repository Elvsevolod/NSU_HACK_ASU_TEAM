#!/usr/bin/env python3
"""Build/test OUR Rust analyzer in an isolated Cargo target dir; never run target services.
Source dependency downloads occur only if Cargo requires them and --offline is absent.
No source edits, no copying gold into the production path. GNU time reports whole command RSS.

Provenance: this harness was prepared by the independent engineering audit of the
a4db167 archive (SEMARCH_ENGINEERING_RESEARCH_AND_PLAN) and is kept verbatim in
`semarch/scripts/` so the developer reproduces the same evidence. After N01 the
report path accepts the same `--disable` switches as the exporter, so an ablation
answer and the report that explains it can be produced from one configuration.
"""
import argparse,hashlib,json,os,platform,shutil,subprocess,sys,time
from pathlib import Path

def main():
 ap=argparse.ArgumentParser();ap.add_argument('root',type=Path);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--offline',action='store_true');ap.add_argument('--ablations',action='store_true');a=ap.parse_args();r=a.root.resolve();o=a.out.resolve();o.mkdir(parents=True,exist_ok=True)
 results=[];env=os.environ.copy();env['CARGO_TARGET_DIR']=str(o/'cargo-target')
 def flush(): (o/'commands.json').write_text(json.dumps({'platform':platform.platform(),'commands':results},ensure_ascii=False,indent=2)+'\n')
 def run(name,cmd,cwd,ok=(0,),measure=False):
  full=list(map(str,cmd));tfile=o/(name+'.time.txt')
  if measure and sys.platform.startswith('linux') and Path('/usr/bin/time').is_file():full=['/usr/bin/time','-v','-o',str(tfile)]+full
  t=time.perf_counter()
  try:
   with (o/(name+'.stdout.txt')).open('w') as so,(o/(name+'.stderr.txt')).open('w') as se:
    p=subprocess.run(full,cwd=cwd,env=env,stdout=so,stderr=se,check=False)
   x={'name':name,'argv':full,'cwd':str(cwd),'exit':p.returncode,'accepted_exit_codes':list(ok),'status':'passed' if p.returncode in ok else 'failed','wall_seconds':time.perf_counter()-t}
  except OSError as e:x={'name':name,'argv':full,'status':'blocked','error':str(e)}
  results.append(x);flush();return x['status']=='passed'
 if not shutil.which('cargo'):
  results.append({'name':'rust-reproduction','status':'blocked','reason':'cargo not installed; no tests or Rust outputs generated'});flush();print('BLOCKED: cargo unavailable');return 2
 cargo=['cargo'];off=['--offline'] if a.offline else []
 run('cargo-version',cargo+['--version'],r/'semarch')
 if not run('tests',cargo+['test','--workspace','--locked']+off,r/'semarch',measure=True):return 1
 if not run('release-build',cargo+['build','--release','--locked','-p','semarch-cli']+off,r/'semarch',measure=True):return 1
 binary=o/'cargo-target/release/semarch';tt=r/'tt-challenge'
 for name in ('run1','run2'):
  if not run(name,[binary,'tt-export',tt,'--out',o/(name+'.json')],r,measure=True):return 1
 hashes={n:hashlib.sha256((o/(n+'.json')).read_bytes()).hexdigest() for n in ('run1','run2')}
 (o/'determinism.json').write_text(json.dumps({'sha256':hashes,'byte_equal':hashes['run1']==hashes['run2'],'scope':'two process runs; OS page cache not flushed'},indent=2)+'\n')
 run('report',[binary,'tt-report',tt,'--out',o/'report.json'],r,measure=True)
 ev=tt/'platform/evaluate_golden.py'
 run('s0-score',[sys.executable,ev,tt/'gold/S0.json',o/'run1.json'],r)
 run('format',[sys.executable,ev,'--check',tt/'skeleton/trainticket.json.gz',o/'run1.json'],r,ok=(3,))
 run('s0-diff',[sys.executable,r/'semarch/scripts/compare_gold.py',o/'run1.json',tt/'gold/S0.json'],r)
 if a.ablations:
  for mech in ('dispatch','declarations','repositories','entities','callbacks','guards','static'):
   dest=o/('without_'+mech+'.json')
   if run('ablate_'+mech,[binary,'tt-export',tt,'--disable',mech,'--out',dest],r,measure=True):
    run('score_without_'+mech,[sys.executable,ev,tt/'gold/S0.json',dest],r)
    run('format_without_'+mech,[sys.executable,ev,'--check',tt/'skeleton/trainticket.json.gz',dest],r,ok=(3,))
    # The report path takes the identical switch (N01), so an ablation answer
    # is explained by a report built from the same configuration.
    run('report_without_'+mech,[binary,'tt-report',tt,'--disable',mech,'--out',o/('report_without_'+mech+'.json')],r)
 return 0 if all(x['status']=='passed' for x in results) and hashes['run1']==hashes['run2'] else 1
if __name__=='__main__':sys.exit(main())
