"""New app-level retrieval holdout, frozen from source before query inference."""
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path
from analyzer.project import Project,text
from analyzer.frontend import Frontend
from analyzer.contracts import ContractIndex
from analyzer.retrieval_sources import documents

V=Path(__file__).resolve().parents[1]


def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def main():
    output=V/'development/real-retrieval-frozen-v1';output.mkdir(exist_ok=False)
    previous=V/'development/model-pilot/frozen-v2'
    old_corpus=json.loads((previous/'corpus.json').read_text())
    development=json.loads((previous/'labels-dev.json').read_text())
    corpus={key:value for key,value in old_corpus.items() if key in {q['project'] for q in development}}
    projects={};origins={}
    for name in ('employment','healthcare'):
        base=V/'development/holdout-preflight'/name
        project=Project(base/'prepared/skeleton.json',base/'source');projects[name]=project
        raw=documents(project,ContractIndex(project,Frontend(project)).contracts);units={}
        for row in raw.values():
            facts=row['facts'];mid=row['entry'];assert mid not in units
            prefix=f"{facts['owner']}.{facts['method']}\nHTTP {facts['http_method']} /{'/'.join(facts['route'])}\nRequest fields: "+json.dumps(facts['request_fields'],ensure_ascii=False,sort_keys=True)+'\n'
            content=prefix+text(project.ast[mid])
            units[mid]={'entry':mid,'file':row['file'],'line':row['line'],'source_sha256':row['source_sha256'],
                'text':content,'context_text':content,'source_chunks':row['chunks']}
        corpus[name]={'documents':units,'candidate_pool':sorted(units),'root_relative_to_variant':(base/'source').relative_to(V).as_posix()}
        origins[name]={'origin_sha256':hashlib.sha256((base/'origin.json').read_bytes()).hexdigest(),
            'revision':json.loads((base/'origin.json').read_text())['revision'],
            'skeleton_sha256':hashlib.sha256((base/'prepared/skeleton.json').read_bytes()).hexdigest()}
    def entry(project,owner,name,count):
        p=projects[project]
        found=[mid for mid,m in p.methods.items() if p.nodes[m['owner']]['fqn'].endswith('.'+owner)
            and m['name']==name and len(m['params_as_written'])==count]
        assert len(found)==1,(project,owner,name,count,found)
        return found[0]
    spec={
      'employment':[
        ('vacancy-create','JobController','createJob',1,'Advertise a new vacancy titled Analyst for employer 1.','Опубликуй новую вакансию аналитика у работодателя 1.'),
        ('vacancy-read','JobController','getJob',1,'Show vacancy 10 with its employer details and reviews.','Покажи вакансию 10 вместе с работодателем и отзывами.'),
        ('vacancy-update','JobController','updateJob',2,'Change the location and salary range of vacancy 10.','Измени местоположение и диапазон зарплаты вакансии 10.'),
        ('vacancy-delete','JobController','deleteJob',1,'Remove vacancy 10 from the job board.','Удали вакансию 10 с доски объявлений.'),
        ('employer-create','CompanyController','createCompany',1,'Register a new employer profile named North with a short description.','Зарегистрируй нового работодателя North с кратким описанием.'),
        ('employer-read','CompanyController','getCompany',1,'Read employer profile 1.','Прочитай карточку работодателя 1.'),
        ('employer-update','CompanyController','updateCompany',2,'Change the name and description of employer 1.','Измени название и описание работодателя 1.'),
        ('review-update','ReviewController','updateReview',2,'Revise the title, text and rating of review 4.','Измени заголовок, текст и оценку отзыва 4.'),
      ],
      'healthcare':[
        ('patient-create','PatientController','create',1,'Register a new patient named Alex with age 35 and phone 1001.','Зарегистрируй пациента Алекс, возраст 35, телефон 1001.'),
        ('patient-read','PatientController','getById',1,'Read the clinical profile of patient 10.','Прочитай медицинскую карточку пациента 10.'),
        ('patient-update','PatientController','update',2,'Change the name, age and phone of patient 10.','Измени имя, возраст и телефон пациента 10.'),
        ('patient-delete','PatientController','delete',1,'Remove the patient record with id 10.','Удали запись пациента с идентификатором 10.'),
        ('physician-create','DoctorController','create',1,'Add a physician named Vera specializing in cardiology.','Добавь врача Веру со специализацией кардиология.'),
        ('physician-read','DoctorController','getById',1,'Show the profile and experience of physician 20.','Покажи карточку и стаж врача 20.'),
        ('physician-update','DoctorController','update',2,'Change the specialization and phone of physician 20.','Измени специализацию и телефон врача 20.'),
        ('physician-patient','DoctorController','getDoctorWithPatient',2,'Show physician 20 together with the clinical record of patient 10.','Покажи врача 20 вместе с медицинской карточкой пациента 10.'),
      ]}
    labels=[]
    for project,rows in spec.items():
        for family,owner,name,count,en,ru in rows:
            mid=entry(project,owner,name,count)
            for language,action in (('en',en),('ru',ru)):
                labels.append({'id':project+'/'+family+'/'+language,'project':project,'family':project+'/'+family,
                    'language':language,'action':action,'acceptable_entries':[mid],'kind':'answer','requires_refusal':False,'split':'test',
                    'label_basis':'Independent pinned controller annotations and service-body reading before any analyzer/model query prediction.'})
        owner_names=('JobController','CompanyController','ReviewController') if project=='employment' else ('PatientController','DoctorController')
        method_names=('deleteJob','deleteCompany','deleteReview') if project=='employment' else ('delete','delete')
        ambiguous=[entry(project,owner,name,1) for owner,name in zip(owner_names,method_names)]
        for family,acceptable,kind,en,ru in [
            ('ambiguous-delete',ambiguous,'ambiguous','Delete the record with id 10.','Удали запись с идентификатором 10.'),
            ('no-sms',[],'no-handler','Send an SMS text message to phone 1001.','Отправь SMS на номер телефона 1001.')]:
            for language,action in (('en',en),('ru',ru)):
                labels.append({'id':project+'/'+family+'/'+language,'project':project,'family':project+'/'+family,'language':language,
                    'action':action,'acceptable_entries':acceptable,'kind':kind,'requires_refusal':True,'split':'test',
                    'label_basis':'No entity qualification for deletion; no SMS handler in the selected production services. Source-only label, not an analyzer answer.'})
    for q in development+labels:assert set(q['acceptable_entries'])<=set(corpus[q['project']]['candidate_pool']),q['id']
    protocol=json.loads((previous/'protocol.json').read_text())
    protocol.update(frozen_at=datetime.now(timezone.utc).isoformat(),test='40 new RU/EN retrieval queries, split by two new applications; full semantic oracle remains separate and not yet frozen',
        development='Exactly the previous 32 organization/library development queries and source documents; no new tuning data',
        new_projects=origins,context_ablation='Not requested in this extension; base text identical for all compared modes',
        model_selection='Keep CodeRank selected previously by development; do not reselect model/thresholds using these test labels',
        semantics='Retrieval-only extension. It does not complete real graph/state/HTTP/error transfer requirements.',
        preregistered_comparison='Common Unicode BM25 and previously selected CodeRank; all other models remain separately measured historical pilots',
        selection_source='benchmark/model-selection-dev.json')
    save(output/'corpus.json',corpus);save(output/'labels-dev.json',development);save(output/'labels-test.json',labels)
    save(output/'actions.json',[{k:q[k] for k in ('id','project','action','language','split')} for q in development+labels])
    save(output/'protocol.json',protocol)
    save(output/'sha256.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()})
    print(json.dumps({'test_queries':len(labels),'test_answer':sum(not q['requires_refusal'] for q in labels),
        'new_handlers':{p:len(corpus[p]['documents']) for p in projects},'source_only_preparation':True,'query_inference_run':False}))


if __name__=='__main__':main()
