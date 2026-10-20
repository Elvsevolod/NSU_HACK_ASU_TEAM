"""Record the source-native summary preconditions without target execution."""
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'code/tests'))
from test_native_equipment_contracts33 import equipment, RID
from analyzer.engine import Engine
from analyzer.native_storage import JavaList
from analyzer.state import ScenarioState

with TemporaryDirectory() as directory:
    p, db, ids = equipment(Path(directory))
    values = JavaList(); values.opaque = True
    e = Engine(p, ScenarioState(db, {'scoped_effect_summary': True}))
    e.run(ids['Approval.inspect'], {'id': 'A', 'unknown': values, 'inspectOnly': True})
    print(json.dumps({
        'outcome':e.outcome, 'warnings': sorted(e.warnings),
        'unscoped_state_assumptions':e.state.unscoped_state_assumptions,
        'boundary_had_transaction':e.boundary_had_transaction,
        'frames': [{'mid':mid,'node':node.type if node else None,
            'unknown_type':type(env.get('unknown')).__name__,
            'unknown_flavor':getattr(env.get('unknown'),'flavor',None),
            'unknown_opaque':getattr(env.get('unknown'),'opaque',None)} for mid,node,env in e.boundary_frames],
        'effects': e.effect_events, 'losses':e.loss_events,
        'rows':e.state.database.rows(p.nodes[RID]),
    }, default=str, indent=2))
