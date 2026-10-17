"""Тесты разбора Spring-маршрутов в baseline_closure."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from baseline_closure import Index, RouteWarning, ann_paths


def _ann(name, args):
    return {"name": name, "args": args}


def test_value_and_path_attrs_only():
    assert ann_paths([_ann("PostMapping", 'value = "/tickets", produces = "application/json"')]) == [("POST", ["/tickets"])]
    assert ann_paths([_ann("PutMapping", 'path = "/p", consumes = "text/plain"')]) == [("PUT", ["/p"])]
    assert ann_paths([_ann("org.springframework.web.bind.annotation.GetMapping", '"/tickets"')]) == [("GET", ["/tickets"])]
    assert ann_paths([_ann("CustomMapping", '"/skip"'), _ann("Service", "")]) == []


def test_method_array_expands_to_separate_tuples():
    anns = [_ann("RequestMapping", 'value = {"/a", "/b"}, method = {RequestMethod.GET, RequestMethod.POST}')]
    assert ann_paths(anns) == [("GET", ["/a", "/b"]), ("POST", ["/a", "/b"])]
    assert ann_paths([_ann("RequestMapping", '"/x"')]) == [("REQUEST", ["/x"])]
    assert ann_paths([_ann("DeleteMapping", "")]) == [("DELETE", [""])]


def test_symbolic_path_warns_without_route():
    with pytest.warns(RouteWarning):
        assert ann_paths([_ann("GetMapping", "ApiPaths.TICKETS")]) == []


def test_index_unions_class_and_method_verbs_with_class_prefix():
    cls_post = [_ann("RequestMapping", 'value = "/api", method = RequestMethod.POST')]
    cls_plain = [_ann("RequestMapping", '"/api"')]
    m_get = [_ann("GetMapping", '"/list"')]
    m_plain = [_ann("RequestMapping", '"/list"')]

    def build(class_anns, method_anns):
        return Index({"nodes": {
            "ctrl": {"id": "ctrl", "kind": "type", "name": "Ctrl", "annotations": class_anns},
            "list": {"id": "list", "kind": "method", "owner": "ctrl", "name": "list",
                     "module": "ctrl", "annotations": method_anns},
        }, "edges": []})

    both = build(cls_post, m_get)
    assert sorted(h[1] for h in both.handlers) == ["GET", "POST"]
    assert both.handlers_for("GET", "/api/list") == {"list"}
    assert both.handlers_for("POST", "/api/list") == {"list"}
    assert both.handlers_for("GET", "/list") == set()

    assert [h[1] for h in build(cls_plain, m_get).handlers] == ["GET"]
    assert [h[1] for h in build(cls_post, m_plain).handlers] == ["POST"]
