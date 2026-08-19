"""
Stub rpds-py module for offline use.

rpds-py provides Rust-based persistent data structures (HashTrieMap,
HashTrieSet, List). They are used by the `referencing` package which
is a dependency of `jsonschema` → `nbformat` → `nbconvert`.

For static notebook-to-markdown conversion, the performance benefits
of Rust-backed structures are irrelevant. This stub provides pure-Python
equivalents that are API-compatible for the subset used by `referencing`.
"""

import types

__version__ = "0.27.1"


class HashTrieMap:
    """Pure-Python stub for rpds.HashTrieMap.

    A persistent (immutable) hash trie map. This stub uses a regular dict
    copy-on-write approach — less efficient but API-compatible.
    """

    __slots__ = ("_data",)

    def __init__(self, _data=None, **kwargs):
        d = dict(_data or {})
        d.update(kwargs)
        self._data = d

    @classmethod
    def convert(cls, mapping):
        if isinstance(mapping, HashTrieMap):
            return mapping
        return cls(dict(mapping))

    def insert(self, key, value):
        new = HashTrieMap(self._data)
        new._data[key] = value
        return new

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __getitem__(self, key):
        return self._data[key]

    def __contains__(self, key):
        return key in self._data

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __eq__(self, other):
        if isinstance(other, HashTrieMap):
            return self._data == other._data
        return self._data == other

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    def remove(self, key):
        new = HashTrieMap(self._data)
        new._data.pop(key, None)
        return new

    def update(self, other):
        new = HashTrieMap(self._data)
        if isinstance(other, HashTrieMap):
            new._data.update(other._data)
        else:
            new._data.update(other)
        return new

    def is_disjoint(self, other):
        return not bool(set(self._data) & set(other._data if isinstance(other, HashTrieMap) else other))


class HashTrieSet:
    """Pure-Python stub for rpds.HashTrieSet."""

    __slots__ = ("_data",)

    def __init__(self, _data=None):
        self._data = set(_data or ())

    @classmethod
    def convert(cls, iterable):
        return cls(iterable)

    def insert(self, value):
        new = HashTrieSet(self._data)
        new._data.add(value)
        return new

    def remove(self, value):
        new = HashTrieSet(self._data)
        new._data.discard(value)
        return new

    def __contains__(self, item):
        return item in self._data

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __eq__(self, other):
        if isinstance(other, HashTrieSet):
            return self._data == other._data
        return self._data == other

    def is_subset(self, other):
        other_set = other._data if isinstance(other, HashTrieSet) else set(other)
        return self._data.issubset(other_set)

    def is_disjoint(self, other):
        other_set = other._data if isinstance(other, HashTrieSet) else set(other)
        return self._data.isdisjoint(other_set)

    def update(self, other):
        new = HashTrieSet(self._data)
        if isinstance(other, HashTrieSet):
            new._data.update(other._data)
        else:
            new._data.update(other)
        return new


class List:
    """Pure-Python stub for rpds.List (persistent linked list)."""

    __slots__ = ("_data",)

    def __init__(self, _data=None):
        self._data = list(_data or ())

    @classmethod
    def convert(cls, iterable):
        return cls(iterable)

    def push_front(self, value):
        new = List(self._data)
        new._data.insert(0, value)
        return new

    def first(self):
        if not self._data:
            raise IndexError("first from empty list")
        return self._data[0]

    def rest(self):
        return List(self._data[1:])

    def is_empty(self):
        return len(self._data) == 0

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __eq__(self, other):
        if isinstance(other, List):
            return self._data == other._data
        return self._data == list(other)


def install(modules=None):
    """Inject the stub into sys.modules so `import rpds` succeeds."""
    import sys
    if modules is None:
        modules = sys.modules

    try:
        import rpds  # noqa: F401
        return False
    except ImportError:
        pass

    mod = types.ModuleType("rpds")
    mod.__version__ = __version__
    mod.HashTrieMap = HashTrieMap
    mod.HashTrieSet = HashTrieSet
    mod.List = List
    modules["rpds"] = mod
    return True
