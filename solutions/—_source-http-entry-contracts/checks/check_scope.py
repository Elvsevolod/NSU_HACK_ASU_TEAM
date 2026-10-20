"""Inspect the introduced inference delta; runtime read evidence is checked separately."""
import ast,difflib,hashlib,json,re
from pathlib import Path
V=Path(__file__).resolve().parents[1]


def main():
    baseline=V/'development/stages/G01-parent30/code';issues=[];changed=[]
    for path in sorted((V/'code/analyzer').glob('*.py')):
        old=baseline/'analyzer'/path.name;before=old.read_text() if old.exists() else '';after=path.read_text()
        if before==after:continue
        changed.append(path.name)
        added='\n'.join(line[1:] for line in difflib.unified_diff(before.splitlines(),after.splitlines()) if line.startswith('+') and not line.startswith('+++'))
        if re.search(r'\bS[0-7]\b|trainticket|2f106aca|G1234|Ning Bo',added):issues.append('scenario/project literal in introduced production delta: '+path.name)
        for node in ast.walk(ast.parse(after)):
            names=[node.module or ''] if isinstance(node,ast.ImportFrom) else [n.name for n in node.names] if isinstance(node,ast.Import) else []
            if any(re.match(r'(?:checks|openai|deepseek|opencode|solutions)(?:\.|$)',n) for n in names):issues.append('forbidden production import: '+path.name)
    b=ast.parse((baseline/'analyzer/contracts.py').read_text());c=ast.parse((V/'code/analyzer/contracts.py').read_text())
    rank=lambda t:next(n for n in ast.walk(t) if isinstance(n,ast.FunctionDef) and n.name=='rank')
    ranking=ast.dump(rank(b))==ast.dump(rank(c))
    paths=(V/'code/analyzer/paths.py').read_text();oldpaths=(baseline/'analyzer/paths.py').read_text()
    budgets=all(term in paths and term in oldpaths for term in ['completion_budget=max(8,limit)','completion_splits+len(branch.choices)<=completion_budget','completion_splits+len(completion.choices)<=completion_budget'])
    guard='self.calls >= 12000 or len(self.active) >= 64'
    budgets=budgets and guard in (V/'code/analyzer/engine.py').read_text() and guard in (baseline/'analyzer/engine.py').read_text()
    pilot_not_default=not any('residual_state_pilot' in p.read_text() or 'order_completion_probe' in p.read_text() for p in (V/'code').rglob('*.py'))
    result={'passed':not issues and ranking and budgets and pilot_not_default,'introduced_production_issues':issues,
        'ranking_function_AST_unchanged':ranking,'global_call_recursion_completion_budgets_unchanged':budgets,
        'G06_checker_only_not_imported':pilot_not_default,'changed_production_modules':changed,
        'scope':'Static introduced-delta checks plus separate actual offline audit; not a proof about arbitrary future behavior.'}
    (V/'development/scope-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));assert result['passed']


if __name__=='__main__':main()
