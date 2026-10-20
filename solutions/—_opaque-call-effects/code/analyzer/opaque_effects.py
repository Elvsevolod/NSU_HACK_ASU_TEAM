"""Forget mutable facts at a call whose effect footprint is unavailable.

Java objects/maps retain identity. An ordinary Python list cannot represent an
unknown Java collection length, so every reference to such a list in live
environments is replaced with U. No empty or singleton collection is invented.
"""
from collections import Counter
from .state import U
from .java_collections import (JavaRecord, JavaMap, JavaMapView, JavaMapEntry,
    JavaMapIterator, JavaJsonMapper, JavaEnumValue, JavaTypeToken, JavaTypeFactory,
    JacksonFeature, JsonText, JsonObject, is_symbolic)
from .heap_join import widen


def copy_aliases(root, copies):
    """Connect conservative environment copies to caller-visible originals."""
    seen, aliases = set(), {}
    def visit(value):
        if not isinstance(value, (dict, list, tuple)) or id(value) in seen:
            return
        seen.add(id(value))
        copied = copies.get(id(value))
        if copied is not None and copied is not value:
            aliases[id(copied)] = value
        children = list(value.values()) if isinstance(value, dict) else list(value)
        if isinstance(value, (JavaMapView, JavaMapEntry)):
            children.append(value.backing)
        if isinstance(value, JavaMapIterator):
            children.append(value.view)
        for child in children:
            visit(child)
    visit(root)
    return aliases


def havoc(values, roots, aliases=()):
    seen, objects, replacements = set(), [], set()

    def visit(value):
        if not isinstance(value, (dict, list, tuple)) or id(value) in seen:
            return
        seen.add(id(value))
        for scope in aliases:
            original = scope.get(id(value))
            if original is not None:
                visit(original)
        if is_symbolic(value) or isinstance(value, (JsonText, JavaTypeToken, JavaTypeFactory, JacksonFeature)):
            return
        if isinstance(value, JavaMap):
            children = list(value.mapping.values()) if isinstance(value.mapping, dict) else []
            children += [part for slot in value.typed_entries if isinstance(slot, dict)
                         for part in (slot.get('key'), slot.get('value'))]
        elif isinstance(value, (JavaMapView, JavaMapEntry)):
            children = [value.backing]
        elif isinstance(value, JavaMapIterator):
            children = [value.view]
        else:
            children = list(value.values()) if isinstance(value, dict) else list(value)
        # Snapshot descendants before forgetting parent fields/map entries.
        for child in children:
            visit(child)
        if isinstance(value, tuple):
            return
        objects.append(value)
        if isinstance(value, (list, JsonObject)) or type(value) is dict and '__type__' not in value:
            replacements.add(id(value))

    for value in values:
        visit(value)
    for value in objects:
        if isinstance(value, (JavaMap, JavaMapView, JavaMapEntry, JavaMapIterator, JavaJsonMapper)):
            widen(value)
        elif isinstance(value, JavaRecord):
            for key in set(value) | set(value.wire_fields):
                if key in value.wire_fields or key not in ('__type__', '__http_entity__'):
                    value[key] = U
        elif isinstance(value, JavaEnumValue):
            for key in value:
                value[key] = U
        elif type(value) is dict and '__type__' in value:
            for key in value:
                if key not in ('__type__', '__http_entity__'):
                    value[key] = U

    counts = dict(Counter(type(value).__name__ for value in objects))
    if not replacements:
        return counts
    visited = set()
    def replace(value):
        if id(value) in replacements:
            return U
        if not isinstance(value, (dict, list, tuple)) or id(value) in visited:
            return value
        visited.add(id(value))
        if is_symbolic(value) or isinstance(value, (JsonText, JavaTypeToken, JavaTypeFactory, JacksonFeature)):
            return value
        if isinstance(value, dict):
            for key, item in list(value.items()):
                value[key] = replace(item)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                value[index] = replace(item)
        else:
            return tuple(replace(item) for item in value)
        return value
    for root in roots:
        replace(root)
    return counts
