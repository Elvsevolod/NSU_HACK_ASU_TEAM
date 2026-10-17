from pathlib import Path
from importlib.metadata import distribution
import hashlib,json,subprocess,sys
root=Path('/Users/vsevolod/Desktop/NSU_HACK_ASU_TEAM')
v=root/'solutions/—_polyglot-scenario-core';exp=root/'experiments/20261017-polyglot-scenario-core'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
(v/'requirements.lock.txt').write_text(subprocess.check_output([sys.executable,'-m','pip','--disable-pip-version-check','freeze'],text=True))
path=v/'third_party/provenance.json';provenance=json.loads(path.read_text())
for name in ['javaproperties','tzdata']:
 dist=distribution(name);parts=[];sources=[]
 for file in sorted(dist.files):
  if 'license' not in str(file).lower():continue
  raw=dist.locate_file(file).read_bytes();sources.append({'path':str(file),'sha256':hashlib.sha256(raw).hexdigest()})
  parts.append(('Original distribution file: '+str(file)+'\n\n').encode()+raw+b'\n')
 assert parts
 target=v/('third_party/'+name+'-LICENSE.txt');target.write_bytes(b'\n'.join(parts))
 provenance[name]={'version':dist.version,'project_urls':dist.metadata.get_all('Project-URL') or [],'license_file':target.relative_to(v).as_posix(),'license_sha256':digest(target),'original_license_files':sources}
fixture=v/'benchmark/public-spring/fixture/LICENSE'
provenance['public-spring-fixture']={'project_urls':['https://github.com/sqshq/piggymetrics/tree/6bb2cf9ddbca980b664d3edbb6ff775d75369278'],'version':'6bb2cf9ddbca980b664d3edbb6ff775d75369278','license_file':fixture.relative_to(v).as_posix(),'license_sha256':digest(fixture),'license_source':'https://raw.githubusercontent.com/sqshq/piggymetrics/6bb2cf9ddbca980b664d3edbb6ff775d75369278/LICENCE','scope':'Unmodified production Java declarations, selected configuration and Maven descriptors as static test input; no target startup or import.'}
write(path,provenance)
path=v/'development/deepseek-audit.json';audit=json.loads(path.read_text())
audit['phase5']={'second_opinion':'Need reassessed for deployment-scoped configuration, MVC advice, Feign selection and temporal boundary. A bounded read-only attempt produced no substantive response or tool action; no independent review accepted.','session':'ses_eb6150683ffePQXPD88HKxmT3n','attempt':json.loads((exp/'phase5-consult-status.json').read_text()),'implementation_delegation':'Not used: human requires DeepSeek to remain read-only. No model substituted.','files_changed_by_deepseek':[]}
for file in ['phase5-consult.jsonl','phase5-consult.stderr','phase5-consult-status.json']:audit['raw_sha256'][file]=digest(exp/file)
write(path,audit)
path=v/'development/model-contracts.json';contracts=json.loads(path.read_text())
contracts['spring_configuration']={'native_libraries':{'javaproperties':'0.8.2','PyYAML':'6.0.3'},'upstream_sources':json.loads((exp/'phase5-config-upstream.json').read_text()),'documentation':['https://cloud.spring.io/spring-cloud-config/2.0.x/multi/multi__spring_cloud_config_server.html','https://docs.spring.io/spring-boot/docs/2.0.x/reference/html/boot-features-external-config.html'],'scope':'Deployment-scoped conventional classpath sources, bounded literal profile selectors and ordered resolved Environment snapshots. External config fetch, custom imports, locations, ConfigData loader and full bootstrap lifecycle are unsupported.'}
contracts['spring_MVC_validation']={'sources':['https://docs.spring.io/spring-framework/docs/5.3.4/reference/html/web.html#mvc-ann-exceptionhandler','https://docs.jboss.org/hibernate/validator/6.0/reference/en-US/html_single/'],'scope':'Bounded field Default-group constraints, selected source exception handlers and known routing status. Custom getter/class/field validation, groups, selectors, resolvers and full request/response lifecycle are not inferred.'}
contracts['java_time']={'native_libraries':{'CPython':'3.11.9','tzdata':'2026.5','IANA':'2026e'},'sources':['https://docs.oracle.com/javase/8/docs/api/java/time/LocalDate.html','https://docs.oracle.com/javase/8/docs/api/java/time/LocalDateTime.html','https://docs.oracle.com/javase/8/docs/api/java/util/Date.html','https://github.com/python/cpython/blob/v3.11.14/Doc/library/zoneinfo.rst','https://github.com/python/tzdata/releases/tag/2026.5'],'scope':'Selected LocalDate/LocalDateTime/ZoneId/Instant/Date conversions over explicit scenario time and pinned timezone data. No wall clock or OS timezone files. Regional rules require matching timezone_database. Nanoseconds, extended years and unspecified codecs are explicit cutoffs.'}
write(path,contracts)
write(v/'development/code-freeze.json',{'files':{p.relative_to(v).as_posix():digest(p) for p in sorted((v/'code').rglob('*.py'))}})
print(json.dumps({'code_files':len(json.loads((v/'development/code-freeze.json').read_text())['files']),'license_entries':len(provenance)}))
