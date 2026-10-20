from builders import build


def test_hydration_preserves_null_and_typed_unknown_enum(tmp_path):
    project,database,_=build(tmp_path,{'Record.java':'''enum State { READY, DONE; }
      @Entity @Table(name="records") class Record {@Id String id;State state;}'''})
    resource=next(iter(project.entities))
    unknown={'__symbol__':'seed.state','__type__':'State','__constraints__':[]}
    for value in (None,unknown):
        row={'id':'R1','state':value}
        assert project.materialize(database,resource,row)['state']==value
