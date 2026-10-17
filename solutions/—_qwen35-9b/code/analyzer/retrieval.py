"""Rank source-derived handler contracts by BM25 and dense reciprocal ranks."""
import hashlib
import json
from pathlib import Path
from baseline_closure import BM25
from baseline_nlp import ntoks, front_files
from .project import text


def fingerprint(project):
    digest = hashlib.sha256(json.dumps(project.skeleton, sort_keys=True).encode())
    for file, source in sorted(project.sources.items()):
        digest.update(file.encode())
        digest.update(source)
    for file in sorted(front_files(str(project.root))):
        digest.update(str(Path(file).relative_to(project.root)).encode())
        digest.update(Path(file).read_bytes())
    return digest.hexdigest()


class Retrieval:
    def __init__(self, project, frontend):
        self.documents = {}
        for mid, _, route in project.ix.handlers:
            meta = project.methods[mid]
            sites = [site for site in frontend.sites.values() if mid in site['handlers']]
            source = text(project.ast.get(mid))
            self.documents[mid] = '\n'.join([meta['name'], meta['module'], '/'.join(route),
                                             str(project.request_fields(mid)), source[:1800],
                                             *[site['labels'][:700] + '\n' + site['source'][:1200] for site in sites[:4]]])
        self.ids = sorted(self.documents)
        self.bm25 = BM25({mid: ntoks(doc) for mid, doc in self.documents.items()})
        self.rankings = {}

    def prepare(self, actions, encoder):
        import numpy as np
        # Fixed-size overlapping text windows prevent long files from replacing method boundaries.
        chunks, owners = [], []
        for mid in self.ids:
            words = self.documents[mid].split()
            for start in range(0, max(1, len(words)), 220):
                chunks.append(' '.join(words[start:start + 280]))
                owners.append(mid)
        vectors = encoder.encode(chunks)
        queries = sorted(set(actions))
        query_vectors = encoder.encode(queries) if queries else np.zeros((0, vectors.shape[1]))
        for query, query_vector in zip(queries, query_vectors):
            dense_scores = {}
            for mid, score in zip(owners, vectors @ query_vector):
                dense_scores[mid] = max(dense_scores.get(mid, -1), float(score))
            dense = sorted(dense_scores, key=lambda mid: (-dense_scores[mid], mid))
            lexical = [mid for _, mid in self.bm25.rank(ntoks(query))]
            scores = {mid: 0.0 for mid in self.ids}
            for ranking in (dense, lexical):
                for rank, mid in enumerate(ranking):
                    scores[mid] += 1 / (60 + rank + 1)
            hybrid = sorted(scores, key=lambda mid: (-scores[mid], mid))
            self.rankings[query] = {'hybrid': hybrid[:20], 'bm25': lexical[:20], 'dense': dense[:20],
                                    'scores': {mid: scores[mid] for mid in hybrid[:20]}}
        return self.rankings

    def save(self, path, project):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps({'schema': 1, 'recipe': 'BM25+BGE-M3-dense/RRF60/windows280-overlap60/max_seq512',
                                         'fingerprint': fingerprint(project), 'rankings': self.rankings}, indent=2) + '\n')

    def load(self, path, project):
        obj = json.loads(Path(path).read_text())
        if obj.get('schema') != 1 or obj['fingerprint'] != fingerprint(project):
            raise ValueError('Retrieval index does not match source and skeleton')
        self.rankings = obj['rankings']

    def candidates(self, action, limit=6):
        if action not in self.rankings:
            raise ValueError('Unindexed action: run prepare_index.py for the new scenarios')
        return self.rankings[action]['hybrid'][:limit]
