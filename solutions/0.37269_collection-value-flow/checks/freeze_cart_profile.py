"""Freeze a real source profile and a source-reviewed contract BEFORE inference."""
import hashlib,json,re,shutil,sys
from pathlib import Path
V=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(V/'code'),str(V/'code/tests')]
from builders import build
from analyzer.project import text,walk


def main():
    source=V/'development/holdout-candidate-cart';root=V/'validation_inputs/shopping-cart'
    assert not root.exists();root.mkdir()
    graph={'project':'shopping-cart','nodes':{},'edges':[]};identifiers={}
    for module in ('payment-service','order-service'):
        sources={str(p.relative_to(source/module)):p.read_text() for p in sorted((source/module/'src/main/java').rglob('*.java'))}
        project,_,ids=build(root/module,sources,module=module)
        local=project.skeleton
        # The fixture graph adapter extracts packages and ALL implements clauses;
        # these are source facts, never scenario/business rules in the analyzer.
        for tid,node in local['nodes'].items():
            if node['kind']!='type':continue
            file=node['file'];tree=project.trees[file]
            package=next((text(n).removeprefix('package').strip().rstrip(';') for n in tree.root_node.named_children if n.type=='package_declaration'),'')
            node['fqn']=(package+'.' if package else '')+node['fqn']
        for declaration in (n for tree in project.trees.values() for n in walk(tree.root_node) if n.type=='class_declaration'):
            owner=text(declaration.child_by_field_name('name'));header=text(declaration).split('{',1)[0]
            if 'implements' not in header:continue
            for parent in re.findall(r'\b\w+\b',header.split('implements',1)[1]):
                left='type:'+module+':'+owner;right='type:'+module+':'+parent
                if right not in local['nodes']:continue
                local['edges'].append({'source':left,'type':'implements','target':right})
                for imid,im in list(local['nodes'].items()):
                    if im.get('owner')!=right or im.get('kind')!='method':continue
                    for cmid,cm in list(local['nodes'].items()):
                        if cm.get('owner')==left and cm.get('name')==im['name'] and cm.get('params_as_written')==im.get('params_as_written'):
                            local['edges'].append({'source':cmid,'type':'overrides','target':imid})
        for node in local['nodes'].values():
            if node.get('file'):node['file']=module+'/'+node['file']
            for origin in node.get('origin',[]):origin['file']=module+'/'+origin['file']
        graph['nodes'].update(local['nodes']);graph['edges'].extend(local['edges'])
        identifiers.update({module+'.'+key:value for key,value in ids.items()})
        for name in ('pom.xml','src/main/resources/application.properties'):
            target=root/module/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/module/name,target)
    (root/'skeleton.json').write_text(json.dumps(graph,ensure_ascii=False,indent=2)+'\n')
    initial='''USE `payment-service`;
CREATE TABLE `payments` (
 `id` bigint, `order_id` bigint, `customer_id` bigint, `amount` decimal(10,2),
 `payment_method` varchar(30), `status` varchar(30), `created_at` timestamp
) ENGINE=InnoDB;
INSERT INTO `payments` VALUES (21,11,7,12.50,'CREDIT_CARD','APPROVED','2026-10-17 12:00:00'),(23,11,7,12.50,'CREDIT_CARD','REJECTED','2026-10-17 11:00:00'),(22,12,7,25.00,'DEBIT_CARD','APPROVED','2026-10-17 13:00:00');
USE `order-service`;
CREATE TABLE `orders` (
 `id` bigint, `customer_id` bigint, `customer_name` varchar(80), `customer_email` varchar(80), `status` varchar(30), `created_at` timestamp
) ENGINE=InnoDB;
INSERT INTO `orders` VALUES (11,7,'Ari','ari@example.test','PAID','2026-10-17 10:00:00'),(12,7,'Ari','ari@example.test','PAID','2026-10-17 10:30:00');
CREATE TABLE `order_details` (
 `id` bigint, `order_id` bigint, `product_id` bigint, `product_name` varchar(80), `quantity` int, `unit_price` decimal(10,2)
) ENGINE=InnoDB;
INSERT INTO `order_details` VALUES (31,11,51,'Notebook',2,6.25),(32,12,52,'Lamp',1,25.00);
'''
    (root/'initial.sql').write_text(initial.replace(', `',',\n `'))
    plan={'id':'cart-refund','steps':[
        {'n':1,'action':'GET /api/payments?orderId=11'},
        {'n':2,'action':'Refund the approved payment'},
        {'n':3,'action':'Read the refunded payment'},
        {'n':4,'action':'Read its order'},
        {'n':5,'action':'Refund the same payment again'},
        {'n':6,'action':'GET /api/payments/999'},
        {'n':7,'action':'Read the record'},
        {'n':8,'action':'GET /api/payments?orderId=11'}]}
    (root/'scenarios.json').write_text(json.dumps(plan,indent=2)+'\n')
    # Checker contract is authored from source, not generated from predictions.
    oracle={'version':1,'review':'single Codex source review, frozen before first target inference; no independent-reader claim',
      'source_commit':'64273c71575d61db8de6ba1a582b02f6a11103b3',
      'scope':'post-authentication controller/application/persistence HTTP profile; JWT filter, validation and server startup are outside this oracle',
      'steps':[
        {'n':1,'module':'payment-service','method':'GET','path':'/api/payments?orderId=11','status':200,
         'rows':[{'id':21,'orderId':11,'status':'APPROVED'},{'id':23,'orderId':11,'status':'REJECTED'}]},
        {'n':2,'module':'payment-service','method':'PATCH','path':'/api/payments/21/refund','status':200,
         'result_fields':{'id':21,'orderId':11,'status':'REFUNDED'},'changes':{'payments.21.status':'REFUNDED','orders.11.status':'PENDING'},
         'remote':{'method':'PATCH','path':'/api/orders/11/revert-payment'},'writes':['payments','orders','order_details']},
        {'n':3,'module':'payment-service','method':'GET','path':'/api/payments/21','status':200,'result_fields':{'id':21,'status':'REFUNDED'}},
        {'n':4,'module':'order-service','method':'GET','path':'/api/orders/11','status':200,'result_fields':{'id':11,'status':'PENDING','total':12.5}},
        {'n':5,'module':'payment-service','method':'PATCH','path':'/api/payments/21/refund','status':409,'error_code':'PAYMENT_ALREADY_PROCESSED','writes':[],'remote':None},
        {'n':6,'module':'payment-service','method':'GET','path':'/api/payments/999','status':404,'error_code':'PAYMENT_NOT_FOUND','writes':[]},
        {'n':7,'ambiguous':True,'must_not_choose':True,'state_unchanged':True},
        {'n':8,'module':'payment-service','method':'GET','path':'/api/payments?orderId=11','status':200,
         'rows':[{'id':21,'orderId':11,'status':'REFUNDED'},{'id':23,'orderId':11,'status':'REJECTED'}]}],
      'invariants':['payment 22 and order 12 are unchanged','payment/order/detail cardinalities remain 3/2/2',
                    'IDs for steps 2–5 must come from step 1/2 responses, not checker constants',
                    'repeat refund throws before save/remote; no rollback is invented around the prior successful request'],
      'expected_nonempty_relations':['executes','calls','remote','data'],
      'graph_oracle_status':'required source edges below; incomplete precision oracle, never score precision against this subset',
      'required_edges':[]}
    def mid(module,key):return identifiers[module+'-service.'+key]
    def edge(a,relation,b):oracle['required_edges'].append([a,relation,b])
    for left,right in [('PaymentController.getByOrder','PaymentQueryService.getByOrderId'),
                       ('PaymentQueryService.getByOrderId','GetPaymentsByOrderUseCase.execute'),
                       ('GetPaymentsByOrderUseCase.execute','PaymentPersistenceAdapter.findByOrderId'),
                       ('PaymentPersistenceAdapter.findByOrderId','PaymentPersistenceMapper.toDomain'),
                       ('PaymentPersistenceMapper.toDomain','Payment.reconstitute'),
                       ('PaymentController.refund','PaymentCommandService.refund'),
                       ('PaymentCommandService.refund','RefundPaymentUseCase.execute'),
                       ('RefundPaymentUseCase.execute','Payment.refund'),
                       ('RefundPaymentUseCase.execute','PaymentPersistenceAdapter.save'),
                       ('RefundPaymentUseCase.execute','OrderClientAdapter.revertToPending')]:edge(mid('payment',left),'calls',mid('payment',right))
    edge(mid('payment','OrderClientAdapter.revertToPending'),'remote',mid('order','OrderController.revertPayment'))
    for owner in ('PaymentPersistenceAdapter.findById','PaymentPersistenceAdapter.findByOrderId','PaymentPersistenceAdapter.save'):
        edge(mid('payment',owner),'data','res:table:payment-service.payments')
    for left,right in [('OrderController.revertPayment','OrderCommandService.revertToPending'),
                       ('OrderCommandService.revertToPending','RevertOrderToPendingUseCase.execute'),
                       ('RevertOrderToPendingUseCase.execute','Order.revertToPending')]:edge(mid('order',left),'calls',mid('order',right))
    edge(mid('order','OrderPersistenceAdapter.save'),'data','res:table:order-service.orders')
    (root/'oracle-v1.json').write_text(json.dumps(oracle,indent=2,ensure_ascii=False)+'\n')
    (root/'source-identifiers.json').write_text(json.dumps(identifiers,indent=2)+'\n')
    manifest={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file()}
    (V/'development/cart-freeze.json').write_text(json.dumps({'upstream':'https://github.com/Proyectosbme/shopping-cart-microservices-2026',
        'commit':oracle['source_commit'],'before_first_inference':True,'files':manifest,'targets_started':False,
        'selection_rejections':{'ewolff/microservice':'HAL/Spring Data REST/ModelAndView outside current HTTP scope',
          'piomin/sample-spring-microservices-new':'in-memory repositories; no nonempty database data relation'},
        'chronology':'Selected after C1/C2/S1/S2 implementation; frozen before any cart target inference or target-specific adjustment',
        'limits':['No new-holdout success claim until result/state/remote checks pass','Required-edge subset is not a full graph precision oracle']},indent=2)+'\n')
    print(json.dumps({'frozen_files':len(manifest),'oracle_sha256':manifest['oracle-v1.json'],'inference_has_not_run':True}))


if __name__=='__main__':main()
