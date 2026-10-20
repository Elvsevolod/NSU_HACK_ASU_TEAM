"""Handwritten positive checker fixture; never an analyzer input or inference result."""
from copy import deepcopy
import json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cart_evaluator_v2 import evaluate,INPUTS


def positive():
    tables=json.loads((INPUTS/'checker-initial-rows-v2.json').read_text())
    payloads=[
      [{'id':21,'orderId':11,'status':'APPROVED'},{'id':23,'orderId':11,'status':'REJECTED'}],
      {'id':21,'orderId':11,'status':'REFUNDED'}, {'id':21,'status':'REFUNDED'},
      {'id':11,'status':'PENDING','total':12.5},
      {'error_code':'PAYMENT_ALREADY_PROCESSED'}, {'error_code':'PAYMENT_NOT_FOUND'},None,
      [{'id':21,'orderId':11,'status':'REFUNDED'},{'id':23,'orderId':11,'status':'REJECTED'}]]
    paths=['/api/payments?orderId=11','/api/payments/21/refund','/api/payments/21','/api/orders/11','/api/payments/21/refund','/api/payments/999',None,'/api/payments?orderId=11']
    rows=[]
    for n in range(1,9):
        before={'tables':deepcopy(tables),'unknown_tables':[]}
        if n==2:
            tables['payment-service.payments'][0]['status']='REFUNDED';tables['order-service.orders'][0]['status']='PENDING'
        after={'tables':deepcopy(tables),'unknown_tables':[]}
        if n==7:
            rows.append({'n':n,'alternatives':[],'state_before':before,'state_after':after});continue
        module='order-service' if n==4 else 'payment-service'
        req={'deployment':module,'method':'PATCH' if n in (2,5) else 'GET','url':paths[n-1]}
        owner='OrderController' if n==4 else 'PaymentController'
        method='refund(Long)' if n in (2,5) else 'getByOrder(Long)' if n in (1,8) else 'getById(Long)'
        entry=f'method:{module}:{owner}#{method}'
        edges=[['','executes',entry]]
        def method(m,name):return 'method:'+m+':'+name
        def call(left,right,m='payment-service'):edges.append([method(m,left),'calls',method(m,right)])
        def data(left,table,m='payment-service'):edges.append([method(m,left),'data','res:table:'+m+'.'+table])
        if n in (1,8):
            call('PaymentController#getByOrder(Long)','PaymentQueryService#getByOrderId(Long)')
            call('PaymentQueryService#getByOrderId(Long)','GetPaymentsByOrderUseCase#execute(Long)')
            call('GetPaymentsByOrderUseCase#execute(Long)','PaymentPersistenceAdapter#findByOrderId(Long)')
            call('PaymentPersistenceAdapter#findByOrderId(Long)','PaymentPersistenceMapper#toDomain(PaymentJpaEntity)')
            call('PaymentPersistenceMapper#toDomain(PaymentJpaEntity)','Payment#reconstitute(Long,Long,Long,BigDecimal,PaymentMethod,PaymentStatus,LocalDateTime)')
            data('PaymentPersistenceAdapter#findByOrderId(Long)','payments')
        if n in (2,3,5,6):data('PaymentPersistenceAdapter#findById(Long)','payments')
        if n==2:
            call('PaymentController#refund(Long)','PaymentCommandService#refund(Long)')
            call('PaymentCommandService#refund(Long)','RefundPaymentUseCase#execute(Long)')
            for target in ('Payment#refund()','PaymentPersistenceAdapter#save(Payment)','OrderClientAdapter#revertToPending(Long)'):
                call('RefundPaymentUseCase#execute(Long)',target)
            call('OrderController#revertPayment(Long)','OrderCommandService#revertToPending(Long)','order-service')
            call('OrderCommandService#revertToPending(Long)','RevertOrderToPendingUseCase#execute(Long)','order-service')
            call('RevertOrderToPendingUseCase#execute(Long)','Order#revertToPending()','order-service')
            data('PaymentPersistenceAdapter#save(Payment)','payments');data('OrderPersistenceAdapter#save(Order)','orders','order-service')
        events=[{'id':1,'request':deepcopy(req)}]
        responses=[{'request':1,'status':409 if n==5 else 404 if n==6 else 200,'body':deepcopy(payloads[n-1])}]
        ops=[]
        if n==2:
            edges.append(['method:payment-service:OrderClientAdapter#revertToPending(Long)','remote','method:order-service:OrderController#revertPayment(Long)'])
            events.append({'id':2,'request':{'method':'PATCH','url':'http://localhost:8083/api/orders/11/revert-payment'}})
            responses.insert(0,{'request':2,'status':200,'body':{'id':11,'status':'PENDING'}})
            for m,t in [('payment-service','payments'),('order-service','orders')]:
                ops.append({'resource':f'res:table:{m}.{t}','operation':'save','datastore_event':True})
        row={'n':n,'request':req,'state_before':before,'state_after':after,'alternatives':[{'outcome':'returned','result':payloads[n-1],
               'requests':events,'responses':responses,'edges':edges,'data_operations':ops,'state_after':deepcopy(after)}]}
        if n in (2,3,4,5):row['producer']={'producer_step':1,'payment_id':21,'order_id':11,'source':'actual root result'}
        rows.append(row)
    return {'entry_boundary':'application_after_authentication','security_evaluated':False,'steps':rows}


def test_positive_fixture_is_accepted():
    result=evaluate(positive());assert result['passed'],result['errors']


@pytest.mark.parametrize('mutation',[
 'missing-step','duplicate-step','wrong-payment','wrong-producer-type','lost-producer','wrong-status','lost-code',
 'wrong-root','swapped-responses','foreign-row','write-after-refusal','remote-other-step','ambiguous-write',
 'arbitrary-read','missing-execute','duplicate-row','wrong-row-type','missing-state-before','lost-scope','lost-body','missing-call','missing-data'])
def test_meaningful_negative_is_rejected(mutation):
    t=positive();rows=t['steps'];a=rows[1]['alternatives'][0]
    if mutation=='missing-step':rows.pop(2)
    elif mutation=='duplicate-step':rows[2]['n']=2
    elif mutation=='wrong-payment':rows[1]['request']['url']='/api/payments/22/refund'
    elif mutation=='wrong-producer-type':rows[1]['producer']['producer_step']=True
    elif mutation=='lost-producer':rows[1].pop('producer')
    elif mutation=='wrong-status':rows[4]['alternatives'][0]['responses'][0]['status']=200
    elif mutation=='lost-code':rows[4]['alternatives'][0]['result']={}
    elif mutation=='wrong-root':a['responses'][-1]['request']=2
    elif mutation=='swapped-responses':
        a['responses'][0]['request'],a['responses'][1]['request']=1,2
    elif mutation=='foreign-row':a['state_after']['tables']['payment-service.payments'][2]['amount']=0.0
    elif mutation=='write-after-refusal':rows[4]['alternatives'][0]['data_operations']=deepcopy(a['data_operations'])
    elif mutation=='remote-other-step':
        rows[2]['alternatives'][0]['edges'].append(a['edges'].pop())
    elif mutation=='ambiguous-write':rows[6]['alternatives']=[deepcopy(a),deepcopy(a)]
    elif mutation=='arbitrary-read':rows[6]['alternatives']=[deepcopy(rows[2]['alternatives'][0])]
    elif mutation=='missing-execute':a['edges'].pop(0)
    elif mutation=='duplicate-row':rows[0]['alternatives'][0]['result'][1]=deepcopy(rows[0]['alternatives'][0]['result'][0])
    elif mutation=='wrong-row-type':rows[0]['alternatives'][0]['result'][0]['id']=True
    elif mutation=='missing-state-before':rows[3].pop('state_before')
    elif mutation=='lost-scope':t.pop('entry_boundary')
    elif mutation in ('missing-call','missing-data'):
        rel={'missing-call':'calls','missing-data':'data'}[mutation];a['edges']=[e for e in a['edges'] if e[1]!=rel]
    elif mutation=='lost-body':a['responses'][-1].pop('body')
    result=evaluate(t);assert not result['passed'],mutation
    assert result['errors']


def test_historical_failed_trace_is_rejected():
    root=INPUTS.parents[1]/'development/cart-historical30'
    assert not evaluate(json.loads((root/'explicit.json').read_text()))['passed']
