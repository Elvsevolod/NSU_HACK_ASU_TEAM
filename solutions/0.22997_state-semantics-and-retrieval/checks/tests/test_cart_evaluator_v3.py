"""Source-written fixture adds bound native arguments and server-side Void duties."""
from copy import deepcopy
import pytest
from test_cart_evaluator_v2 import positive as original
from cart_evaluator_v3 import evaluate


def positive():
    trace=original()
    for row in trace['steps']:
        n=row['n']
        if n==7:continue
        a=row['alternatives'][0];root=a['requests'][0]
        root['entry']=a['edges'][0][2]
        root['bound_arguments']=[{'name':'orderId' if n in (1,8) else 'id','declared_type':'java.lang.Long',
                                 'value':11 if n in (1,4,8) else 999 if n==6 else 21}]
        if n in (2,4):
            for target in ('OrderHttpMapper#toResponse(Order)','OrderPersistenceMapper#toDomain(OrderJpaEntity)',
                           'Order#total()','OrderDetail#subtotal()'):
                a['edges'].append(['','executes','method:order-service:'+target])
        if n==2:
            a['requests'][1].update(entry='method:order-service:OrderController#revertPayment(Long)',
                bound_arguments=[{'name':'id','declared_type':'java.lang.Long','value':11}])
            a['requests'][1]['request']['deployment']='order-service'
            a['responses'][0]['body']['total']=12.5
    return trace


def test_source_fixture_passes():
    result=evaluate(positive());assert result['passed'],result['errors']


@pytest.mark.parametrize('mutation',[
    'bool-argument','wrong-native-type','wrong-entry','wrong-remote-entry','wrong-remote-id',
    'wrong-port','missing-server-body','wrong-server-total','missing-server-mapper','missing-server-subtotal',
    'duplicate-request','boolean-request-id'])
def test_stronger_regression_obligation(mutation):
    t=positive();a=t['steps'][1]['alternatives'][0]
    if mutation=='bool-argument':a['requests'][0]['bound_arguments'][0]['value']=True
    elif mutation=='wrong-native-type':a['requests'][0]['bound_arguments'][0]['declared_type']='java.lang.String'
    elif mutation=='wrong-entry':a['requests'][0]['entry']='method:payment-service:PaymentController#getById(Long)'
    elif mutation=='wrong-remote-entry':a['requests'][1]['entry']=a['requests'][0]['entry']
    elif mutation=='wrong-remote-id':a['requests'][1]['bound_arguments'][0]['value']=12
    elif mutation=='wrong-port':a['requests'][1]['request']['url']='http://localhost:8084/api/orders/11/revert-payment'
    elif mutation=='missing-server-body':a['responses'][0].pop('body')
    elif mutation=='wrong-server-total':a['responses'][0]['body']['total']=0
    elif mutation.startswith('missing-server-'):
        prefix='OrderHttpMapper#' if mutation.endswith('mapper') else 'OrderDetail#'
        a['edges']=[e for e in a['edges'] if prefix not in e[2]]
    elif mutation=='duplicate-request':a['requests'].append(deepcopy(a['requests'][1]))
    elif mutation=='boolean-request-id':a['responses'][-1]['request']=True
    result=evaluate(t);assert not result['passed'],mutation
