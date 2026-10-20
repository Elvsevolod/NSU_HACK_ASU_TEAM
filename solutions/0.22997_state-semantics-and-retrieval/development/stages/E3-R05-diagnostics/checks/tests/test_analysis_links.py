"""Ordinary evidence folders need no controller run.json to be packaged."""
from package_analysis import exclusion,document_links,V


def test_artifact_directory_is_not_mistaken_for_active_controller():
    path=V/'benchmark/overnight/G02/causal-ledger-v2/causal-ledger.json'
    assert path.exists() and not (path.parent/'run.json').exists()
    assert exclusion(path) is None


def test_missing_document_evidence_is_rejected():
    name='solution_31/FINAL_REVIEW.md';body=b'[evidence](benchmark/ledger/result.json)'
    assert document_links({}, {name:body})==[[name,'solution_31/benchmark/ledger/result.json']]
    assert document_links({'solution_31/benchmark/ledger/result.json':'digest'},{name:body})==[]
