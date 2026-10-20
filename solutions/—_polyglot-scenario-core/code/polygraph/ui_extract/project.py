"""Syntax helpers only; no legacy Project or Engine."""

def text(node):
    return node.text.decode('utf-8') if node is not None else ''


def walk(node):
    yield node
    for child in node.named_children:
        yield from walk(child)


