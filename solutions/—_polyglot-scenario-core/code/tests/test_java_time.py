"""Time results use declared analysis inputs, never the host clock/timezone."""
import pytest

from polygraph.analysis import analyze
from support import fixture,scenario


def run(tmp_path,expression,context=None,statements=''):
    source='''import org.springframework.web.bind.annotation.*;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.Instant;
import java.time.ZoneId;
import java.util.Date;
@RestController class Endpoint {@GetMapping("/value") Object value(){'''+statements+'return '+expression+';}}'
    p,store,ids=fixture(tmp_path,{'Endpoint.java':source})
    block,detail=analyze(p,store,context or {},scenario({'path':'/value'}))
    return block,detail


def test_current_day_converts_through_java_types_and_preserves_epoch_millis(tmp_path):
    _,detail=run(tmp_path,'Date.from(LocalDate.now().atStartOfDay().atZone(ZoneId.systemDefault()).toInstant()).getTime()',
                 {'clock':'2026-01-02T10:00:00Z','timezone':'UTC'})
    assert len(detail['paths'])==1
    assert detail['paths'][0]['steps'][0]['response']['body']==1767312000000


@pytest.mark.parametrize('instant,expected',[
    ('LocalDateTime.of(2021,3,14,2,30)',1615707000000),
    ('LocalDateTime.of(2021,11,7,1,30)',1636263000000),
])
def test_gap_shifts_forward_and_overlap_chooses_earlier_offset(tmp_path,instant,expected):
    _,detail=run(tmp_path,instant+'.atZone(ZoneId.of("America/New_York")).toInstant().toEpochMilli()',{'timezone_database':'2026e'})
    assert detail['paths'][0]['steps'][0]['response']['body']==expected


def test_date_constructor_floors_fractional_milliseconds_and_keeps_negative_epoch(tmp_path):
    _,detail=run(tmp_path,'new Date().getTime()',{'clock':'1969-12-31T23:59:59.999999Z'})
    assert detail['paths'][0]['steps'][0]['response']['body']==-1


def test_date_millis_round_trip_does_not_depend_on_float_timestamp(tmp_path):
    _,detail=run(tmp_path,'Date.from(new Date(-1L).toInstant()).getTime()')
    assert detail['paths'][0]['steps'][0]['response']['body']==-1


def test_current_date_uses_supplied_zone_at_midnight_boundary(tmp_path):
    _,detail=run(tmp_path,'LocalDate.now().toString()',{'clock':'2026-01-02T00:30:00Z','timezone':'America/Los_Angeles','timezone_database':'2026e'})
    assert detail['paths'][0]['steps'][0]['response']['body']=='2026-01-01'


@pytest.mark.parametrize('expression,context,reason',[
    ('Instant.now().toEpochMilli()',{},'analysis clock'),
    ('LocalDate.now().toEpochDay()',{'clock':'2026-01-02T00:00:00Z'},'timezone'),
    ('LocalDate.now().toEpochDay()',{'clock':'2026-01-02T00:00:00Z','timezone':'Europe/Paris'},'timezone_database'),
    ('Instant.now().toEpochMilli()',{'clock':'2026-01-02T00:00:00.123456789Z'},'nanosecond'),
    ('LocalDate.of(10000,1,1).toEpochDay()',{},'year'),
])
def test_unprovided_or_unrepresentable_time_stops_with_diagnostics(tmp_path,expression,context,reason):
    _,detail=run(tmp_path,expression,context)
    assert all(path['coverage']=='cutoff' for path in detail['paths'])
    assert any(reason in note['message'] for path in detail['paths'] for note in path['diagnostics'])


def test_java_temporal_http_codec_is_not_fabricated_as_object_fields(tmp_path):
    _,detail=run(tmp_path,'LocalDate.of(2026,1,2)')
    response=detail['paths'][0]['steps'][0]['response']
    assert response['body']['kind']=='Unknown' and 'codec' in response['body']['reason']
    assert response['status']['kind']=='Unknown'


def test_zone_conversion_overflow_remains_a_model_limit(tmp_path):
    _,detail=run(tmp_path,'LocalDate.of(1,1,1).atStartOfDay().atZone(ZoneId.of("Asia/Tokyo")).toInstant().toEpochMilli()',{'timezone_database':'2026e'})
    assert all(path['coverage']=='cutoff' for path in detail['paths'])
    assert any('range' in note['message'] for path in detail['paths'] for note in path['diagnostics'])


def test_unmodeled_java_time_method_does_not_fall_through_to_generic_string_coercion(tmp_path):
    _,detail=run(tmp_path,'new Date(0L).toString()')
    assert all(path['coverage']=='cutoff' for path in detail['paths'])
    assert any('instance method' in note['message'] for path in detail['paths'] for note in path['diagnostics'])


@pytest.mark.parametrize('identifier',['UTC+01:00','Z','Unavailable/Region'])
def test_zone_outside_iana_subset_does_not_fabricate_a_java_exception(tmp_path,identifier):
    _,detail=run(tmp_path,'ZoneId.of("'+identifier+'").getId()',{'timezone_database':'2026e'})
    assert all(path['coverage']=='cutoff' for path in detail['paths'])
    assert any('ZoneId needs' in note['message'] for path in detail['paths'] for note in path['diagnostics'])


def test_source_time_named_class_keeps_source_constructor_and_methods(tmp_path):
    source='''import org.springframework.web.bind.annotation.*;
class Date {long getTime(){return 17L;}}
@RestController class Endpoint {@GetMapping("/value") long value(){return new Date().getTime();}}'''
    p,store,ids=fixture(tmp_path,{'Endpoint.java':source})
    block,detail=analyze(p,store,{},scenario({'path':'/value'}))
    assert detail['paths'][0]['steps'][0]['response']['body']==17
    assert any(edge['target']==ids['Date.getTime'] for edge in block['edges'])
