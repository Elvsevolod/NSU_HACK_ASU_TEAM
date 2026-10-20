"""Record observed site receipts without touching assessed code or ZIP bytes."""
import hashlib
import json
import shutil
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

V = Path(__file__).resolve().parents[1]
ROOT = V.parents[1]


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    assert V.name == '—_state-semantics-and-retrieval'
    destination = V.with_name('0.22997_state-semantics-and-retrieval')
    assert not destination.exists()
    candidate = Path('/Users/elvsevolod/Downloads/submit_1666111 (1).zip')
    restored = Path('/Users/elvsevolod/Downloads/submit_1666114.zip')
    archive_sha = '7c827af7802db725c714b99adfa87f1578fddd775267b86f31da7868a0db645a'
    submission_sha = '7c9e2664e30368f7509f871941070c72c721ef2f76fefa1340f334ee4c3f75ce'
    best_sha = 'f574de87739df8a679fff57d632b792c3a4742de7cb1d146d9b92fd2d7db0e46'
    assert sha(candidate) == sha(V/'solution.zip') == archive_sha
    assert sha(V/'submission.json') == submission_sha
    assert sha(restored) == sha(ROOT/'solutions/0.909870_field-constructor-projection/solution.zip') == best_sha
    shutil.copyfile(candidate, V/'benchmark/site/server-1666111.zip')
    shutil.copyfile(restored, V/'benchmark/site/restored-server-1666114.zip')
    observed = json.loads((V/'benchmark/site/scenarios-1666111.json').read_text())
    scores = dict(zip((f'S{i}' for i in range(1, 8)), observed['scores'], strict=True))
    parent = json.loads((ROOT/'solutions/0.39232_typed-collection-continuations/benchmark/site-score.json').read_text())
    deltas = {name: str(Decimal(value)-Decimal(parent['scenario_scores'][name])) for name,value in scores.items()}
    now = datetime.now(timezone.utc).isoformat()
    screenshots = [{'path': 'benchmark/site/'+name, 'sha256': sha(V/'benchmark/site'/name),
                    'unmodified': True, 'file_mtime_utc': datetime.fromtimestamp((V/'benchmark/site'/name).stat().st_mtime, timezone.utc).isoformat()}
                   for name in ('result-1666111.jpg', 'ranking-1666111.jpg', 'restored-1666114-full.jpg')]
    site = {'schema': 'site-score/32', 'variant':32, 'parent':31, 'status':'verified',
            'verdict':'A', 'submission_id':'1666111', 'submitted_site_time':'2026-10-19 13:44:49',
            'site_timezone':'Asia/Barnaul', 'recorded_at_utc':now,
            'score':'0.22997', 'score_display':'0.22997', 'ranking_score':'0.229970',
            'scenario_scores':scores, 'parent_score':parent['score'],
            'delta_from_parent':str(Decimal('0.22997')-Decimal(parent['score'])),
            'delta_scenarios_from_parent':deltas, 'archive_sha256':archive_sha,
            'submission_sha256':submission_sha, 'local_S0_is_separate':'0.8008928571428572',
            'source':'NSUts result receipt and ASU Team ranking DOM aria-label values before restoration; raw DOM-backed row retained.',
            'screenshots':screenshots,
            'causality_limit':'All seven scenario scores declined. Hidden per-edge gold is unavailable; this does not identify which prediction delta is correct.'}
    save(V/'benchmark/site-score.json', site)
    save(V/'benchmark/server-verification.json', {'passed':True, 'submission_id':'1666111',
         'archive_sha256':archive_sha, 'downloaded_archive_sha256':sha(candidate),
         'submission_sha256':submission_sha, 'code_and_judge_zip_unchanged':True})
    save(V/'benchmark/site-best-restored.json', {'passed':True, 'submission_id':'1666114',
         'submitted_site_time':'2026-10-19 13:52:06', 'verdict':'A', 'score':'0.90987',
         'restored_variant':5, 'archive_sha256':best_sha, 'downloaded_archive_sha256':sha(restored),
         'screenshot':'benchmark/site/restored-1666114-full.jpg',
         'source':'Visible NSUts result row, independently downloaded source ZIP hash comparison'})
    readme = V/'README.md'
    text = readme.read_text().replace('| Score сайта | — (не получен) |', '| Score сайта | 0.22997; A; посылка 1666111 |')
    text += '\nОценка сайта снизилась относительно № 31 на **0.16235**. Все S1–S7 ухудшились; точные значения и дельты — в [site-score.json](benchmark/site-score.json). Это отдельная регрессия качества, которую успешные локальные проверки не отменяют. Оценённые code/submission/solution.zip сохранены. Лучшая посылка № 5 восстановлена: 1666114, A, 0.90987.\n'
    readme.write_text(text)
    review = V/'CAUSAL_REVIEW.md'
    review.write_text(review.read_text() + '\n## Реальная оценка сайта\n\n№ 32 отправлен как 1666111: A, **0.22997**. По сравнению с № 31 общий score снизился на **0.16235**, все семь сценариев ухудшились. Точные значения и дельты сохранены в benchmark/site-score.json; локальный S0 не изменился. Скачанный серверный ZIP совпал с оценённым solution.zip побайтно. Это регрессия скрытого качества; локальная корректность отдельных native-контрактов не доказывает полноту сценарных графов. Прямых оснований приписывать падение одному ремонту без hidden gold нет. Причинные stage deltas и новые first-loss witnesses позволяют поставить следующий независимый эксперимент; возвращать исчезнувшие рёбра вручную нельзя.\n\nВосстановлен исходный ZIP лучшего № 5: посылка 1666114, A, 0.90987. Серверный архив восстановления имеет исходный SHA256 f574de87739df8a679fff57d632b792c3a4742de7cb1d146d9b92fd2d7db0e46. Результат № 32 не заменён этой оценкой. Новая реализация после site judgement не менялась.\n')
    state_path = V/'development/implementation-state.json'
    state = json.loads(state_path.read_text())
    state['site'] = {'candidate':'benchmark/site-score.json', 'restored':'benchmark/site-best-restored.json'}
    state['updated_at'] = now
    state['current_goal'] = 'analytic-archive-verification'
    state['next_action'] = 'Verify exact analytical archive; two independent real transfer packages remain absent and not_run. Qwen and lexical B adoption rejected on measured downstream errors.'
    save(state_path, state)
    registry = ROOT/'solutions/README.md'
    original = registry.read_bytes()
    assert hashlib.sha256(original).hexdigest() == '4291b7f7010fe0d9a9e73f7068ca906982ca3e60cd1f8007325e0125840a179a'
    score_row = '| 32 | ' + ' | '.join(value.replace('.', ',') for value in scores.values()) + ' | **0,22997** |'
    delta_row = '| Δ № 32 − № 31 | ' + ' | '.join(value.replace('.', ',') for value in deltas.values()) + ' | **−0,16235** |'
    addition = '\n\nРешение № 32 — [state-semantics-and-retrieval](0.22997_state-semantics-and-retrieval/README.md), родитель № 31.\n\n| № | Фича | Score сайта | Тестовый score S0 | Результаты |\n| --- | --- | --- | --- | --- |\n| 32 | state-semantics-and-retrieval | **0,22997** | 0,8008928571 | [Причинный разбор](0.22997_state-semantics-and-retrieval/CAUSAL_REVIEW.md) |\n\n| № | S1 | S2 | S3 | S4 | S5 | S6 | S7 | Итог |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n' + score_row + '\n' + delta_row + '\n\nR01–R06 проверены в заявленных ограниченных контрактах; 2080 тестов и 17 интеграционных запусков проходят. Unicode lexical B и локальный Qwen-пилот отклонены по downstream-проверкам, прежний retrieval A сохранён. Два новых реальных transfer-пакета отсутствуют: всю R01–R08 нельзя объявить verified. На сайте все семь сценариев ухудшились относительно № 31, общий score −0,16235; причины hidden edge errors ещё не установлены. Источник — [реальные site receipts и хеши](0.22997_state-semantics-and-retrieval/benchmark/site-score.json). После проверки восстановлен неизменённый № 5: 1666114, A, 0,90987; код, ответ и оценённый ZIP № 32 не менялись.\n'
    registry.write_bytes(original + addition.encode())
    assert registry.read_bytes().startswith(original)
    save(V/'development/registry-append.json', {'passed':True, 'old_bytes':len(original),
         'old_sha256':hashlib.sha256(original).hexdigest(), 'new_sha256':sha(registry),
         'original_prefix_unchanged':True, 'only_appended_variant32_record':True})
    V.rename(destination)
    print(destination)


if __name__ == '__main__':
    main()
