"""Independent source-engineered expectations, before opening new predictions.

Business literals below belong to test inputs/checkers, never the analyzer.
No inference module, saved answer, ranking output or model is imported here.
The full graph projection follows tt-challenge/REFERENCE.md, including its
exclusion of reflection-only getters/constructors and generated methods.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

V = Path(__file__).resolve().parents[1]
BASE = V / 'development/holdout-preflight'
OUTPUT = V / 'development/semantic-holdouts-frozen-v1'


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def variable(name):
    return {'$identity': name, 'native_kind': 'Long', 'fresh': True}


def previous(step, field='id'):
    return {'$response': step, 'path': [field], 'native_kind': 'Long'}


class SourceOracle:
    def __init__(self, name):
        self.name = name
        self.root = BASE / name
        self.graph = json.loads((self.root / 'prepared/skeleton.json').read_text())
        self.methods = {key: row for key, row in self.graph['nodes'].items() if row['kind'] == 'method'}
        self.evidence = {}

    def method(self, module, owner, name, arity=None):
        matches = [key for key, row in self.methods.items() if row['module'] == module and row['name'] == name
                   and self.graph['nodes'][row['owner']]['fqn'].endswith('.' + owner)
                   and (arity is None or len(row['params_as_written']) == arity)]
        assert len(matches) == 1, (module, owner, name, matches)
        key = matches[0]
        row = self.methods[key]
        self.evidence[key] = {'file': row['file'], 'line': row['line'], 'end': row['end'],
                              'sha256': sha(self.root / 'source' / row['file'])}
        return key

    def edges(self, entry, calls=(), data=(), remote=(), callbacks=()):
        executed = {entry, *callbacks}
        rows = set()
        for relation, pairs in [('calls', calls), ('remote', remote), ('data', data)]:
            for source, target in pairs:
                assert source in self.methods
                assert target in self.graph['nodes']
                rows.add((source, relation, target))
                executed.add(source)
                if relation != 'data':
                    executed.add(target)
        rows.update(('$scenario', 'executes', target) for target in executed)
        return [{'source': source, 'relation': relation, 'target': target} for source, relation, target in sorted(rows)]

    def step(self, action, entry, verb, route, parameters, result, status, state, *, body=None, calls=(),
             data=(), remote=(), callbacks=(), operations=(), requests=(), producer=None, value_limits=()):
        recipe = {'deployment': self.methods[entry]['module'], 'method': verb, 'route_template': route,
                  'parameters': parameters, 'headers': {}}
        if body is not None:
            recipe.update(body=body, headers={'content-type': ['application/json']})
        return {'actions': action, 'request_script': recipe,
                'expected': {'entry': entry, 'edges': self.edges(entry, calls, data, remote, callbacks),
                             'status': status, 'result': result, 'tables': deepcopy(state),
                             'operations': list(operations), 'remote_requests': list(requests),
                             'producer': producer, 'exploration_complete': True,
                             'graph_complete': True, 'persistent_rows_complete': True,
                             'value_limits': list(value_limits)}}


def healthcare():
    o = SourceOracle('healthcare')
    p = lambda owner, name: o.method('patient-service', owner, name)
    d = lambda owner, name: o.method('doctor-service', owner, name)
    pc = {name: p('PatientController', name) for name in ('create', 'getById', 'update', 'delete')}
    ps = {name: p('PatientServiceImpl', name) for name in ('createPatient', 'getPatientById', 'updatePatient', 'deletePatient')}
    dc = d('DoctorController', 'getDoctorWithPatient')
    ds = d('DoctorServiceImpl', 'getDoctorWithPatient')
    dg = d('DoctorServiceImpl', 'getDoctorById')
    exception = p('PatientNotFoundException', '<init>')
    advice = p('GlobalExceptionHandler', 'handlePatientNotFound')
    generic = d('GlobalExceptionHandler', 'handleGenericException')
    pt, dt = 'res:table:hospital_db.patients', 'res:table:hospital_db.doctors'
    doctor = {'id': 7, 'name': 'Dr Vale', 'specialization': 'Cardiology', 'experience': 12, 'phone': '701'}
    seeded = {'id': 11, 'name': 'Seed Patient', 'age': 45, 'gender': 'F', 'department': 'General', 'phone': '702'}
    incoming = {'name': 'Mira Bell', 'age': 29, 'gender': 'F', 'department': 'Cardiology', 'phone': '703'}
    changed = {**incoming, 'age': 30, 'department': 'Rehabilitation', 'phone': '704'}
    identity = variable('new_patient')
    current = {'hospital_db.doctors': [doctor], 'hospital_db.patients': [seeded]}
    initial = deepcopy(current)
    steps = []
    current['hospital_db.patients'].append({'id': identity, **incoming})
    steps.append(o.step({'en': 'Create a patient: ' + json.dumps(incoming), 'ru': 'Создать пациента: ' + json.dumps(incoming)},
        pc['create'], 'POST', '/patients', {}, {'id': identity, **incoming}, 200, current, body=incoming,
        calls=[(pc['create'], ps['createPatient'])], data=[(ps['createPatient'], pt)],
        operations=[{'method': ps['createPatient'], 'operation': 'save', 'table': pt, 'writes': True}],
        producer={'identity': 'new_patient', 'response_path': ['id'], 'origin': 'ORM generated identifier', 'native_kind': 'Long'}))
    def read_created(action):
        return o.step(action, pc['getById'], 'GET', '/patients/{id}', {'id': previous(1)}, current['hospital_db.patients'][-1], 200, current,
            calls=[(pc['getById'], ps['getPatientById'])], data=[(ps['getPatientById'], pt)],
            operations=[{'method': ps['getPatientById'], 'operation': 'findById', 'arguments': [identity], 'table': pt, 'writes': False}])
    steps.append(read_created({'en': 'Read the patient just created', 'ru': 'Прочитать только что созданного пациента'}))
    current['hospital_db.patients'][-1] = {'id': identity, **changed}
    calls = [(pc['update'], ps['updatePatient']), (ps['updatePatient'], ps['getPatientById'])]
    steps.append(o.step({'en': 'Update the patient just created: ' + json.dumps(changed), 'ru': 'Обновить только что созданного пациента: ' + json.dumps(changed)},
        pc['update'], 'PUT', '/patients/{id}', {'id': previous(1)}, {'id': identity, **changed}, 200, current, body=changed,
        calls=calls, data=[(ps['getPatientById'], pt), (ps['updatePatient'], pt)],
        operations=[{'method': ps['getPatientById'], 'operation': 'findById', 'arguments': [identity], 'table': pt, 'writes': False},
                    {'method': ps['updatePatient'], 'operation': 'save', 'table': pt, 'writes': True}]))
    steps.append(read_created({'en': 'Read the patient just created again', 'ru': 'Ещё раз прочитать только что созданного пациента'}))
    remote = [(ds, pc['getById'])]
    rcalls = [(dc, ds), (ds, dg), (pc['getById'], ps['getPatientById'])]
    rdata = [(dg, dt), (ps['getPatientById'], pt)]
    request = {'source': ds, 'target': pc['getById'], 'deployment': 'patient-service', 'method': 'GET',
               'path': ['patients', identity], 'query': {}, 'status': 200}
    steps.append(o.step({'en': 'Read doctor 7 together with the patient just created', 'ru': 'Получить врача с id=7 вместе с только что созданным пациентом'},
        dc, 'GET', '/doctors/{doctorId}/patient/{patientId}', {'doctorId': 7, 'patientId': previous(1)},
        {'doctor': doctor, 'patient': {'id': identity, **changed}}, 200, current,
        calls=rcalls, data=rdata, remote=remote, requests=[request]))
    current['hospital_db.patients'] = [seeded]
    steps.append(o.step({'en': 'Delete the patient just created', 'ru': 'Удалить только что созданного пациента'},
        pc['delete'], 'DELETE', '/patients/{id}', {'id': previous(1)}, None, 200, current,
        calls=[(pc['delete'], ps['deletePatient'])], data=[(ps['deletePatient'], pt)],
        operations=[{'method': ps['deletePatient'], 'operation': 'deleteById', 'arguments': [identity], 'table': pt, 'writes': True}]))
    error = {'timestamp': {'$native': 'LocalDateTime'}, 'message': {'$text': ['Patient not found with ID: ', identity]}, 'status': 404}
    for en, ru in [('Update the deleted patient again', 'Ещё раз обновить удалённого пациента'),
                   ('Repeat updating the deleted patient', 'Повторить обновление удалённого пациента')]:
        steps.append(o.step({'en': en + ': ' + json.dumps(changed), 'ru': ru + ': ' + json.dumps(changed)},
            pc['update'], 'PUT', '/patients/{id}', {'id': previous(1)}, error, 404, current, body=changed,
            calls=[*calls, (ps['getPatientById'], exception)], data=[(ps['getPatientById'], pt)], callbacks=[advice],
            operations=[{'method': ps['getPatientById'], 'operation': 'findById', 'arguments': [identity], 'table': pt, 'writes': False}]))
    steps.append(o.step({'en': 'Read doctor 7 together with the deleted patient', 'ru': 'Получить врача с id=7 вместе с удалённым пациентом'},
        dc, 'GET', '/doctors/{doctorId}/patient/{patientId}', {'doctorId': 7, 'patientId': previous(1)},
        {'timestamp': {'$native': 'LocalDateTime'}, 'message': {'$native': 'FeignExceptionMessage', 'response': error}, 'status': 500},
        500, current, calls=[*rcalls, (ps['getPatientById'], exception)], data=rdata, remote=remote,
        callbacks=[advice, generic], requests=[{**request, 'status': 404}],
        value_limits=['Exact Feign exception message spelling is version dependent; assert the source exception-message relationship and String kind, not a guessed literal.']))
    steps.append(o.step({'en': 'Read patient with id=11', 'ru': 'Прочитать пациента с id=11'}, pc['getById'], 'GET', '/patients/{id}', {'id': 11},
        seeded, 200, current, calls=[(pc['getById'], ps['getPatientById'])], data=[(ps['getPatientById'], pt)]))
    fresh = [o.step({'en': 'Read patient with id=11', 'ru': 'Прочитать пациента с id=11'}, pc['getById'], 'GET', '/patients/{id}', {'id': 11}, seeded, 200,
        initial, calls=[(pc['getById'], ps['getPatientById'])], data=[(ps['getPatientById'], pt)])]
    return o, initial, {'state-chain': steps, 'fresh-state': fresh}


def employment():
    o = SourceOracle('employment')
    c = lambda owner, name, arity=None: o.method('companyms', owner, name, arity)
    j = lambda owner, name: o.method('jobms', owner, name)
    r = lambda owner, name: o.method('reviewms', owner, name)
    cc = {n: c('CompanyController', n) for n in ('createCompany', 'getCompany', 'updateCompany')}
    cs = {n: c('companyServiceImplement', n) for n in cc}
    jc, js, convert = j('JobController', 'getJob'), j('JobServiceImplement', 'getJobById'), j('JobServiceImplement', 'convertToDto')
    rc, rs = r('ReviewController', 'getAllreview'), r('reviewServiceImpl', 'getAllreview')
    ct, jt, rt = 'res:table:company.company', 'res:table:job.job', 'res:table:review.review'
    company = {'id': 1, 'name': 'North Works', 'description': 'Manufacturing', 'rating': None}
    job = {'id': 101, 'title': 'Assembler', 'description': 'Build devices', 'minSalary': '40', 'maxSalary': '60', 'location': 'North', 'company': 1}
    review = {'id': 201, 'title': 'Original', 'description': 'Before', 'rating': 3.0, 'companyId': 2}
    current = {'company.company': [company], 'job.job': [job], 'review.review': [review]}
    initial = deepcopy(current)
    incoming = {'name': 'Delta Lab', 'description': 'Robotics'}
    identity = variable('new_company')
    created = {'id': identity, **incoming, 'rating': None}
    current['company.company'].append(created)
    cset = [c('Company', 'set' + n) for n in ('Name', 'Description')]
    cpairs = [(cs['createCompany'], c('Company', '<init>', 0))]
    cpairs += [(cs['createCompany'], c('Company', prefix + field)) for field in ('Name', 'Description') for prefix in ('get', 'set')]
    steps = [o.step({'en': 'Create a company: ' + json.dumps(incoming), 'ru': 'Создать компанию: ' + json.dumps(incoming)},
        cc['createCompany'], 'POST', '/companies', {}, created, 201, current, body=incoming,
        calls=[(cc['createCompany'], cs['createCompany']), *cpairs], data=[(cs['createCompany'], ct)], callbacks=cset,
        producer={'identity': 'new_company', 'response_path': ['id'], 'origin': 'ORM generated identifier', 'native_kind': 'Long'})]
    def company_read(en, ru):
        return o.step({'en': en, 'ru': ru}, cc['getCompany'], 'GET', '/companies/{id}', {'id': previous(1)}, created, 200, current,
            calls=[(cc['getCompany'], cs['getCompany'])], data=[(cs['getCompany'], ct)])
    steps.append(company_read('Read the company just created', 'Прочитать только что созданную компанию'))
    changed = {'name': 'Changed Name', 'description': 'Changed description'}
    pairs = [(cc['updateCompany'], cs['updateCompany'])]
    pairs += [(cs['updateCompany'], c('Company', prefix + field)) for field in ('Name', 'Description') for prefix in ('get', 'set')]
    steps.append(o.step({'en': 'Update the company just created: ' + json.dumps(changed), 'ru': 'Обновить только что созданную компанию: ' + json.dumps(changed)},
        cc['updateCompany'], 'PUT', '/companies/{id}', {'id': previous(1)}, 'Update Succesfully', 200, current, body=changed,
        calls=pairs, data=[(cs['updateCompany'], ct)], callbacks=cset,
        operations=[{'method': cs['updateCompany'], 'operation': 'findById', 'arguments': [identity], 'table': ct, 'writes': False}]))
    steps.append(company_read('Read the company just created again', 'Ещё раз прочитать только что созданную компанию'))
    remote = [(convert, cc['getCompany']), (convert, rc)]
    pairs = [(jc, js), (js, convert), (convert, j('Job', 'getCompany')),
             (cc['getCompany'], cs['getCompany']), (rc, rs)]
    mapper = j('mappper.JobMapper', 'mapJobWithCompanyDto')
    pairs.append((convert, mapper))
    pairs += [(mapper, j('Job', 'get' + field)) for field in ('Id', 'Description', 'Location', 'Title', 'MaxSalary', 'MinSalary')]
    pairs += [(mapper, j('dto.JobDTO', 'set' + field)) for field in ('Id', 'Description', 'Location', 'Title', 'MaxSalary', 'MinSalary', 'Company', 'Review')]
    external_setters = [j('external.Company', 'set' + field) for field in ('Id', 'Name', 'Description')]
    result = {key: value for key, value in job.items() if key != 'company'}
    result.update(company={key: company[key] for key in ('id', 'name', 'description')}, review=[])
    requests = [{'source': convert, 'target': cc['getCompany'], 'deployment': 'companyms', 'method': 'GET', 'path': ['companies', '1'], 'query': {}, 'status': 200},
                {'source': convert, 'target': rc, 'deployment': 'reviewms', 'method': 'GET', 'path': ['reviews'], 'query': {'companyId': ['1']}, 'status': 200}]
    steps.append(o.step({'en': 'Read vacancy with id=101 including company and reviews', 'ru': 'Прочитать вакансию с id=101 вместе с компанией и отзывами'},
        jc, 'GET', '/jobs/{id}', {'id': 101}, result, 200, current, calls=pairs,
        data=[(js, jt), (cs['getCompany'], ct), (rs, rt)], remote=remote, callbacks=external_setters, requests=requests))
    updated = {'title': 'Updated', 'description': 'After', 'rating': 4.0, 'companyId': 2}
    update_c, update_s = r('ReviewController', 'updateReview'), r('reviewServiceImpl', 'updateReview')
    rset = [r('Review', 'set' + field) for field in ('Title', 'Description', 'Rating', 'CompanyId')]
    rpairs = [(update_c, update_s)] + [(update_s, r('Review', prefix + field)) for field in ('Title', 'Description', 'Rating', 'CompanyId') for prefix in ('get', 'set')]
    current['review.review'] = [{'id': 201, **updated}]
    steps.append(o.step({'en': 'Update review with id=201: ' + json.dumps(updated), 'ru': 'Обновить отзыв с id=201: ' + json.dumps(updated)},
        update_c, 'PUT', '/reviews/{reviewId}', {'reviewId': 201}, 'updated', 200, current, body=updated, calls=rpairs, data=[(update_s, rt)], callbacks=rset,
        operations=[{'method': update_s, 'operation': 'findById', 'arguments': [201], 'table': rt, 'writes': False},
                    {'method': update_s, 'operation': 'save', 'table': rt, 'writes': True}]))
    get_c, get_s = r('ReviewController', 'getReview'), r('reviewServiceImpl', 'getReview')
    steps.append(o.step({'en': 'Read review with id=201', 'ru': 'Прочитать отзыв с id=201'}, get_c, 'GET', '/reviews/{reviewId}', {'reviewId': 201},
        {'id': 201, **updated}, 200, current, calls=[(get_c, get_s)], data=[(get_s, rt)]))
    for en, ru in [('Update missing review with id=999', 'Обновить отсутствующий отзыв с id=999'),
                   ('Repeat updating missing review with id=999', 'Повторить обновление отсутствующего отзыва с id=999')]:
        steps.append(o.step({'en': en + ': ' + json.dumps(updated), 'ru': ru + ': ' + json.dumps(updated)}, update_c, 'PUT', '/reviews/{reviewId}',
            {'reviewId': 999}, 'Not Updated', 404, current, body=updated, calls=[(update_c, update_s)], data=[(update_s, rt)], callbacks=rset,
            operations=[{'method': update_s, 'operation': 'findById', 'arguments': [999], 'table': rt, 'writes': False}]))
    fresh = [o.step({'en': 'Read company with id=1', 'ru': 'Прочитать компанию с id=1'}, cc['getCompany'], 'GET', '/companies/{id}', {'id': 1},
        company, 200, initial, calls=[(cc['getCompany'], cs['getCompany'])], data=[(cs['getCompany'], ct)])]
    # A frozen environment variant has a bad Review URL prefix. The first
    # Company request succeeds; Review has no source handler, so no review
    # controller/service/mapper suffix can be exported.
    prefix_pairs = [(jc, js), (js, convert), (convert, j('Job', 'getCompany')), (cc['getCompany'], cs['getCompany'])]
    remote_error = [o.step({'en': 'Read vacancy with id=101 including company and reviews', 'ru': 'Прочитать вакансию с id=101 вместе с компанией и отзывами'},
        jc, 'GET', '/jobs/{id}', {'id': 101}, {'$native': 'DefaultSpringErrorBody', 'status': 500}, 500, initial,
        calls=prefix_pairs, data=[(js, jt), (cs['getCompany'], ct)], remote=[remote[0]], callbacks=external_setters,
        requests=[requests[0], {'source': convert, 'target': None, 'deployment': 'reviewms', 'method': 'GET',
                              'path': ['no-such-prefix', 'reviews'], 'query': {'companyId': ['1']}, 'status': 404}],
        value_limits=['Framework default error body is not a project-method trace; the exact timestamp/error text is outside the complete graph/state oracle.'])]
    return o, initial, {'state-chain': steps, 'fresh-state': fresh, 'remote-error': remote_error}


def relational_snapshot(tables):
    # Canonical table dump transport used by the ready-skeleton input contract.
    # For employment this is not a claim that the target PostgreSQL uses MySQL.
    lines = ['-- Independent relational snapshot; no target database is executed.']
    def literal(value):
        if value is None: return 'NULL'
        if isinstance(value, str): return "'" + value.replace("'", "''") + "'"
        return str(value)
    for name, rows in tables.items():
        schema, table = name.split('.')
        columns = list(rows[0])
        lines += ['USE `' + schema + '`;', 'CREATE TABLE `' + table + '` (',
                  ',\n'.join('  `' + column + '` TEXT' for column in columns), ') ENGINE=InnoDB;']
        for row in rows:
            lines.append('INSERT INTO `' + table + '` VALUES (' + ','.join(literal(row[key]) for key in columns) + ');')
    return '\n'.join(lines) + '\n'


def main():
    OUTPUT.mkdir(exist_ok=False)
    for build in (healthcare, employment):
        o, initial, cases = build()
        root = OUTPUT / o.name
        root.mkdir()
        graph = deepcopy(o.graph)
        graph['context'].update(preflight_only=False,
            environment_scope='Direct synchronous API, no external actors/writers, healthy databases, supplied resolved configuration. Source-only engineering oracle, no target run.',
            framework_scope='Default Spring HTTP/Jackson/JPA; Spring AOP is explicitly disabled in this independent deployment input. CircuitBreaker/RateLimiter annotations do not activate callbacks in this scope.')
        for module, config in graph['context']['configuration'].items():
            props = config['propertySources'][0]['source']
            props.update({'spring.aop.auto': 'false', 'spring.jpa.open-in-view': 'false',
                          'spring.cloud.openfeign.circuitbreaker.enabled': 'false'})
            if o.name == 'employment':
                if module == 'jobms':
                    props.update({'company-service.url': 'http://companyms:8081', 'review-service.url': 'http://reviewms:8083'})
        save(root / 'skeleton.json', graph)
        if o.name == 'employment':
            failed = deepcopy(graph)
            failed['context']['configuration']['jobms']['propertySources'][0]['source']['review-service.url'] = 'http://reviewms:8083/no-such-prefix'
            save(root / 'remote-error-skeleton.json', failed)
        (root / 'initial.sql').write_text(relational_snapshot(initial))
        oracle = {'project': graph['project'], 'source_revision': json.loads((o.root / 'origin.json').read_text())['revision'],
                  'prepared_before_inference': True, 'inference_predictions_used': False,
                  'projection_reference': 'tt-challenge/REFERENCE.md:62-64', 'initial_tables': initial,
                  'identity_rule': 'Fresh source-declared Long, same identity in producer response, subsequent wire/binding and persistent rows; numeric spelling never chosen from a prediction.',
                  'cases': {}, 'source_evidence': o.evidence}
        for case, steps in cases.items():
            for mode in ('explicit-script', 'nl-en', 'nl-ru'):
                sid = o.name + '-' + case + '-' + mode
                scenario = {'id': sid, 'project': graph['project'], 'steps': [], 'request_scripts': {}}
                expected = []
                for number, row in enumerate(steps, 1):
                    key = sid + ':' + str(number)
                    action = '@http-script:' + key if mode == 'explicit-script' else row['actions'][mode[-2:]]
                    scenario['steps'].append({'n': number, 'action': action})
                    if mode == 'explicit-script': scenario['request_scripts'][key] = row['request_script']
                    exp = deepcopy(row['expected'])
                    for edge in exp['edges']:
                        if edge['source'] == '$scenario': edge['source'] = 'scenario:' + sid
                    expected.append(exp)
                save(root / ('remote-error' if case == 'remote-error' else 'normal') / mode / (sid + '.json'), scenario)
                oracle['cases'][sid] = {'mode': mode, 'steps': expected, 'environment': 'remote-error' if case == 'remote-error' else 'normal',
                                       'full_graph_oracle': True, 'full_persistent_state_oracle': True}
        # Refusal inputs have no privileged handler, value, or request recipe.
        for language, ambiguous, absent in [('en', 'Delete the record', 'Send an SMS to the user'),
                                             ('ru', 'Удалить запись', 'Отправить пользователю СМС')]:
            for kind, action in [('ambiguous', ambiguous), ('no-handler', absent)]:
                sid = o.name + '-' + kind + '-' + language
                save(root / 'normal' / ('nl-' + language) / (sid + '.json'),
                     {'id': sid, 'project': graph['project'], 'steps': [{'n': 1, 'action': action}]})
                oracle['cases'][sid] = {'mode': 'nl-' + language, 'environment': 'normal', 'full_graph_oracle': True,
                    'full_persistent_state_oracle': True, 'steps': [{'refusal': kind, 'edges': [], 'tables': initial, 'operations': [], 'exploration_complete': False}]}
        save(root / 'oracle.json', oracle)
        save(root / 'review.json', {'reviewer': 'Codex independent engineering reading before predictions',
            'inference_predictions_used': False, 'second_human_or_agent_review': False, 'targets_executed': False,
            'scope': 'Exact source-method E/C/R/D and complete persistent rows in the explicitly supplied synchronous deployment slice. Parametric generated identity; error-message/timestamp formatting limitations remain explicit.',
            'explicit_control_protocol': 'HTTP script recipes are external client input, not NL hints. They bind only stated literals or a prior response property. The same normal HTTP binding/engine must consume the resulting wire; no oracle, expected handler, edge or state is read by the driver.',
            'not_claimed': ['Dynamic ground truth', 'All modules of either application', 'AOP-enabled deployment/fallback coverage', 'A second independently authored oracle', 'Exact framework-generated error-message/timestamp bytes'],
            'source_evidence': o.evidence})
    save(OUTPUT / 'freeze.json', {'frozen_at': datetime.now(timezone.utc).isoformat(), 'query_predictions_seen': False,
        'target_applications_started': False, 'applications': ['healthcare', 'employment'],
        'full_semantic_transfer_verified': False, 'status': 'Independent graph/state expectations frozen; inference and checker validation are pending.',
        'files': {path.relative_to(OUTPUT).as_posix(): sha(path) for path in sorted(OUTPUT.rglob('*')) if path.is_file()},
        'source_files': {name + '/' + path.relative_to(BASE / name / 'source').as_posix(): sha(path)
                         for name in ('employment', 'healthcare') for path in sorted((BASE / name / 'source').rglob('*')) if path.is_file()}})
    print(json.dumps({'frozen': str(OUTPUT), 'apps': 2, 'inference_run': False, 'targets_started': False}))


if __name__ == '__main__':
    main()
