"""Explicit Java abrupt completion and a bounded standard exception hierarchy."""
from .state import U


class JavaThrow(Exception):
    def __init__(self,value):
        self.value = value


class ExceptionBound(str):
    """The failure has this base type; its precise subclass is unobserved."""


PARENTS = {
    'Throwable':None,'Exception':'Throwable','Error':'Throwable','RuntimeException':'Exception',
    'LinkageError':'Error','ExceptionInInitializerError':'LinkageError','NoClassDefFoundError':'LinkageError',
    'IllegalArgumentException':'RuntimeException','IllegalStateException':'RuntimeException',
    'NumberFormatException':'IllegalArgumentException','NullPointerException':'RuntimeException',
    'NoSuchElementException':'RuntimeException','ArithmeticException':'RuntimeException',
    'ClassCastException':'RuntimeException','ArrayStoreException':'RuntimeException',
    'IndexOutOfBoundsException':'RuntimeException','ArrayIndexOutOfBoundsException':'IndexOutOfBoundsException',
    'StringIndexOutOfBoundsException':'IndexOutOfBoundsException',
    'IOException':'Exception','FileNotFoundException':'IOException',
    'ParseException':'Exception',
    'RestClientException':'RuntimeException','RestClientResponseException':'RestClientException',
    'HttpStatusCodeException':'RestClientResponseException','HttpClientErrorException':'HttpStatusCodeException',
    'HttpServerErrorException':'HttpStatusCodeException',
    'HttpMessageConversionException':'RuntimeException',
    'HttpMessageNotWritableException':'HttpMessageConversionException',
    'UnsupportedOperationException':'RuntimeException','ConcurrentModificationException':'RuntimeException',
    'JsonProcessingException':'IOException','JsonMappingException':'JsonProcessingException',
    'MismatchedInputException':'JsonMappingException','PropertyBindingException':'MismatchedInputException',
    'UnrecognizedPropertyException':'PropertyBindingException',
    'AuthenticationException':'RuntimeException','BadCredentialsException':'AuthenticationException',
    'UsernameNotFoundException':'AuthenticationException','AccountStatusException':'AuthenticationException',
    'LockedException':'AccountStatusException','DisabledException':'AccountStatusException',
    'AccountExpiredException':'AccountStatusException','CredentialsExpiredException':'AccountStatusException',
    'FeignException':'RuntimeException',
    'TransactionException':'RuntimeException','UnexpectedRollbackException':'TransactionException',
    'JwtException':'RuntimeException','MalformedJwtException':'JwtException','UnsupportedJwtException':'JwtException',
    'SignatureException':'JwtException','ClaimJwtException':'JwtException',
    'ExpiredJwtException':'ClaimJwtException','PrematureJwtException':'ClaimJwtException',
}

NATIVE_TYPES={name:'java.lang.'+name for name in PARENTS}
NATIVE_TYPES.update({name:package+'.'+name for package,names in {
    'java.io':('IOException','FileNotFoundException'),
    'java.text':('ParseException',),
    'java.util':('NoSuchElementException','ConcurrentModificationException'),
    'org.springframework.web.client':('RestClientException','RestClientResponseException','HttpStatusCodeException','HttpClientErrorException','HttpServerErrorException'),
    'org.springframework.http.converter':('HttpMessageConversionException','HttpMessageNotWritableException'),
    'com.fasterxml.jackson.core':('JsonProcessingException',),
    'com.fasterxml.jackson.databind':('JsonMappingException',),
    'com.fasterxml.jackson.databind.exc':('MismatchedInputException','PropertyBindingException','UnrecognizedPropertyException'),
    'org.springframework.security.core':('AuthenticationException',),
    'org.springframework.security.authentication':('BadCredentialsException','AccountStatusException','LockedException','DisabledException','AccountExpiredException','CredentialsExpiredException'),
    'org.springframework.security.core.userdetails':('UsernameNotFoundException',),
    'feign':('FeignException',),
    'org.springframework.transaction':('TransactionException','UnexpectedRollbackException'),
    'io.jsonwebtoken':('JwtException','MalformedJwtException','UnsupportedJwtException','SignatureException',
        'ClaimJwtException','ExpiredJwtException','PrematureJwtException'),
}.items() for name in names})


def native_type(name):
    canonical=NATIVE_TYPES.get(name,name)
    return ExceptionBound(canonical) if isinstance(name,ExceptionBound) else canonical


def assignable(thrown,caught,project):
    if thrown is U or not isinstance(thrown,str):
        return U
    if isinstance(thrown,ExceptionBound):
        forward=assignable(str(thrown),caught,project)
        if forward is not False:return forward
        return False if assignable(caught,str(thrown),project) is False else U
    source_catch=any(node['kind']=='type' and node['fqn']==caught for node in project.nodes.values())
    pending,seen,unknown = [thrown],set(),False
    while pending:
        name = pending.pop()
        if name in seen:continue
        seen.add(name)
        if name == caught:return True
        owners = [tid for tid,node in project.nodes.items() if node['kind']=='type' and node['fqn']==name]
        if len(owners)==1:
            pending.extend(project.framework_types.get(owners[0],set()))
        elif name in NATIVE_TYPES or name in NATIVE_TYPES.values():
            simple = name.split('.')[-1]
            if not source_catch and native_type(name)==native_type(caught):return True
            parent = PARENTS[simple]
            if parent is not None:pending.append(native_type(parent))
        else:
            unknown = True
    return U if unknown else False
