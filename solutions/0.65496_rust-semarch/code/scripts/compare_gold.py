#!/usr/bin/env python3
"""Diff submitted scenario blocks against an organizer gold file.

    compare_gold.py <submission.json> [gold.json] [all|extra|miss]

Reports, per relation, the size of both sets, the true positives and the
edges that are extra or missing. This is a *measurement* helper: the tool that
builds the answer never reads a gold file, so this script lives outside the
analysis path.
"""
import collections
import json
import sys

sub = json.load(open(sys.argv[1] if len(sys.argv) > 1 else 'submission.json'))
gold_all = json.load(open(sys.argv[2] if len(sys.argv) > 2 else 'gold/S0.json'))['scenarios']
show = sys.argv[3] if len(sys.argv) > 3 else 'all'

short = lambda s: s.split(':', 2)[-1]


def gmap_of(gold):
    return {
        'executes': {('scenario', m) for m in gold['methods']},
        'calls': {tuple(x) for x in gold['calls']},
        'remote': {tuple(x) for x in gold['remote']},
        'data': {tuple(x) for x in gold['data']},
    }


for sid, gold in sorted(gold_all.items()):
    block = sub['scenarios'].get(sid)
    if block is None:
        print(f"== {sid}: missing from the submission")
        continue
    pred = collections.defaultdict(set)
    for e in block['edges']:
        src = 'scenario' if e['source'].startswith('scenario:') else e['source']
        pred[e['relation']].add((src, e['target']))
    gmap = gmap_of(gold)
    print(f"### {sid}")
    for rel in ('executes', 'calls', 'remote', 'data'):
        p, g = pred.get(rel, set()), gmap[rel]
        tp, extra, miss = p & g, p - g, g - p
        print(f"== {rel}: pred={len(p)} gold={len(g)} tp={len(tp)} extra={len(extra)} miss={len(miss)}")
        if show in ('all', 'extra'):
            for a, b in sorted(extra):
                print(f"   + {short(a)} -> {short(b)}")
        if show in ('all', 'miss'):
            for a, b in sorted(miss):
                print(f"   - {short(a)} -> {short(b)}")
