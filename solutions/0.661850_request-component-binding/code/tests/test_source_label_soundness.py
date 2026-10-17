from analyzer.source_labels import field_aliases
from builders import build


def test_block_local_does_not_retype_field_after_its_scope(tmp_path):
    project, _, ids=build(tmp_path,{'Api.java':'''class Api {void submit(@RequestBody Batch input){}}
      class Batch {int premiumSlots;} class Invoice {int premiumSlots;}
      class Reader {Invoice shelf;
        int read(Batch batch){
          {Batch shelf=batch; int inside=shelf.getPremiumSlots();}
          int outside=shelf.getPremiumSlots(); return outside;
        }
      }'''})
    assert all(alias['label']!='outside' for aliases in field_aliases(project,ids['Api.submit']).values() for alias in aliases)


def test_custom_getter_is_not_assumed_to_read_same_named_field(tmp_path):
    project, _, ids=build(tmp_path,{'Api.java':'''class Api {void submit(@RequestBody Batch input){}}
      class Batch {int premiumSlots;int standardSlots;int getPremiumSlots(){return standardSlots;}}
      class Reader {int read(Batch batch){int priorityCount=batch.getPremiumSlots();return priorityCount;}}'''})
    assert 'premiumSlots' not in field_aliases(project,ids['Api.submit'])


def test_nested_local_class_does_not_retype_outer_receiver(tmp_path):
    project, _, ids=build(tmp_path,{'Api.java':'''class Api {void submit(@RequestBody Batch input){}}
      class Batch {int premiumSlots;} class Invoice {int premiumSlots;}
      class Reader {int read(Invoice source){
        class Inner {int ignored(Batch source){Batch nested=source;return nested.getPremiumSlots();}}
        int amount=source.getPremiumSlots();return amount;
      }}'''})
    assert all(alias['label']!='amount' for aliases in field_aliases(project,ids['Api.submit']).values() for alias in aliases)
