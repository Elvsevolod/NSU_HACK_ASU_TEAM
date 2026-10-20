"""Exercise manifest rejection and the analyzer's offline audit before edits."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

VARIANT = Path(__file__).resolve().parents[1]
ROOT = VARIANT.parents[1]


def main():
    source = ROOT / 'tt-challenge/skeleton/trainticket.json.gz'
    expected = json.loads((VARIANT / 'development/input-sha256.json').read_text())[
        source.relative_to(ROOT).as_posix()]
    with tempfile.TemporaryDirectory(prefix='manifest31-') as folder:
        copied = Path(folder) / source.name
        copied.write_bytes(source.read_bytes())
        before = hashlib.sha256(copied.read_bytes()).hexdigest()
        changed = bytearray(copied.read_bytes())
        changed[-1] ^= 1
        copied.write_bytes(changed)
        after = hashlib.sha256(copied.read_bytes()).hexdigest()
    assert before == expected and after != expected
    guards = []
    for label, operation in [
        ('network', "__import__('socket').getaddrinfo('audit.invalid', 80)"),
        ('process', "__import__('os').system('echo forbidden')"),
        ('reference', "open('benchmark/forbidden-reference.json').read()"),
    ]:
        code = ('import sys,json;sys.path.insert(0,' + repr(str(VARIANT / 'code')) + ');'
                'import offline_run;sys.addaudithook(offline_run.audit)\n'
                'try:\n ' + operation + '\n'
                'except PermissionError as error:\n print(json.dumps({"blocked":True,"reason":str(error)}))\n'
                'else:\n raise AssertionError("audit did not reject operation")\n')
        run = subprocess.run([sys.executable, '-B', '-c', code], cwd=VARIANT,
                             capture_output=True, text=True, timeout=20)
        assert run.returncode == 0, (label, run.stderr)
        guards.append({'kind': label, 'returncode': run.returncode, **json.loads(run.stdout)})
    result = {'passed': True, 'manifest_accepts_copy': before == expected,
              'manifest_rejects_one_byte_mutation': after != expected, 'guards': guards,
              'targets_started': False}
    output = VARIANT / 'benchmark/overnight/G01/baseline-gates.json'
    assert not output.exists()
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
