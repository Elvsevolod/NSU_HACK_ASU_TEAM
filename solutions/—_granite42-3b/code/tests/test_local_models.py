import hashlib
import json
import sys
import types

import pytest

import analyzer.local_models as local_models
from analyzer.local_models import LocalParser, manifest_at
from package_solution import solution_number


GENERATION = {'n_ctx': 8192, 'max_tokens': 1800, 'seed': 0, 'temperature': 0.7,
              'top_p': 0.8, 'top_k': 20, 'enable_thinking': False}
SCHEMA = {'type': 'object', 'properties': {'ok': {'type': 'boolean'}},
          'required': ['ok'], 'additionalProperties': False}


def parser_spec(**generation):
    return {'backend': 'mlx-lm', 'repo': 'example/parser', 'revision': 'rev1', 'path': 'parser',
            'local_path': '/nonexistent/parser', 'sha256': {},
            'generation': dict(GENERATION, **generation)}


class FakeTokenizer:
    bos_token = None

    def __init__(self):
        self.template_calls = []

    def apply_chat_template(self, messages, **kwargs):
        from copy import deepcopy
        self.template_calls.append({'messages': deepcopy(messages), 'kwargs': dict(kwargs)})
        return 'PROMPT::' + '|'.join(message['content'] for message in messages)

    def encode(self, text, add_special_tokens=True):
        return list(range(len(text)))


class FakeResponse:
    def __init__(self, text, finish_reason=None, generation_tokens=0, prompt_tps=11.0,
                 generation_tps=22.0, peak_memory=0.5):
        self.text, self.finish_reason, self.generation_tokens = text, finish_reason, generation_tokens
        self.prompt_tps, self.generation_tps, self.peak_memory = prompt_tps, generation_tps, peak_memory


def install(monkeypatch, responses=None, **generation):
    spec = parser_spec(**generation)
    tokenizer = FakeTokenizer()
    state = {'loads': [], 'sampler': [], 'seeds': [], 'grammars': [], 'streams': [],
             'backends': [], 'grammar_objects': []}

    def load(spec_arg):
        state['loads'].append(spec_arg)
        return 'fake-model', tokenizer, 'fake-wrapped'

    def make_sampler(config):
        state['sampler'].append(dict(config))
        return ('sampler', config['temperature'], config['top_p'], config['top_k'])

    def seed(value):
        state['seeds'].append(value)

    class FakeBackend:
        def __init__(self, wrapped):
            self.wrapped = wrapped
            state['backends'].append(wrapped)

        def get_json_schema_logits_processor(self, json_schema, whitespace_pattern=None):
            state['grammars'].append({'json_schema': json_schema,
                                      'whitespace_pattern': whitespace_pattern})
            processor = ('grammar', len(state['grammars']))
            state['grammar_objects'].append(processor)
            return processor

    def stream(model, tokenizer_arg, prompt, max_tokens, sampler, logits_processors):
        state['streams'].append({'prompt': prompt, 'max_tokens': max_tokens, 'sampler': sampler,
                                 'logits_processors': logits_processors})
        return iter(responses or [FakeResponse('{"ok": true}', 'stop', 3)])

    monkeypatch.setattr(local_models, 'load_parser_runtime', load)
    monkeypatch.setattr(local_models, 'make_sampler', make_sampler)
    monkeypatch.setattr(local_models, 'seed_generation', seed)
    monkeypatch.setattr(local_models, 'build_outlines_backend', FakeBackend)
    monkeypatch.setattr(local_models, 'stream_parser_tokens', stream)
    return spec, tokenizer, state


def test_propose_applies_native_template_without_thinking(monkeypatch):
    spec, tokenizer, state = install(monkeypatch)
    parser = LocalParser(spec)
    payload = {'candidates': [], 'note': 'Данные решения'}
    value = parser.propose('Select the request.', payload, SCHEMA)
    assert value == {'ok': True}
    call = tokenizer.template_calls[0]
    assert call['kwargs'] == {'add_generation_prompt': True, 'tokenize': False, 'enable_thinking': False}
    assert [message['role'] for message in call['messages']] == ['system', 'user']
    assert call['messages'][0]['content'].startswith('You are a constrained source analysis assistant.')
    assert call['messages'][0]['content'].endswith('Select the request.')
    assert call['messages'][1]['content'] == json.dumps(payload, ensure_ascii=False)
    assert state['streams'][0]['prompt'] == 'PROMPT::' + '|'.join(
        message['content'] for message in call['messages'])


def test_generation_budget_uses_rendered_template_tokens(monkeypatch):
    spec, tokenizer, state = install(monkeypatch, n_ctx=1200)
    parser = LocalParser(spec)
    parser.propose('Select the request.', {'candidates': []}, SCHEMA)
    rendered = state['streams'][0]['prompt']
    assert 'You are a constrained source analysis assistant.' in rendered
    assert 'Select the request.' in rendered
    assert state['streams'][0]['max_tokens'] == 1200 - len(rendered)
    assert parser.calls[0]['input_tokens'] == len(rendered)
    assert parser.calls[0]['generation_budget'] == 1200 - len(rendered)


def test_context_budget_error_is_clear(monkeypatch):
    spec, tokenizer, state = install(monkeypatch, n_ctx=1000)
    parser = LocalParser(spec)
    with pytest.raises(ValueError, match='context budget'):
        parser.propose('x' * 900, {}, SCHEMA)
    assert state['streams'] == []


def test_manifest_verifies_every_file_and_detects_tampering(tmp_path):
    entries = {'embedding': {'model.bin': b'embedding-weights', '1_Pooling/config.json': b'{}'},
               'parser': {'config.json': b'config', 'model.safetensors': b'weights',
                          'tokenizer.json': b'tokenizer'}}
    for kind, files in entries.items():
        for name, data in files.items():
            target = tmp_path / kind / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    manifest = {
        'schema': 1,
        'embedding': {'repo': 'example/embedding', 'revision': 'rev0', 'path': 'embedding',
                      'sha256': {name: hashlib.sha256(data).hexdigest()
                                 for name, data in entries['embedding'].items()}},
        'parser': {'repo': 'example/parser', 'revision': 'rev1', 'path': 'parser', 'backend': 'mlx-lm',
                   'generation': GENERATION,
                   'sha256': {name: hashlib.sha256(data).hexdigest()
                              for name, data in entries['parser'].items()}}}
    (tmp_path / 'models-manifest.json').write_text(json.dumps(manifest))
    loaded = manifest_at(tmp_path / 'models-manifest.json')
    assert loaded['parser']['local_path'] == str((tmp_path / 'parser').resolve())
    assert loaded['embedding']['local_path'] == str((tmp_path / 'embedding').resolve())
    extra_weight = tmp_path / 'parser' / 'unlisted.safetensors'
    extra_weight.write_bytes(b'extra-model-weights')
    with pytest.raises(ValueError, match='weight files'):
        manifest_at(tmp_path / 'models-manifest.json')
    extra_weight.unlink()
    (tmp_path / 'parser' / 'tokenizer.json').write_bytes(b'tampered')
    with pytest.raises(ValueError, match='checksum'):
        manifest_at(tmp_path / 'models-manifest.json')


def test_unknown_backend_is_rejected_before_importing_mlx():
    with pytest.raises(ValueError, match='backend'):
        local_models.load_parser_runtime({'backend': 'llama.cpp', 'local_path': '/nonexistent'})


def test_runtime_load_pins_trust_remote_code(monkeypatch):
    calls = {}
    fake_mlx = types.ModuleType('mlx_lm')

    def load(path, **kwargs):
        calls['path'] = path
        calls.update(kwargs)
        return 'model', 'tokenizer'

    fake_mlx.load = load
    fake_outlines = types.ModuleType('outlines')
    fake_outlines.from_mlxlm = lambda model, tokenizer: 'wrapped'
    monkeypatch.setitem(sys.modules, 'mlx_lm', fake_mlx)
    monkeypatch.setitem(sys.modules, 'outlines', fake_outlines)
    assert local_models.load_parser_runtime(
        {'backend': 'mlx-lm', 'local_path': '/model'}) == ('model', 'tokenizer', 'wrapped')
    assert calls == {'path': '/model', 'tokenizer_config': {'trust_remote_code': False},
                     'trust_remote_code': False}


def test_cpu_flag_is_rejected_before_loading(monkeypatch):
    spec, tokenizer, state = install(monkeypatch)
    with pytest.raises(ValueError, match='CPU'):
        LocalParser(spec, cpu=True)
    assert state['loads'] == []


@pytest.mark.parametrize('raw,finish_reason', [
    ('{"ok": "yes"}', 'stop'),
    ('{"ok": tru', 'stop'),
    ('{"ok": false}', 'length'),
])
def test_invalid_or_truncated_output_is_not_cached(monkeypatch, raw, finish_reason):
    spec, tokenizer, state = install(monkeypatch, responses=[FakeResponse(raw, finish_reason, 5)])
    parser = LocalParser(spec)
    with pytest.raises(ValueError):
        parser.propose('Select the request.', {}, SCHEMA)
    assert parser.cache == {} and len(parser.calls) == 1
    assert parser.calls[0]['response'] is None and parser.calls[0]['raw'] == raw
    with pytest.raises(ValueError):
        parser.propose('Select the request.', {}, SCHEMA)
    assert len(state['streams']) == 2


def test_valid_result_is_cached_without_regeneration(monkeypatch):
    spec, tokenizer, state = install(monkeypatch)
    parser = LocalParser(spec)
    first = parser.propose('Select the request.', {'candidates': []}, SCHEMA)
    second = parser.propose('Select the request.', {'candidates': []}, SCHEMA)
    assert first == second == {'ok': True}
    assert len(state['streams']) == 1
    assert len(parser.calls) == 1


def test_sampler_seed_params_and_identity_follow_manifest(monkeypatch):
    spec, tokenizer, state = install(monkeypatch, temperature=1.0, top_p=0.95, top_k=0)
    parser = LocalParser(spec)
    parser.propose('Select the request.', {'candidates': []}, SCHEMA)
    parser.propose('Select another request.', {'candidates': []}, SCHEMA)
    expected = dict(GENERATION, temperature=1.0, top_p=0.95, top_k=0)
    assert state['seeds'] == [0, 0]
    assert state['sampler'] == [expected, expected]
    assert state['streams'][0]['sampler'] == ('sampler', 1.0, 0.95, 0)
    assert len(state['grammars']) == 2
    assert state['streams'][0]['logits_processors'][0] is not state['streams'][1]['logits_processors'][0]
    entry = parser.calls[0]
    assert entry['params'] == {'temperature': 1.0, 'top_p': 0.95, 'top_k': 0, 'seed': 0,
                               'presence_penalty': 0, 'presence_context_size': 20}
    assert entry['model'] == {'backend': 'mlx-lm', 'schema_backend': 'llguidance', 'repo': 'example/parser', 'revision': 'rev1'}


def test_outlines_backend_is_reused_with_fresh_processors(monkeypatch):
    spec, tokenizer, state = install(monkeypatch)
    parser = LocalParser(spec)
    parser.propose('Select the request.', {'candidates': []}, SCHEMA)
    parser.propose('Select another request.', {'candidates': []}, SCHEMA)
    assert state['backends'] == ['fake-wrapped']
    expected_schema = {**SCHEMA, 'x-guidance': {'whitespace_flexible': False}}
    assert [json.loads(item['json_schema']) for item in state['grammars']] == [expected_schema] * 2
    assert 'x-guidance' not in SCHEMA
    assert all(item['whitespace_pattern'] is None for item in state['grammars'])
    assert state['grammar_objects'][0] is not state['grammar_objects'][1]
    assert parser.backend.wrapped == 'fake-wrapped'


def test_trace_entry_records_hashes_tokens_and_trace_file(monkeypatch, tmp_path):
    responses = [FakeResponse('{"ok": fa', 'stop', 1, prompt_tps=9.0, generation_tps=10.0,
                              peak_memory=0.25),
                 FakeResponse('lse}', 'stop', 6, prompt_tps=12.0, generation_tps=33.0,
                              peak_memory=0.5)]
    spec, tokenizer, state = install(monkeypatch, responses=responses)
    trace = tmp_path / 'trace.jsonl'
    parser = LocalParser(spec, trace_path=trace)
    payload = {'candidates': []}
    parser.propose('Select the request.', payload, SCHEMA)
    entry = parser.calls[0]
    assert entry['input_sha256'] == hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, default=str).encode()).hexdigest()
    assert entry['schema_sha256'] == hashlib.sha256(json.dumps(SCHEMA, sort_keys=True).encode()).hexdigest()
    assert entry['input_tokens'] == len(state['streams'][0]['prompt'])
    assert entry['generated_tokens'] == 6 and entry['finish_reason'] == 'stop'
    assert entry['prompt_tps'] == 12.0 and entry['generation_tps'] == 33.0
    assert entry['peak_memory_bytes'] == 500000000.0
    assert entry['schema_seconds'] >= 0.0 and entry['seconds'] >= entry['schema_seconds']
    assert json.loads(trace.read_text()) == entry


def test_close_releases_runtime_and_device_cache(monkeypatch):
    spec, tokenizer, state = install(monkeypatch)
    released = []
    monkeypatch.setattr(local_models, 'clear_device_cache', lambda: released.append(True))
    parser = LocalParser(spec)
    parser.close()
    assert parser.model is None and parser.tokenizer is None and parser.outlines_model is None
    assert parser.backend is None
    assert released == [True]


def test_packaging_keeps_fractional_solution_number():
    assert solution_number('# Решение № 6.1 — qwen35-9b\n') == '6.1'
    assert solution_number('# Решение № 6.2 — granite42-3b\n') == '6.2'
    assert solution_number('Решение № 7 — parent\n') == '7'


def test_presence_penalty_follows_explicit_generation_config(monkeypatch):
    calls = []
    module = types.ModuleType('mlx_lm.sample_utils')
    module.make_logits_processors = lambda **kwargs: calls.append(kwargs) or ['penalty']
    monkeypatch.setitem(sys.modules, 'mlx_lm', types.ModuleType('mlx_lm'))
    monkeypatch.setitem(sys.modules, 'mlx_lm.sample_utils', module)
    assert local_models.make_penalty_processors({'presence_penalty': 0}) == []
    assert calls == []
    assert local_models.make_penalty_processors(
        {'presence_penalty': 1.5, 'presence_context_size': 20}) == ['penalty']
    assert calls == [{'presence_penalty': 1.5, 'presence_context_size': 20}]
