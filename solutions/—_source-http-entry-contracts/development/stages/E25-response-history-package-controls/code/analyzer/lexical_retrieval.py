"""Optional source-fact lexical retriever; ranking supplies no execution facts."""
import re
from baseline_closure import BM25
from .contracts import ContractIndex,STOP,VERBS
from .retrieval_sources import documents,unicode_tokens

RU_VERBS={'показать':'get','просмотреть':'view','открыть':'open','читать':'read','найти':'find',
    'создать':'create','добавить':'add','зарегистрировать':'register','удалить':'delete',
    'обновить':'update','изменить':'change','войти':'login','оплатить':'pay'}
LANGUAGE_STOP=set('и или в на по для из с со у все всех новый новую текущий текущую'.split())


def tokens(value):
    return [RU_VERBS.get(word,word) for word in unicode_tokens(value) if word not in STOP|LANGUAGE_STOP]


def intent(value):
    value=re.sub(r'^as\b.*?,\s*|^(?:try\s+to|please)\s+','',str(value),flags=re.I)
    words=tokens(value)
    if words and words[0]=='repeat':
        if len(words)<2:return None
        verb=words[1];forms={verb}
        if verb.endswith('ing'):
            base=verb[:-3];forms.update((base,base+'e'))
            if len(base)>1 and base[-1]==base[-2]:forms.add(base[:-1])
        matches={i for i,group in enumerate(VERBS) if forms & group}
        return next(iter(matches)) if len(matches)==1 else None
    return next((i for i,group in enumerate(VERBS) if words and words[0] in group),None)


class LexicalContractIndex(ContractIndex):
    tokenize=staticmethod(tokens)
    query_intent=staticmethod(intent)

    def __init__(self,project,frontend):
        super().__init__(project,frontend)
        self.source_documents=documents(project,self.contracts)
        docs={key:tokens(row['fact_text']) for key,row in self.source_documents.items()}
        extra={key:tokens(' '.join(c['text'] for c in row['chunks'])) for key,row in self.source_documents.items()}
        self.bm25=BM25(docs);self.extra=BM25(extra)
        self.content={key:set(words) for key,words in docs.items()}
        self.last_decision={}

    def rank(self,action,active_page=None,scenario_text=''):
        ranked=super().rank(action,active_page,scenario_text)
        wanted=intent(action);verbs={word for group in VERBS for word in group}
        content=set(tokens(action))-verbs-{'id','name','current','my','by','earlier','please'}
        # A verb alone cannot establish a request. Nor does a high noun score
        # establish a source operation which contradicts the stated action.
        candidates=[row for row in ranked if content & self.content[row[1]] and not
            (wanted==2 and row[2]['verb']!='DELETE' and row[2]['intent']!=2)]
        entries=[]
        for row in candidates:
            if row[2]['entry'] not in [item[2]['entry'] for item in entries]:entries.append(row)
        reason=None
        if not candidates:reason='no source content/operation evidence'
        elif len(entries)>1 and entries[0][0]-entries[1][0] <= 0.08*max(entries[0][0],1e-12):
            reason='source endpoint scores within frozen refusal margin'
        self.last_decision={'accepted':reason is None,'reason':reason,'raw_top':[
            {'contract_id':key,'entry':c['entry'],'score':score} for score,key,c in candidates[:6]],
            'model_calls':0,'profile':'unicode-source-lexical/1'}
        return [] if reason else candidates
