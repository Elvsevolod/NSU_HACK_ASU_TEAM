"""Export source vectors only; no query vectors, rankings or test labels."""
import argparse,hashlib,json,sys
from pathlib import Path
V=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(V/'code'))
from analyzer.project import Project
from analyzer.hashing import fingerprint


def main():
    p=argparse.ArgumentParser()
    for arg in ('frozen','vectors','selection','output'):p.add_argument('--'+arg,type=Path,required=True)
    a=p.parse_args();assert not a.output.exists()
    corpus=json.loads((a.frozen/'corpus.json').read_text());vectors=json.loads(a.vectors.read_text());selection=json.loads(a.selection.read_text())
    model=selection['embedding_winner'];identity=vectors['identity'];assert identity['model']==model
    calibration=selection['calibration'][model]
    data={'model':model,'revision':identity['revision'],'adapter_sha256':identity['adapter_sha256'],
        'minimum_score':calibration['minimum_score'],'minimum_margin':calibration['minimum_margin'],
        'selection_sha256':hashlib.sha256(a.selection.read_bytes()).hexdigest(),'source_corpus_sha256':hashlib.sha256((a.frozen/'corpus.json').read_bytes()).hexdigest(),
        'projects':{},'input_fingerprints':{}}
    for name,group in corpus.items():
        root=V/group['root_relative_to_variant'];data['input_fingerprints'][name]=fingerprint(Project(root/'skeleton.json',root))
        data['projects'][name]={mid:{**{k:doc[k] for k in ('file','line','source_sha256')},
            'text_sha256':hashlib.sha256(doc['text'].encode()).hexdigest(),'vector':vectors['documents'][mid]} for mid,doc in group['documents'].items()}
    a.output.write_text(json.dumps(data,separators=(',',':'))+'\n')


if __name__=='__main__':main()
