"""Run inference with Python audit hooks blocking network and reference inputs."""
import sys
from pathlib import Path

written_outputs = set()
audit_stats = {'blocked_network': 0, 'blocked_processes': 0, 'blocked_reference_reads': 0, 'python_file_reads': 0}
declared_inputs = []
for option in ('--source','--skeleton','--context','--scenarios'):
    if option in sys.argv and sys.argv.index(option)+1<len(sys.argv):
        path=Path(sys.argv[sys.argv.index(option)+1]).resolve()
        declared_inputs.append((path,path.is_dir()))
protected_gold = next((parent/'tt-challenge/gold' for parent in Path(__file__).resolve().parents
                       if (parent/'tt-challenge/gold').is_dir()),None)


def audit(event, args):
    if event in ('socket.connect', 'socket.getaddrinfo', 'subprocess.Popen', 'os.system'):
        audit_stats['blocked_network' if event.startswith('socket.') else 'blocked_processes'] += 1
        raise PermissionError('Offline inference blocked: ' + event)
    if event == 'open' and isinstance(args[0], (str, bytes)):
        path, mode, _ = args
        reading = not isinstance(mode, str) or not any(c in mode for c in 'wax')
        if not reading:
            written_outputs.add(str(Path(path).resolve()))
        else:
            audit_stats['python_file_reads'] += 1
        parts = Path(path).parts
        resolved=Path(path).resolve()
        explicit=any(resolved==root or directory and resolved.is_relative_to(root) for root,directory in declared_inputs)
        gold=protected_gold is not None and resolved.is_relative_to(protected_gold)
        reference=any(p in ('gold','runs','sample','benchmark') for p in parts) or Path(path).name in ('submission.json','solution.zip')
        if reading and (gold or not explicit and reference) and str(resolved) not in written_outputs:
            audit_stats['blocked_reference_reads'] += 1
            raise PermissionError('Reference/previous-answer input blocked: ' + str(path))


if __name__ == '__main__':
    from analyzer.portable import main
    sys.addaudithook(audit)
    try:
        main()
    finally:
        import json
        if '--report' in sys.argv:
            report_path = Path(sys.argv[sys.argv.index('--report') + 1])
            report_path.with_name(report_path.stem + '-offline-audit.json').write_text(json.dumps(audit_stats, indent=2) + '\n')
