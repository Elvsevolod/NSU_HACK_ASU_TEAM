"""Execute only allowlisted FastAPI dependency primitives on supplied data."""
import asyncio
from functools import lru_cache

from fastapi import HTTPException
from fastapi.dependencies.utils import get_dependant, request_body_to_args
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, OAuth2PasswordRequestFormStrict
from starlette.datastructures import FormData
from starlette.requests import Request

from .models import NOT_HANDLED
from .values import Object, Raised, unknown
from .native_contracts import check


FORMS={'fastapi.security.OAuth2PasswordRequestForm':OAuth2PasswordRequestForm,
       'fastapi.security.OAuth2PasswordRequestFormStrict':OAuth2PasswordRequestFormStrict}
BEARERS={'fastapi.security.OAuth2PasswordBearer':OAuth2PasswordBearer}


def public_name(name):
    return name.replace('fastapi.security.oauth2.','fastapi.security.')


@lru_cache(maxsize=8)
def form_fields(name):return get_dependant(path='/',call=FORMS[name]).body_params


def construct(engine,name,args,kwargs,span):
    name=public_name(name)
    if name not in BEARERS:return NOT_HANDLED
    return engine.state.new(name,{'args':args,'kwargs':kwargs})


def dependency(engine,key,span):
    key=public_name(key)
    if key in FORMS:
        check(engine,'fastapi',span)
        form=engine.request_input.get('form',{})
        if any(unknown(value) for value in form.values()):
            engine.unsupported('Native OAuth2 form validation needs concrete field values',span)
        values,errors=asyncio.run(request_body_to_args(body_fields=form_fields(key),received_body=FormData(form),embed_body_fields=True))
        if errors:raise Raised('RequestValidationError',errors)
        native=FORMS[key](**values)
        return engine.state.new(key,vars(native))
    value=engine.state.globals.get(key)
    if key in engine.p.globals and value is None:
        value=engine.definition_value(engine.p.globals[key],key);engine.state.globals[key]=value
    if not isinstance(value,Object) or value.typ not in BEARERS:return NOT_HANDLED
    check(engine,'fastapi',span)
    headers=[]
    for name,items in engine.request_input.get('headers',{}).items():
        for item in items if isinstance(items,list) else [items]:
            if not isinstance(item,str):engine.unsupported('Bearer header value is not concrete text',span)
            headers.append((name.encode('latin-1'),item.encode('latin-1')))
    request=Request({'type':'http','method':engine.request_input.get('method','GET'),'path':'/','headers':headers})
    try:
        native=BEARERS[value.typ](*value.fields['args'],**value.fields['kwargs'])
        return asyncio.run(native(request))
    except HTTPException as exc:
        raise Raised('HTTPException',engine.state.new('HTTPException',{'status_code':exc.status_code,'detail':exc.detail,'headers':exc.headers or {}})) from None
