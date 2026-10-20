"""One local report-write alternative, compared by exact bytes and measured cost."""
import argparse,gzip,hashlib,json,sys,time
from pathlib import Path
V=Path(__file__).resolve().parents[1];sys.path.insert(0,str(V/'code'))
from analyzer.reporting import finite_report


def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert not a.output.exists();a.output.mkdir(parents=True)
    report=json.loads(gzip.decompress((V/'benchmark/stages'/a.stage/'analysis-report.json.gz').read_bytes()));rows=[]
    for name,normalize in [('finite-walk-every-write',finite_report),('cycle-fallback-only',lambda x:x)]:
        path=a.output/(name+'.json');started=time.perf_counter();phase=started
        value=normalize(report);normalization=time.perf_counter()-phase;phase=time.perf_counter()
        with path.open('w') as f:json.dump(value,f,ensure_ascii=True,separators=(',',':'));f.write('\n')
        with path.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
        rows.append({'mode':name,'normalization_seconds':normalization,'serialize_write_seconds':time.perf_counter()-phase,
            'end_to_end_seconds':time.perf_counter()-started,'sha256':digest,'bytes':path.stat().st_size})
        path.unlink()
    result={'rows':rows,'exact_bytes_equal':rows[0]['sha256']==rows[1]['sha256'],
        'candidate':'Try ordinary JSON cycle detection first; only on a circular-reference failure rewind/truncate and emit finite diagnostic view.',
        'boundary':'Same already constructed final report; excludes index/analysis and uses the same disk. One local pair, not a statistical trend.',
        'large_temporary_outputs_removed_after_hash':True}
    (a.output/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));assert result['exact_bytes_equal']


if __name__=='__main__':main()
