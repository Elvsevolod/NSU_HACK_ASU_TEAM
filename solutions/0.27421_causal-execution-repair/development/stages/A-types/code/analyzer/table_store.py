"""Table snapshots share immutable backing rows until mutable access."""
from collections.abc import MutableMapping
from copy import deepcopy


class TableStore(MutableMapping):
    def __init__(self):
        self._tables = {}
        self._shared = set()
        self._copy_memo = {}
        self._sources = []
        self._identity_cache = {}

    def __iter__(self):return iter(self._tables)
    def __len__(self):return len(self._tables)

    def __getitem__(self, key):
        rows = self._tables[key]
        if key in self._shared:
            self._sources.append(rows)
            owned = deepcopy(rows, self._copy_memo)
            # Preserve even an explicitly shared table list inside one path.
            for alias, value in list(self._tables.items()):
                if value is rows:
                    self._tables[alias] = owned
                    self._shared.discard(alias)
                    self._identity_cache.pop(alias,None)
            rows = owned
        return rows

    def __setitem__(self, key, value):
        self._tables[key] = value
        self._shared.discard(key)
        self._identity_cache.pop(key,None)

    def __delitem__(self, key):
        del self._tables[key]
        self._shared.discard(key)
        self._identity_cache.pop(key,None)

    def raw_get(self, key, default=None):return self._tables.get(key, default)
    def raw_items(self):return self._tables.items()
    def raw_values(self):return self._tables.values()

    def __deepcopy__(self, memo):
        owned = TableStore()
        memo[id(self)] = owned
        owned._identity_cache = dict(self._identity_cache)
        for key, rows in self._tables.items():
            if id(rows) in memo:
                owned._tables[key] = memo[id(rows)]
            else:
                owned._tables[key] = rows
                owned._shared.add(key)
                self._shared.add(key)
        return owned

    def shared_identities(self, key, collect):
        rows = self._tables[key]
        if key not in self._identity_cache or self._identity_cache[key][0] is not rows:
            self._identity_cache[key] = (rows, collect(rows))
        return self._identity_cache[key][1]
