"""Freeze source corpus and manually source-labelled development query families."""
import argparse,hashlib,json,sys,time
from pathlib import Path
V=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();assert not args.output.exists();args.output.mkdir(parents=True)
    sys.path[:0]=[str(V/'development/stages/B00-parent31/code'),str(V/'code/tests')]
    from analyzer.project import Project
    from analyzer.frontend import Frontend
    from analyzer.contracts import ContractIndex
    import analyzer
    analyzer.__path__.append(str(V/'code/analyzer'))
    from analyzer.retrieval_sources import documents
    from builders import build
    unicode_root=args.output/'unicode-source'
    build(unicode_root,{'Catalog.java':'''import java.util.*;import org.springframework.web.bind.annotation.*;
      class Item{public String title;}class Catalog{
        @GetMapping("/каталог")List<Item> показатьКаталог(){return new ArrayList<>();}
        @PostMapping("/заявки")Item создатьЗаявку(@RequestBody Item item){return item;}}'''})
    projects={
      'piggymetrics':V/'validation_inputs/piggymetrics',
      'cart':V/'validation_inputs/shopping-cart',
      'petclinic':V/'validation_inputs/legacy-real/petclinic-customers',
      'unicode':unicode_root,
      'trainticket':V.parents[1]/'tt-challenge'}
    protocol={'schema':'source-retrieval-protocol/1','split_policy':'All available applications/families are development/regression. train/test empty; real transfer not_run.',
      'labels':'Manual engineering reading of named source methods, annotations, parameters and DTOs; no analyzer predictions used as labels.',
      'oracle_scope':'Full acceptable handler set for labelled queries; partial downstream required-edge oracles remain partial.',
      'k':[1,3,6],'metrics':['top1','recall@1/3/6','MRR','coverage','false_accept','false_reject'],
      'chunks':{'tokens':192,'max_per_handler':8,'neighbors':0,'splitting':'whole AST nodes; oversized leaves omitted'},
      'bm25':{'k1':1.2,'b':0.75,'extra_weight':0.15},
      'refusal':{'min_content_terms':1,'relative_margin':0.08,'same_handler_ui_ties':'not endpoint ambiguity'},
      'budgets':{'path_limit':4,'completion_policy':'unchanged'},
      'A':'Exact B00-parent31 ContractIndex; historical clipping retained',
      'B':'Unicode/camel/snake source facts + bounded AST chunks on identical semantic engine',
      'C_D':'conditional; not_run without permitted pinned offline runtime and resource profile',
      'transfer_inputs_needed':['real Java/Spring domain A source/config/skeleton/context/explicit+NL chains and independently checked oracle',
        'real Java/Spring domain B same complete package; application/family held out before tuning']}
    (args.output/'protocol.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2)+'\n')
    queries=[];corpus={};cost=[];indexes={}
    for name,root in projects.items():
        started=time.perf_counter()
        if name=='trainticket':p=Project(root/'skeleton/trainticket.json.gz',root/'targets/trainticket')
        else:p=Project(root/'skeleton.json',root)
        f=Frontend(p);index=ContractIndex(p,f);indexes[name]=(p,index)
        docs=documents(p,index.contracts)
        # Identical source fact/chunk inputs are available to every candidate.
        corpus[name]={'documents':docs,'contracts':len(index.contracts),'handlers':len({c['entry'] for c in index.contracts.values()}),
            'source_files':{file:hashlib.sha256(data).hexdigest() for file,data in p.sources.items()}}
        cost.append({'project':name,'preparation_seconds':time.perf_counter()-started,'contracts':len(index.contracts)})
    def add(project,family,owner,method,actions,kind='answer',verb=None,origin='literal/context; no credential inferred'):
        p,index=indexes[project]
        entries=sorted({c['entry'] for c in index.contracts.values() if p.methods[c['entry']]['name'] in method.split('|')
                        and p.nodes[p.methods[c['entry']]['owner']]['fqn'].rsplit('.',1)[-1] in owner.split('|')
                        and (verb is None or c['verb']==verb)}) if owner else []
        assert bool(entries)==(kind!='no-handler'),(project,owner,method,entries)
        evidence=[{'entry':mid,'file':p.methods[mid]['file'],'line':p.methods[mid].get('line'),
             'source_sha256':hashlib.sha256(p.sources[p.methods[mid]['file']]).hexdigest()} for mid in entries]
        for language,action in actions:
            queries.append({'id':f'{project}/{family}/{len(queries)}','project':project,'family':project+'/'+family,
                'split':'development','language':language,'action':action,'kind':kind,'acceptable_entries':entries,
                'requires_refusal':kind in ('no-handler','ambiguous'),'argument_origin':origin,'evidence':evidence})
    add('piggymetrics','current-account','AccountController','getCurrentAccount',[
        ('en','Read current account'),('en','Show my account'),('ru','Показать текущий счёт')],origin='authenticated principal from real login/session producer; missing principal stays unknown')
    add('piggymetrics','named-account','AccountController','getAccountByName',[('en','Find account by name demo'),('ru','Показать account по name demo')])
    add('piggymetrics','create-account','AccountController','createNewAccount',[('en','Create account username=alice password=fixture'),('ru','Создать новый account')])
    add('piggymetrics','update-account','AccountController','saveCurrentAccount',[('en','Update current account'),('ru','Обновить текущий счёт')])
    add('piggymetrics','ambiguous-account','AccountController','getCurrentAccount|getAccountByName',[('en','Read account'),('ru','Показать account')],kind='ambiguous')
    add('piggymetrics','current-statistics','StatisticsController','getCurrentAccountStatistics',[('en','Read current account statistics'),('ru','Показать текущую статистику')])
    add('piggymetrics','named-statistics','StatisticsController','getStatisticsByAccountName',[('en','Find statistics by accountName demo')])
    add('piggymetrics','create-user','UserController','createUser',[('en','Create user username=alice password=fixture')])
    add('piggymetrics','missing-route','','',[('en','Delete all account statistics'),('ru','Удалить все счета')],kind='no-handler')
    for family,owner,method,en,ru in [
      ('create-order','OrderController','create','Create order customerId=1','Создать заказ'),
      ('cancel-order','OrderController','cancel','Cancel order id=1','Отменить заказ'),
      ('pay-order','OrderController','pay','Mark order as paid id=1','Пометить заказ оплаченным'),
      ('revert-order','OrderController','revertPayment','Revert order payment id=1','Вернуть заказ в ожидание оплаты'),
      ('get-order','OrderController','getById','Get order by id=1','Показать заказ по идентификатору'),
      ('list-orders','OrderController','listByCustomer','List orders for customerId=1','Показать заказы клиента'),
      ('process-payment','PaymentController','process','Process payment for orderId=1','Провести платёж'),
      ('refund-payment','PaymentController','refund','Refund payment id=1','Вернуть деньги за платёж'),
      ('get-payment','PaymentController','getById','Get payment by id=1','Показать платёж'),
      ('list-payments','PaymentController','getByOrder','List payments for orderId=1','Показать платежи заказа')]:
        add('cart',family,owner,method,[('en',en),('ru',ru)])
    add('cart','semantic-refund','PaymentController','refund',[('en','Return money for the earlier charge')],origin='previous response payment ID; missing producer must refuse binding')
    add('cart','no-handler','','',[('en','Delete every payment'),('en','Export an invoice to a PDF file')],kind='no-handler')
    add('petclinic','list-owners','OwnerResource','findAll',[('en','List owners'),('ru','Показать всех владельцев')])
    add('petclinic','get-owner','OwnerResource','findOwner',[('en','Get owner by ownerId=1')])
    add('petclinic','create-owner','OwnerResource','createOwner',[('en','Create owner'),('ru','Создать владельца')])
    add('petclinic','update-owner','OwnerResource','updateOwner',[('en','Update owner ownerId=1')])
    add('petclinic','pet-types','PetResource','getPetTypes',[('en','List pet types'),('en','Show available kinds of pets')])
    add('petclinic','find-pet','PetResource','findPet',[('en','Find pet petId=1')])
    add('petclinic','create-pet','PetResource','processCreationForm',[('en','Create pet for ownerId=1')])
    add('petclinic','no-handler','','',[('en','Delete owner ownerId=1')],kind='no-handler')
    add('unicode','catalog','Catalog','показатьКаталог',[('ru','Показать каталог'),('ru','Открыть каталог')])
    add('unicode','create','Catalog','создатьЗаявку',[('ru','Создать заявку title=дрель')])
    add('unicode','no-handler','','',[('ru','Уничтожить каталог')],kind='no-handler')
    for project,url,owner,method in [('cart','GET /api/payments?orderId=1','PaymentController','getByOrder'),
        ('cart','PATCH /api/payments/1/refund','PaymentController','refund')]:
        add(project,'explicit-'+method,owner,method,[('explicit',url)],origin='explicit HTTP literal control; retrieval bypass')
    for name,data in [('corpus.json',corpus),('queries.json',queries),('preparation.json',cost)]:
        (args.output/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    manifest={p.relative_to(args.output).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(args.output.rglob('*')) if p.is_file()}
    (args.output/'sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'queries':len(queries),'projects':{p:c['contracts'] for p,c in corpus.items()},'test_queries':0,'transfer':'not_run'}))


if __name__=='__main__':main()
