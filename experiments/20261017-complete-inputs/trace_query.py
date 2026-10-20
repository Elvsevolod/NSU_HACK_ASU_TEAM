from analyzer.project import Project
from analyzer.engine import Engine
from analyzer.state import Database,ScenarioState
from analyzer.contracts import read_static_context
from analyzer.__main__ import serial
import json
p=Project('tt-challenge/skeleton/trainticket.json.gz','tt-challenge/targets/trainticket')
db=Database('tt-challenge/context/db-after-warmup.sql.gz');db.schemas=p.schemas
c=read_static_context(p.skeleton['context']);s=ScenarioState(db,c);s.now=c['clock']
class Trace(Engine):
 def invoke(self,mid,args,receiver=None,reason='source call'):
  result=super().invoke(mid,args,receiver,reason)
  if p.methods[mid]['name'] in {'getRoutesByRouteIds','getRoutesByIds','queryByIds','conveterObject','queryForTravels','getTicketsByBatch','toString'}:
   print('TRACE',mid, 'args',json.dumps(args,default=serial)[:500], 'RETURN',json.dumps(result,default=serial)[:1600],flush=True)
  return result
mid=next(m for m in p.methods if ':travel.controller.TravelController#queryInfo(' in m)
e=Trace(p,s,conservative=True);r=e.run(mid,{'startPlace':'Shang Hai','endPlace':'Su Zhou','departureTime':'2026-10-01'})
print('RESULT',json.dumps(r,default=serial))
