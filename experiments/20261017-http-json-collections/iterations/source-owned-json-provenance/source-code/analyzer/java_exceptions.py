"""Explicit Java abrupt completion and a bounded standard exception hierarchy."""
from .state import U


class JavaThrow(Exception):
    def __init__(self,value):
        self.value = value


PARENTS = {
    'Throwable':None,'Exception':'Throwable','Error':'Throwable','RuntimeException':'Exception',
    'IllegalArgumentException':'RuntimeException','IllegalStateException':'RuntimeException',
    'NumberFormatException':'IllegalArgumentException','NullPointerException':'RuntimeException',
    'NoSuchElementException':'RuntimeException','ArithmeticException':'RuntimeException',
    'ClassCastException':'RuntimeException',
    'IndexOutOfBoundsException':'RuntimeException','ArrayIndexOutOfBoundsException':'IndexOutOfBoundsException',
    'StringIndexOutOfBoundsException':'IndexOutOfBoundsException',
    'IOException':'Exception','FileNotFoundException':'IOException',
    'ParseException':'Exception',
    'RestClientException':'RuntimeException','RestClientResponseException':'RestClientException',
    'HttpStatusCodeException':'RestClientResponseException','HttpClientErrorException':'HttpStatusCodeException',
    'HttpServerErrorException':'HttpStatusCodeException',
}


def assignable(thrown,caught,project):
    if thrown is U or not isinstance(thrown,str):
        return U
    pending,seen,unknown = [thrown],set(),False
    while pending:
        name = pending.pop()
        if name in seen:continue
        seen.add(name)
        if name == caught:return True
        owners = [tid for tid,node in project.nodes.items() if node['kind']=='type' and node['fqn']==name]
        if len(owners)==1:
            pending.extend(project.framework_types.get(owners[0],set()))
        elif name.split('.')[-1] in PARENTS and caught.split('.')[-1] in PARENTS:
            simple = name.split('.')[-1]
            if simple == caught.split('.')[-1]:return True
            parent = PARENTS[simple]
            if parent is not None:pending.append(parent)
        else:
            unknown = True
    return U if unknown else False
