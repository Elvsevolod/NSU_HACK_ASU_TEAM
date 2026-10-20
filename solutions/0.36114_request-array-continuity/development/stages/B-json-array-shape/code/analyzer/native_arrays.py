"""Explicit array evidence for typed adapter inputs; no JVM allocation model."""
from .native_storage import JavaList


class JavaArray(JavaList):
    def __init__(self,values=(),component='',kinds=None,identity=...):
        super().__init__(values,kinds,identity)
        self.component=component

    def copy(self):
        return JavaArray(self,self.component,self.kinds)
