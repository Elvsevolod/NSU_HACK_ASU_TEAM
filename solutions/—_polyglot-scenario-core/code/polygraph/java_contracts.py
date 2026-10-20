"""Signatures for modeled Java libraries, never names from the target project."""
import re
import xml.etree.ElementTree as ET

RETURNS = {
    'org.springframework.http.HttpHeaders': {'get': 'java.util.List<String>', 'getFirst': 'String', 'containsKey': 'boolean', 'isEmpty': 'boolean'},
    'java.util.List': {'size': 'int', 'isEmpty': 'boolean', 'contains': 'boolean'},
    'java.util.Collection': {'size': 'int', 'isEmpty': 'boolean', 'contains': 'boolean'},
    'java.util.Set': {'size':'int','isEmpty':'boolean','contains':'boolean'},
    'java.util.HashSet': {'size':'int','isEmpty':'boolean','contains':'boolean'},
    'java.util.Map': {'size': 'int', 'isEmpty': 'boolean', 'containsKey': 'boolean'},
    'java.lang.String': {'length': 'int', 'isEmpty': 'boolean', 'equals': 'boolean','valueOf':'String'},
    'java.lang.Integer': {'intValue':'int','longValue':'long','sum':'int','compare':'int','parseInt':'int','valueOf':'Integer','hashCode':'int'},
    'java.lang.Long': {'intValue':'int','longValue':'long','sum':'long','compare':'int','parseLong':'long','valueOf':'Long','hashCode':'int'},
    'java.lang.Boolean': {'booleanValue':'boolean','valueOf':'Boolean','parseBoolean':'boolean','hashCode':'int'},
    'java.util.stream.Stream': {'count':'long'},
    'java.time.LocalDate': {'now':'java.time.LocalDate','of':'java.time.LocalDate','atStartOfDay':'java.time.LocalDateTime','toEpochDay':'long','toString':'String'},
    'java.time.LocalDateTime': {'of':'java.time.LocalDateTime','atZone':'java.time.ZonedDateTime'},
    'java.time.ZonedDateTime': {'toInstant':'java.time.Instant'},
    'java.time.Instant': {'now':'java.time.Instant','ofEpochMilli':'java.time.Instant','toEpochMilli':'long'},
    'java.time.ZoneId': {'of':'java.time.ZoneId','systemDefault':'java.time.ZoneId'},
    'java.util.Date': {'from':'java.util.Date','getTime':'long','toInstant':'java.time.Instant'},
}
for wrapper in ('Integer','Long','Byte','Short','Boolean'):
    RETURNS.setdefault('java.lang.'+wrapper,{}).update({'equals':'boolean','compareTo':'int','toString':'String','hashCode':'int'})
RETURNS['java.util.Arrays']={'asList':'java.util.List'}
RETURNS['java.util.stream.Stream'].update({'of':'java.util.stream.Stream','empty':'java.util.stream.Stream','map':'java.util.stream.Stream','filter':'java.util.stream.Stream','peek':'java.util.stream.Stream','limit':'java.util.stream.Stream','skip':'java.util.stream.Stream'})
TYPES = set(RETURNS) | {
    'org.springframework.http.HttpMethod', 'org.springframework.http.HttpStatus',
    'org.springframework.http.HttpEntity', 'org.springframework.http.ResponseEntity',
    'org.springframework.web.client.RestTemplate', 'org.springframework.util.Assert',
    'org.springframework.util.StringUtils', 'org.slf4j.LoggerFactory', 'org.slf4j.Logger',
    'java.util.ArrayList', 'java.util.HashMap', 'java.util.LinkedList', 'java.util.LinkedHashMap',
    'java.util.Optional', 'java.util.UUID',
    'java.util.stream.Collectors','java.util.stream.Stream','java.util.HashSet','java.util.LinkedHashSet',
    'java.lang.String','java.math.BigDecimal',
    'java.lang.Integer','java.lang.Long','java.lang.Byte','java.lang.Short','java.lang.Boolean','java.lang.Number','java.lang.Object',
    'java.util.Date','java.time.LocalDate','java.time.LocalDateTime','java.time.Instant','java.time.ZonedDateTime','java.time.ZoneId',
}


def spring_versions(pom):
    """Explicit dependency versions only; no Maven execution or guessed Boot BOM."""
    root = ET.fromstring(pom)
    for node in root.iter():
        node.tag = node.tag.rsplit('}', 1)[-1]
    props = {node.tag: node.text or '' for node in root.findall('./properties/*')}
    versions = set()
    for dependency in root.findall('./dependencies/dependency') + root.findall('./dependencyManagement/dependencies/dependency'):
        if dependency.findtext('groupId') != 'org.springframework':
            continue
        version = dependency.findtext('version', '').strip()
        for _ in range(len(props) + 1):
            found = re.fullmatch(r'\$\{([^}]+)\}', version)
            if not found or found[1] not in props:
                break
            version = props[found[1]].strip()
        if re.fullmatch(r'\d+\.\d+\.\d+(?:[.-][\w.-]+)?', version):
            versions.add(version)
    return versions


def entity_headers_readonly(engine, span):
    module = engine.method.module if engine.method else engine.p.module(span.file)
    supplied = engine.context.get('framework_versions', {}).get(module, {}).get('spring')
    version = supplied or engine.p.framework_versions.get(module, {}).get('spring', '')
    family = re.match(r'(\d+)\.(\d+)(?:\.|$)', version) if isinstance(version, str) else None
    # These source contracts were checked against official upstream tags.
    if family and tuple(map(int, family.groups())) in {(5, 3), (6, 2), (7, 0)}:
        return True
    engine.note('framework-version-unknown', 'HttpEntity header mutability is version-dependent; both contracts remain possible', span, module=module, spring_version=version or 'unspecified')
    return engine.choose((True, False), 'HttpEntity headers readonly contract')
