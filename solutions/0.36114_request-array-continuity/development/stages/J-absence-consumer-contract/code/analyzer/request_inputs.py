"""Flat grounding values with separately proven JSON property absence."""
class RequestInputs(dict):
    def __init__(self,values=(),body_omissions=None,flat_bodies=(),body_unknowns=None):
        super().__init__(values)
        self.body_omissions={name:frozenset(fields) for name,fields in (body_omissions or {}).items()}
        self.flat_bodies=frozenset(flat_bodies)
        self.body_unknowns={name:dict(fields) for name,fields in (body_unknowns or {}).items()}
