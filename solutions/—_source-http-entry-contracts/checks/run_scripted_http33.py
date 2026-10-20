"""Use the unchanged portable analyzer with an external explicit-input adapter."""
import importlib.util
import json
from pathlib import Path
import sys
from scripted_http_inputs33 import script_grounder


def main():
    import analyzer.portable as portable
    option = Path(sys.argv[sys.argv.index('--scenarios') + 1])
    paths = sorted(option.glob('*.json')) if option.is_dir() else [option]
    recipes = {}
    for path in paths:
        scenario = json.loads(path.read_text())
        for name, recipe in scenario.get('request_scripts', {}).items():
            assert name not in recipes, 'Duplicate client recipe'
            recipes[name] = recipe
    portable.ContractGrounder = script_grounder(recipes)
    guard_path = Path(portable.__file__).parents[1] / 'offline_run.py'
    spec = importlib.util.spec_from_file_location('scripted_offline_guard', guard_path)
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    sys.addaudithook(guard.audit)
    def oracle_guard(event, args):
        if event == 'open' and isinstance(args[0], (str, bytes)):
            path = Path(args[0])
            if path.name in ('oracle.json', 'expected.json', 'labels-dev.json', 'labels-test.json'):
                guard.audit_stats['blocked_reference_reads'] += 1
                raise PermissionError('Independent checker material is not an inference input')
    sys.addaudithook(oracle_guard)
    try:
        portable.main()
    finally:
        report = Path(sys.argv[sys.argv.index('--report') + 1])
        report.with_name(report.stem + '-offline-audit.json').write_text(json.dumps(guard.audit_stats, indent=2) + '\n')


if __name__ == '__main__':
    main()
