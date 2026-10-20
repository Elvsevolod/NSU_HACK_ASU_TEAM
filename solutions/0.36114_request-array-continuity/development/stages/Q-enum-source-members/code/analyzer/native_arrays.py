"""Explicit array evidence for typed adapter inputs; no JVM allocation model."""
from .native_storage import JavaList,ReadOnlyList


class JavaArray(JavaList):
    def __init__(self,values=(),component='',kinds=None,identity=...):
        super().__init__(values,kinds,identity)
        self.component=component

    def copy(self):
        return JavaArray(self,self.component,self.kinds)


class ArrayListView(ReadOnlyList):
    """Arrays.asList reference-array view; size is fixed, elements writable."""
    def __init__(self,backing):
        super().__init__(backing)
        self.unmodifiable=False
        self.flavor='Arrays.ArrayList'

    def set_value(self,index,value,kind=None):self.backing.set_value(index,value,kind)
    def __setitem__(self,index,value):self.backing[index]=value
