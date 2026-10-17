#!/usr/bin/env python3
"""Локальная проверка варианта: S0, формат S0-S7, сверка с родителем, тесты.

Запуск из корня репозитория:

    py -3 skills/s0-check/scripts/check.py --submission solutions_G/—_feature/submission.json
    py -3 skills/s0-check/scripts/check.py --submission ... \\
        --parent solutions/0.909870_field-constructor-projection --require-identical \\
        --save solutions_G/—_feature/benchmark --tests

Коды выхода: 0 — проверки пройдены; 1 — не пройдены; 2 — проверка не выполнена
(не найден пакет организаторов, не читается ответ, неверные аргументы).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

RELATIONS = ("executes", "calls", "remote", "data")
CHECK_ENV = {"PYTHONUTF8": "1", "PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1"}


def force_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def find_challenge(start: Path) -> Path | None:
    """Пакет организаторов: ищем вверх от указанного пути."""
    cur = start.resolve()
    if cur.is_file():
        cur = cur.parent
    for folder in (cur, *cur.parents):
        if (folder / "tt-challenge" / "platform" / "evaluate_golden.py").is_file():
            return folder / "tt-challenge"
    return None


def run(cmd, cwd: Path | None = None, env_extra: dict | None = None):
    env = dict(os.environ)
    env.update(CHECK_ENV)
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(
        [str(x) for x in cmd],
        cwd=str(cwd) if cwd else None,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, proc.stdout, proc.stderr


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def to_lf(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def first_diff(a: bytes, b: bytes) -> int | None:
    limit = min(len(a), len(b))
    for i in range(limit):
        if a[i] != b[i]:
            return i
    return limit if len(a) != len(b) else None


def venv_python(variant: Path) -> str | None:
    """Интерпретатор окружения варианта, если оно создано."""
    for rel in ("Scripts/python.exe", "bin/python", "bin/python3"):
        candidate = variant / ".venv" / rel
        if candidate.is_file():
            return str(candidate)
    return None


def evaluate_s0(py: str, challenge: Path, submission: Path):
    """Официальный S0 по открытому эталону: (код выхода, отчёт, stdout, stderr)."""
    evaluator = challenge / "platform" / "evaluate_golden.py"
    code, out, err = run([py, "-B", evaluator, challenge / "gold" / "S0.json", submission, "--json"])
    report = None
    if out.strip():
        try:
            report = json.loads(out)
        except ValueError:
            report = None
    return code, report, out, err


def ious(report) -> dict:
    """{вид связи: IoU} по посчитанным сценариям отчёта."""
    result = {}
    if not isinstance(report, dict):
        return result
    for block in (report.get("scenarios") or {}).values():
        if block.get("status") != "scored":
            continue
        for rel, value in (block.get("sets") or {}).items():
            result[rel] = value.get("iou")
    return result


def short(text: str, width: int = 110) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= width else text[: width - 1] + "…"


class Report:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.failures: list[str] = []

    def title(self, text: str) -> None:
        self.lines.append("")
        self.lines.append(text)
        self.lines.append("-" * len(text))

    def say(self, text: str = "") -> None:
        self.lines.append(text)

    def fail(self, reason: str) -> None:
        self.failures.append(reason)

    def render(self) -> str:
        self.lines.append("")
        self.lines.append("ИТОГ")
        self.lines.append("-----")
        if self.failures:
            for reason in self.failures:
                self.lines.append(f"  не пройдено: {reason}")
            self.lines.append("  ВЕРДИКТ: проверки не пройдены")
        else:
            self.lines.append("  ВЕРДИКТ: проверки пройдены")
        return "\n".join(self.lines)


def section_s0(rep: Report, py: str, challenge: Path, submission: Path):
    code, report, out, err = evaluate_s0(py, challenge, submission)
    rep.title("S0 по открытому эталону (официальный оценщик)")
    if report is None:
        rep.say(f"  отчёт не разобран (код выхода {code})")
        if err.strip():
            rep.say(f"  stderr: {short(err)}")
        rep.fail("S0 не посчитан")
        return None, code
    status = report.get("status")
    if status == "invalid":
        for message in report.get("errors", []):
            rep.say(f"  ошибка формата: {short(message)}")
        rep.fail("S0: сдача не принята")
        return report, code
    if status != "scored":
        rep.say(f"  статус: {status} — балла нет")
        rep.fail("S0 не посчитан")
        return report, code
    rep.say(f"  балл: {report['score']!r}")
    for sid, block in report.get("scenarios", {}).items():
        if block.get("status") != "scored":
            continue
        parts = []
        for rel in RELATIONS:
            value = block["sets"][rel]
            if value["pred"] == 0 and value["gold"] == 0:
                parts.append(f"{rel} {value['iou']:.3f} (и в эталоне, и в сдаче пусто)")
                continue
            parts.append(
                f"{rel} {value['iou']:.3f} (точность {value['precision']:.2f}, "
                f"полнота {value['recall']:.2f}; сдано {value['pred']}, "
                f"в эталоне {value['gold']}, совпало {value['tp']})"
            )
        rep.say(f"  сценарий {sid}:")
        for part in parts:
            rep.say(f"    {part}")
        rejected = sum(block.get("rejected", {}).values())
        rep.say(
            f"    принято рёбер {block['accepted']}"
            + (f", повторов {block['duplicates']}" if block.get("duplicates") else "")
            + (f", отклонено {rejected}" if rejected else ", отклонённых нет")
        )
        for message in block.get("warnings", []):
            rep.say(f"    предупреждение: {short(message)}")
        if rejected:
            rep.fail(f"S0: отклонённых рёбер {rejected}")
    return report, code


def section_s0_parent(rep: Report, py: str, challenge: Path, parent_file: Path, ours_report):
    """S0 родителя и дельта — чтобы не сверять числа глазами по README."""
    rep.title("S0 родителя (для сравнения)")
    if not parent_file.is_file():
        rep.say(f"  нет ответа родителя: {parent_file}")
        return None
    code, report, out, err = evaluate_s0(py, challenge, parent_file)
    if report is None or report.get("status") != "scored":
        status = "не разобран" if report is None else report.get("status")
        rep.say(f"  S0 родителя не посчитан ({status}, код выхода {code})")
        return None
    rep.say(f"  родитель: {parent_file}")
    own_score = ours_report.get("score") if isinstance(ours_report, dict) else None
    line = f"  балл: {report['score']!r}"
    if isinstance(own_score, (int, float)):
        line += f"; дельта к нашему: {report['score'] - own_score:+.10f}"
    rep.say(line)
    ours_ious = ious(ours_report)
    theirs_ious = ious(report)
    parts = []
    for rel in RELATIONS:
        if rel not in ours_ious or rel not in theirs_ious:
            continue
        mark = "" if abs(ours_ious[rel] - theirs_ious[rel]) < 1e-9 else " — отличается"
        parts.append(f"{rel} {ours_ious[rel]:.3f} → {theirs_ious[rel]:.3f}{mark}")
    if parts:
        rep.say("  виды связи (наш → родителя): " + "; ".join(parts))
    return report


def section_format(rep: Report, py: str, challenge: Path, submission: Path):
    skeleton = challenge / "skeleton" / "trainticket.json.gz"
    evaluator = challenge / "platform" / "evaluate_golden.py"
    code, out, err = run([py, "-B", evaluator, "--check", skeleton, submission, "--json"])
    report = None
    if out.strip():
        try:
            report = json.loads(out)
        except ValueError:
            report = None
    rep.title("Формат S0–S7")
    if report is None:
        rep.say(f"  отчёт не разобран (код выхода {code})")
        if err.strip():
            rep.say(f"  stderr: {short(err)}")
        rep.fail("формат не проверен")
        return None, code
    if report.get("status") == "invalid":
        for message in report.get("errors", []):
            rep.say(f"  ошибка: {short(message)}")
        rep.fail("формат: сдача не принята")
        return report, code
    accepted = 0
    rejected_total = 0
    reasons: dict[str, int] = {}
    warnings: list[str] = []
    scenarios = report.get("scenarios", {})
    for block in scenarios.values():
        accepted += block.get("accepted", 0)
        for reason, count in (block.get("rejected") or {}).items():
            reasons[reason] = reasons.get(reason, 0) + count
            rejected_total += count
        warnings += block.get("warnings") or []
    rep.say(f"  сценариев проверено: {len(scenarios)}")
    rep.say(f"  принято рёбер: {accepted}")
    rep.say(f"  отклонено рёбер: {rejected_total}")
    for reason, count in sorted(reasons.items(), key=lambda kv: -kv[1]):
        rep.say(f"    {reason}: {count}")
    for message in warnings[:10]:
        rep.say(f"  предупреждение: {short(message)}")
    if len(warnings) > 10:
        rep.say(f"  … ещё предупреждений: {len(warnings) - 10}")
    if rejected_total:
        rep.fail(f"формат: отклонённых рёбер {rejected_total}")
    return report, code


def section_parent(rep: Report, submission: Path, parent_dir: Path, require_identical: bool):
    parent_file = parent_dir / "submission.json"
    rep.title("Сверка с родителем")
    if not parent_file.is_file():
        rep.say(f"  нет файла {parent_file}")
        rep.fail("сверка невозможна: у родителя нет submission.json")
        return None
    ours = submission.read_bytes()
    theirs = parent_file.read_bytes()
    raw_same = ours == theirs
    lf_same = to_lf(ours) == to_lf(theirs)
    diff = first_diff(ours, theirs)
    rep.say(f"  родитель: {parent_dir}")
    rep.say(f"  сырые байты:     {'совпадают' if raw_same else 'не совпадают'}")
    rep.say(f"  LF-нормализация: {'совпадают' if lf_same else 'не совпадают'}")
    if not raw_same:
        rep.say(f"  размер: наш {len(ours)}, родитель {len(theirs)}, первое расхождение в байте {diff}")
    if raw_same:
        rep.say("  вывод: ответ не изменился")
    elif lf_same:
        rep.say("  вывод: ответ не изменился, различаются только переводы строк")
    else:
        rep.say("  вывод: ответ изменился")
    if require_identical and not lf_same:
        rep.fail("структурный вариант: ответ отличается от родителя")
    return {
        "parent": str(parent_dir),
        "parent_submission": str(parent_file),
        "ours_sha256": sha256(ours),
        "ours_sha256_lf": sha256(to_lf(ours)),
        "parent_sha256": sha256(theirs),
        "parent_sha256_lf": sha256(to_lf(theirs)),
        "bytes_ours": len(ours),
        "bytes_parent": len(theirs),
        "identical_raw": raw_same,
        "identical_lf": lf_same,
        "first_diff_byte": diff,
    }


def section_tests(rep: Report, py: str, variant: Path):
    tests_dir = variant / "code" / "tests"
    rep.title("Тесты варианта")
    if not tests_dir.is_dir():
        rep.say(f"  нет каталога {tests_dir} — пропущено")
        return None
    code, out, err = run(
        [py, "-B", "-m", "pytest", "code/tests", "-q"],
        cwd=variant,
        env_extra={"PYTHONPATH": "code"},
    )
    tail = [line for line in (out or "").strip().splitlines() if line.strip()]
    summary = tail[-1] if tail else "(нет вывода)"
    rep.say(f"  {short(summary)}")
    if not tail and (err or "").strip():
        rep.say(f"  stderr: {short(err.strip().splitlines()[-1])}")
    rep.say(f"  код выхода: {code}")
    if code != 0:
        rep.fail(f"тесты: код выхода {code}")
        for line in tail[-15:]:
            rep.say(f"    {short(line)}")
    return {"exit_code": code, "summary": summary}


def main() -> int:
    force_utf8()
    parser = argparse.ArgumentParser(
        description="Локальная проверка варианта: S0, формат, сверка с родителем, тесты",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--submission", required=True, help="путь к submission.json варианта")
    parser.add_argument("--parent", help="папка родительского варианта для сверки ответов")
    parser.add_argument("--require-identical", action="store_true",
                        help="считать расхождение с родителем провалом (для структурного рефактора)")
    parser.add_argument("--tests", action="store_true", help="прогнать pytest варианта")
    parser.add_argument("--save", help="каталог benchmark/, куда сохранить отчёты")
    parser.add_argument("--challenge", help="путь к tt-challenge (по умолчанию ищется вверх по дереву)")
    parser.add_argument("--python", default=None,
                        help="интерпретатор для дочерних запусков (по умолчанию — из .venv варианта, иначе текущий)")
    args = parser.parse_args()

    submission = Path(args.submission).resolve()
    if not submission.is_file():
        print(f"не читается {submission}", file=sys.stderr)
        return 2
    variant = submission.parent
    challenge = Path(args.challenge).resolve() if args.challenge else find_challenge(variant)
    if challenge is None or not (challenge / "platform" / "evaluate_golden.py").is_file():
        print("не найден пакет организаторов tt-challenge (укажите --challenge)", file=sys.stderr)
        return 2

    py = args.python or venv_python(variant) or sys.executable
    rep = Report()
    data = submission.read_bytes()
    rep.say(f"вариант: {variant}")
    rep.say(f"ответ:   {submission} ({len(data)} байт)")
    rep.say(f"sha256 ответа:      {sha256(data)}")
    rep.say(f"sha256 ответа (LF): {sha256(to_lf(data))}")
    rep.say(f"пакет:   {challenge}")
    rep.say(f"python:  {py}")

    s0_report, _ = section_s0(rep, py, challenge, submission)
    if args.parent:
        section_s0_parent(rep, py, challenge,
                          Path(args.parent).resolve() / "submission.json", s0_report)
    format_report, _ = section_format(rep, py, challenge, submission)
    comparison = None
    if args.parent:
        comparison = section_parent(rep, submission, Path(args.parent).resolve(), args.require_identical)
    tests = section_tests(rep, py, variant) if args.tests else None

    if args.save:
        save_dir = Path(args.save)
        save_dir.mkdir(parents=True, exist_ok=True)
        if s0_report is not None:
            (save_dir / "evaluation.json").write_text(
                json.dumps(s0_report, ensure_ascii=False, indent=1), encoding="utf-8")
        if format_report is not None:
            (save_dir / "format_check.json").write_text(
                json.dumps(format_report, ensure_ascii=False, indent=1), encoding="utf-8")
        if comparison is not None:
            (save_dir / "comparison.json").write_text(
                json.dumps(comparison, ensure_ascii=False, indent=1), encoding="utf-8")
        rep.title("Сохранено")
        for name in ("evaluation.json", "format_check.json", "comparison.json"):
            if (save_dir / name).is_file():
                rep.say(f"  {save_dir / name}")
        if tests is not None:
            rep.say("  тесты не сохраняются: вывод выше")

    print(rep.render())
    return 1 if rep.failures else 0


if __name__ == "__main__":
    sys.exit(main())
