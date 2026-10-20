"""Freeze independent source, scenario and oracle before any candidate run."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

variant = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(variant/'code'), str(variant/'code/tests')]
from builders import build

parser=argparse.ArgumentParser()
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
assert not args.output.exists()
sources={
    'Gateway.java': '''import java.util.*;import org.springframework.web.client.*;
      import org.springframework.http.*;import org.springframework.core.ParameterizedTypeReference;
      class Gateway {RestTemplate client;
        @PostMapping("/bookings") Object createBooking(@RequestBody BookingInput input){try{
          return client.postForObject("http://warehouse/reservations",new HttpEntity(input),Booking.class);
        }catch(RestClientException e){return failed();}}
        String failed(){return "refused";}
        @GetMapping("/bookings") List<Booking> listBookings(){return client.exchange(
          "http://warehouse/reservations",HttpMethod.GET,null,new ParameterizedTypeReference<List<Booking>>(){}).getBody();}
        @GetMapping("/bookings/{bookingId}") Booking inspectBooking(@PathVariable String bookingId){
          return client.getForObject("http://warehouse/reservations/"+bookingId,Booking.class);}
        @DeleteMapping("/bookings/{bookingId}") void cancelBooking(@PathVariable String bookingId){
          client.exchange("http://warehouse/reservations/"+bookingId,HttpMethod.DELETE,null,String.class);}
      }''',
    'Warehouse.java': '''import java.util.*;class Warehouse {Store store;
      @PostMapping("/reservations") Booking reserve(@RequestBody BookingInput input){
        if(!input.enabled){throw new IllegalArgumentException();}
        Booking item=new Booking();item.id=input.id;item.title=input.title;store.save(item);return item;}
      @GetMapping("/reservations") List<Booking> list(){return store.findAll();}
      @GetMapping("/reservations/{id}") Booking read(@PathVariable String id){return store.findById(id);}
      @DeleteMapping("/reservations/{id}") void remove(@PathVariable String id){store.deleteById(id);}}
      class BookingInput {public String id;public String title;public boolean enabled;}
      @Entity @Table(name="bookings") class Booking {@Id public String id;public String title;}
      interface Store extends JpaRepository<Booking,String>{Booking save(Booking input);Booking findById(String id);List<Booking> findAll();void deleteById(String id);}'''}
project,db,ids=build(args.output,sources,module='review',rows={'bookings':[]})
skeleton=project.skeleton
for unit in ('gateway','warehouse'):
    skeleton['nodes']['module:'+unit]={'kind':'module','name':unit,'deployment_units':[unit]}
for node in skeleton['nodes'].values():
    if node.get('file'):node['module']='gateway' if node['file']=='Gateway.java' else 'warehouse'
(args.output/'skeleton.json').write_text(json.dumps(skeleton,indent=2)+'\n')
(args.output/'ui.js').write_text('''function createBooking(){$.ajax({url:"/bookings",type:"POST",contentType:"application/json",data:JSON.stringify({id:$("#id").val(),title:$("#title").val(),enabled:$("#enabled").is(":checked")})});}
function listBookings(){$.ajax({url:"/bookings",type:"GET"});}
function inspectBooking(){$.ajax({url:"/bookings/"+$("#bookingId").val(),type:"GET"});}
function cancelBooking(){$.ajax({url:"/bookings/"+$("#bookingId").val(),type:"DELETE"});}''')
actions=[
 ('Create booking id "A" title "Alpha" with enabled true','Gateway.createBooking',{'id':'A','title':'Alpha'},1),
 ('List bookings','Gateway.listBookings',[{'id':'A','title':'Alpha'}],1),
 ('Create booking id "B" title "Beta" with enabled true','Gateway.createBooking',{'id':'B','title':'Beta'},2),
 ('List bookings','Gateway.listBookings',[{'id':'A','title':'Alpha'},{'id':'B','title':'Beta'}],2),
 ('Cancel booking bookingId "A"','Gateway.cancelBooking',None,1),
 ('List bookings','Gateway.listBookings',[{'id':'B','title':'Beta'}],1),
 ('Inspect first booking','Gateway.inspectBooking',{'id':'B','title':'Beta'},1),
 ('Create booking id "C" title "Blocked" with enabled false','Gateway.createBooking','refused',1),
 ('Cancel booking bookingId "B"','Gateway.cancelBooking',None,0),
 ('List bookings','Gateway.listBookings',[],0),
 ('Inspect first booking','Gateway.inspectBooking',None,0),
]
scenario={'id':'review-journey','project':'fixture','steps':[{'n':i+1,'action':row[0]} for i,row in enumerate(actions)]}
(args.output/'scenario.json').write_text(json.dumps(scenario,indent=2)+'\n')
names=['Gateway.createBooking','Gateway.listBookings','Gateway.inspectBooking','Gateway.cancelBooking','Gateway.failed',
       'Warehouse.reserve','Warehouse.list','Warehouse.read','Warehouse.remove']
edges={('scenario:review-journey','executes',ids[name]) for name in names}
edges.add((ids['Gateway.createBooking'],'calls',ids['Gateway.failed']))
for gateway,warehouse in [('createBooking','reserve'),('listBookings','list'),('inspectBooking','read'),('cancelBooking','remove')]:
    edges.add((ids['Gateway.'+gateway],'remote',ids['Warehouse.'+warehouse]))
    edges.add((ids['Warehouse.'+warehouse],'data','res:table:review.bookings'))
oracle={'reference_fixed_before_prediction':True,'application_started':False,
    'scope':'independent synthetic full NL/HTTP/state journey; not evidence of real-app portability',
    'edges':[dict(zip(('source','relation','target'),edge)) for edge in sorted(edges)],
    'steps':[{'n':i+1,'endpoint':ids[row[1]],'result':row[2],'rows':row[3],
              'result_must_be_unresolved':i==10,'optional_result':row[1]=='Gateway.cancelBooking'} for i,row in enumerate(actions)]}
(args.output/'oracle.json').write_text(json.dumps(oracle,indent=2)+'\n')
manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(args.output.iterdir()) if p.is_file()}
(args.output/'FILES.sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'fixture':str(args.output),'steps':len(actions),'edges':len(edges),'oracle_sha256':manifest['oracle.json']}))
