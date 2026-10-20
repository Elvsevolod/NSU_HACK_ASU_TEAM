"""Bounded legacy AngularJS $http promise callbacks, tied to their AST call."""
import re
from urllib.parse import urlsplit


def callbacks(frontend,path,tree,call,pages):
    from .frontend import text,walk,ancestor,FUNCTIONS,redeclares
    found={};current=call
    while current.parent is not None and current.parent.type=='member_expression':
        member=current.parent
        if member.child_by_field_name('object')!=current:break
        method=text(member.child_by_field_name('property'))
        outer=member.parent
        if method not in ('success','error') or outer.type!='call_expression' or outer.child_by_field_name('function')!=member:break
        args=outer.child_by_field_name('arguments').named_children
        if len(args)!=1 or args[0].type not in FUNCTIONS:return {},None
        if method in found:return {},None
        found[method]=args[0];current=outer
    if not found:return {},None
    if text(call.child_by_field_name('function'))!='$http':return {},None
    scope=ancestor(call.parent,(*FUNCTIONS,'program'));injected=None
    while scope is not None and scope.type!='program':
        params=scope.child_by_field_name('parameters')
        names=[text(n) for n in params.named_children] if params else []
        if '$http' in names:injected=scope;break
        if redeclares(scope,'$http',None):return {},None
        scope=ancestor(scope.parent,(*FUNCTIONS,'program'))
    if injected is None:return {},None
    # A parameter is an Angular service only in a source-proven registration.
    registration=injected.parent.parent if injected.parent is not None and injected.parent.type=='arguments' else None
    if registration is None or registration.type!='call_expression':return {},None
    function=registration.child_by_field_name('function')
    if function.type!='member_expression' or text(function.child_by_field_name('property')) not in ('controller','run','factory','service'):return {},None
    receiver=function.child_by_field_name('object')
    module_calls=[]
    if receiver.type=='call_expression':module_calls=[receiver]
    elif receiver.type=='identifier':
        for variable in walk(tree.root_node):
            if variable.type=='variable_declarator' and text(variable.child_by_field_name('name'))==text(receiver):
                module_calls.append(variable.child_by_field_name('value'))
    if len(module_calls)!=1 or module_calls[0] is None or module_calls[0].type!='call_expression' or text(module_calls[0].child_by_field_name('function'))!='angular.module':return {},None
    for node in walk(injected):
        if node.type in ('variable_declarator','assignment_expression'):
            target=node.child_by_field_name('name' if node.type=='variable_declarator' else 'left')
            if text(target)=='$http':return {},None
    if any(node.type=='variable_declarator' and text(node.child_by_field_name('name'))=='angular' for node in walk(tree.root_node)):return {},None
    versions=set()
    for page_path,page in pages:
        for src in page.scripts:
            address=urlsplit(src)
            if address.netloc in ('ajax.googleapis.com','code.angularjs.org'):
                match=re.search(r'/(1\.\d+\.\d+)/angular(?:\.min)?\.js$',address.path)
                if match:versions.add(match[1])
                continue
            vendor=(page_path.parent/src).resolve()
            if not vendor.is_relative_to(frontend.project.root.resolve()) or not vendor.is_file():continue
            head=vendor.read_bytes()[:1024].decode(errors='replace')
            match=re.search(r'@license AngularJS v(1\.\d+\.\d+)',head)
            if match:versions.add(match[1])
    if len(versions)!=1:return {},None
    version=versions.pop()
    if tuple(map(int,version.split('.')))>(1,5,11):return {},None
    for node in walk(tree.root_node):
        if node.type=='call_expression' and text(node.child_by_field_name('function')).endswith('.useLegacyPromiseExtensions'):
            args=node.child_by_field_name('arguments').named_children
            if len(args)!=1 or text(args[0])!='true':return {},None
    contract={'library':'AngularJS','version':version,'response_argument':'response.data',
        'request_byte':call.start_byte,'request_line':call.start_point.row+1,
        'callbacks':{name:{'line':node.start_point.row+1,'byte':node.start_byte} for name,node in found.items()}}
    return found,contract
