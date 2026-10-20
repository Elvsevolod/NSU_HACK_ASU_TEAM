"""Native payload carriers with separately observed Java boxed classes.

Payloads stay ordinary Python values and aliases keep sharing them. Observed
runtime classes live only in parallel metadata; no kind is ever inferred from
a Python payload shape, and no conversion, cast or serialization is modeled.
"""
from copy import deepcopy
from .java_collections import JavaIdentity


class JavaFrame(dict):
    """A frame whose kind metadata is separate from native payloads.

    kinds maps each present name to an observed native class string, or None
    when there is no evidence. Ordinary writes, updates and removals drop
    evidence; only set_value records an observed kind.
    """
    def __init__(self, values=None, kinds=None):
        super().__init__() if values is None else super().__init__(values)
        self.kinds = {name: kinds.get(name) if kinds is not None else None for name in self}

    def __setitem__(self, name, value):
        super().__setitem__(name, value)
        self.kinds[name] = None

    def __delitem__(self, name):
        super().__delitem__(name)
        self.kinds.pop(name, None)

    def set_value(self, name, value, kind=None):
        """Write payload and observed kind atomically; None means unknown."""
        super().__setitem__(name, value)
        self.kinds[name] = kind

    def update(self, *args, **kwargs):
        for name, value in dict(*args, **kwargs).items():
            self[name] = value

    def __ior__(self, other):
        self.update(other)
        return self

    def setdefault(self, name, default=None):
        if name in self:
            return self[name]
        self[name] = default
        return default

    def pop(self, name, *default):
        value = super().pop(name, *default)
        self.kinds.pop(name, None)
        return value

    def popitem(self):
        name, value = super().popitem()
        self.kinds.pop(name, None)
        return name, value

    def clear(self):
        super().clear()
        self.kinds.clear()

    def copy(self):
        """Shallow clone: shared payloads, copied evidence, new frame."""
        return JavaFrame(self, self.kinds)

    def __copy__(self):
        return self.copy()

    def __deepcopy__(self, memo):
        if id(self) in memo:
            return memo[id(self)]
        result = JavaFrame()
        memo[id(self)] = result
        for name, value in self.items():
            dict.__setitem__(result, name, deepcopy(value, memo))
        result.kinds = deepcopy(self.kinds, memo)
        return result


class StaticCells(JavaFrame):
    """Typed static storage, separately tracked from lexical frames at joins."""


class JavaList(list):
    """A list allocation with one observed class per index.

    kinds is parallel to the payload: kinds[i] is the observed native class of
    self[i], or None when unknown. Payloads are never inspected. java_identity
    is the allocation token shared by alias-preserving deepcopies.
    """
    def __init__(self, values=(), kinds=None, identity=...):
        items = list(values)
        super().__init__(items)
        if kinds is None:
            self.kinds = [None] * len(items)
        else:
            evidence = list(kinds)
            if len(evidence) != len(items):
                raise ValueError('kinds must match values length')
            self.kinds = evidence
        self.java_identity = JavaIdentity() if identity is ... else identity
        self.structural_version=0
        self.opaque=False
        self.fixed_size=False
        self.flavor='ArrayList'
        self.order_known=True

    def append(self, value, kind=None):
        super().append(value)
        self.kinds.append(kind)
        self.structural_version=None if self.structural_version is None else self.structural_version+1

    def extend(self, values, kinds=None):
        items = list(values)
        if kinds is None:
            evidence = list(values.kinds) if isinstance(values, JavaList) else [None] * len(items)
        else:
            evidence = list(kinds)
            if len(evidence) != len(items):
                raise ValueError('kinds must match values length')
        super().extend(items)
        self.kinds.extend(evidence)
        if items:self.structural_version=None if self.structural_version is None else self.structural_version+1

    def insert(self, index, value, kind=None):
        super().insert(index, value)
        self.kinds.insert(index, kind)
        self.structural_version=None if self.structural_version is None else self.structural_version+1

    def set_value(self, index, value, kind=None):
        """Set one element and its observed class atomically (None = unknown)."""
        if isinstance(index, slice):
            raise TypeError('set_value requires an integer index')
        super().__setitem__(index, value)
        self.kinds[index] = kind

    def pop(self, index=-1):
        value = super().pop(index)
        self.kinds.pop(index)
        self.structural_version=None if self.structural_version is None else self.structural_version+1
        return value

    def clear(self):
        super().clear()
        self.kinds.clear()
        self.opaque=False
        self.structural_version=None if self.structural_version is None else self.structural_version+1

    def remove(self, value):
        del self[self.index(value)]

    def reverse(self):
        super().reverse()
        self.kinds.reverse()

    def sort(self, *args, **kwargs):
        try:
            super().sort(*args, **kwargs)
        finally:
            # Python may reorder the payload before a comparison raises.
            self.kinds[:] = [None] * len(self)

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            previous=len(self)
            items = list(value)
            super().__setitem__(index, items)
            self.kinds[index] = [None] * len(items)
            if len(self)!=previous:self.structural_version=None if self.structural_version is None else self.structural_version+1
        else:
            super().__setitem__(index, value)
            self.kinds[index] = None

    def __delitem__(self, index):
        previous=len(self)
        super().__delitem__(index)
        del self.kinds[index]
        if len(self)!=previous:self.structural_version=None if self.structural_version is None else self.structural_version+1

    def __iadd__(self, values):
        self.extend(values)
        return self

    def __imul__(self, count):
        previous=len(self)
        super().__imul__(count)
        self.kinds *= count
        if len(self)!=previous:self.structural_version=None if self.structural_version is None else self.structural_version+1
        return self

    def copy(self):
        """Shallow clone: new allocation, copied kinds, shared elements."""
        result=JavaList(self,self.kinds)
        result.opaque,result.fixed_size,result.flavor=self.opaque,self.fixed_size,self.flavor
        result.order_known=self.order_known
        return result

    def __copy__(self):
        return self.copy()

    def __deepcopy__(self, memo):
        if id(self) in memo:
            return memo[id(self)]
        result = type(self).__new__(type(self))
        list.__init__(result)
        memo[id(self)] = result
        items = [deepcopy(item, memo) for item in self]
        list.extend(result, items)
        result.__dict__.update(deepcopy(self.__dict__,memo))
        return result


class JavaStream(dict):
    """Interpreter-owned sequential pipeline; JSON keys cannot forge a stream."""


class ServletObject(dict):
    """Dispatcher-owned servlet carrier, distinct from application JSON."""


class JavaHttpClient(dict):
    """A source-proven RestTemplate factory binding, not application JSON."""


class ReadOnlyList(JavaList):
    """Collections.unmodifiableList view; payload and kinds follow the backing."""
    def __init__(self,backing):
        self.backing=backing
        self.java_identity=JavaIdentity()
        self.fixed_size=True
        self.unmodifiable=True
        self.flavor='List'

    def __getattr__(self,name):
        if name in ('kinds','structural_version','opaque','order_known'):
            backing=self.__dict__.get('backing')
            if backing is not None:return getattr(backing,name)
        raise AttributeError(name)

    def __len__(self):return len(self.backing)
    def __iter__(self):return iter(self.backing)
    def __getitem__(self,index):return self.backing[index]
    def __contains__(self,value):return value in self.backing
    def index(self,*args):return self.backing.index(*args)
    def __eq__(self,other):return list(self)==list(other) if isinstance(other,list) else False


class JavaListIterator(dict):
    """Interpreter-owned cursor; JSON properties cannot forge this carrier."""
    def __init__(self,backing):
        super().__init__(backing=backing,index=0,last=None,expected=backing.structural_version)
        if not getattr(backing,'order_known',True):self['remaining']=list(range(len(backing)))
        self.java_identity=JavaIdentity()
