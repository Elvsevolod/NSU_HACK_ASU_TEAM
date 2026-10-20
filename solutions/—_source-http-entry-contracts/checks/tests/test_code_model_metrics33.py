import pytest
from evaluate_code_models import metrics,rows,validate_predictions


def label(key,refuse=False,valid=None,kind='answer'):
    return {'id':key,'requires_refusal':refuse,'acceptable_entries':['a'] if valid is None else valid,'kind':kind}


def prediction(key,score=.8):
    return {'id':key,'candidate_pool':['a','b'],'ranking':[{'entry':'a','score':score},{'entry':'b','score':score-.1}]}


def test_answer_and_ambiguity_have_distinct_denominators():
    labels=[label('ok'),label('ambiguous',True,['a','b'],'ambiguous'),label('none',True,[],'no-handler')]
    result=metrics(rows(labels,[prediction(q['id']) for q in labels],(.5,0)))
    assert result['answer_queries']==1 and result['refusal_queries']==2
    assert result['accepted_correct']==1 and result['false_accepts']==2 and result['wrong_accepts']==0
    assert result['recall_at_1']=={'count':1,'denominator':1,'rate':1}


def test_false_reject_is_not_a_ranking_error():
    result=metrics(rows([label('x')],[prediction('x')],(.9,0)))
    assert result['mrr']==1 and result['false_rejects']==1 and result['wrong_accepts']==0


def test_accepted_wrong_is_separate_from_false_accept():
    result=metrics(rows([label('x',valid=['b'])],[prediction('x')],(.5,0)))
    assert result['wrong_accepts']==1 and result['false_accepts']==0 and result['mrr']==.5


@pytest.mark.parametrize('case',['empty','duplicate','foreign','nan','unsorted'])
def test_incomplete_or_corrupt_worker_output_cannot_be_a_valid_pilot(case):
    actions=[{'id':'x','project':'p'}];corpus={'p':{'candidate_pool':['a','b']}}
    data=[prediction('x')]
    if case=='empty':data=[]
    elif case=='duplicate':data*=2
    elif case=='foreign':data[0]['candidate_pool']=['a','alien']
    elif case=='nan':data[0]['ranking'][0]['score']=float('nan')
    else:data[0]['ranking'].reverse()
    with pytest.raises(AssertionError):validate_predictions(data,actions,corpus)
