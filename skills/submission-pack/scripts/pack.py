#!/usr/bin/env python3
"""Сборка посылки для платформы: zip из папки готового варианта.

    py -3 skills/submission-pack/scripts/pack.py --variant solutions_G/—_feature

Скрипт собирает архив, проверяет содержимое самого архива (submission.json в
корне, ответ читается, совпадает с ответом на диске и проходит официальную
проверку формата), считает хеши и записывает акт в benchmark/pack.json.
Существующий архив не перезаписывается без --force.

Коды выхода: 0 — посылка собрана и проверена; 1 — проверки не пройдены;
2 — сборка невозможна (нет папки, ответа, кода, пакета организаторов).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

CHECK_ENV = {"PYTHONUTF8": "1", "PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1"}

#: каталоги, которые никогда не попадают в посылку
EXCLUDED_DIRS = {
    ".venv", "venv", "env", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", ".git", ".hg", ".idea", ".vscode", ".vs", "node_modules",
}
#: файлы, которые никогда не попадают в посылку
EXCLUDED_FILES = {".DS_Store", "Thumbs.db", "desktop.ini", ".gitignore"}
#: расширения, которые никогда не попадают в посылку
EXCLUDED_SUFFIXES = (".pyc", ".pyo", ".zip")
#: служебные файлы самого варианта
EXCLUDED_RELATIVE = {"benchmark/pack.json"}


def force_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def find_challenge(start: Path) -> Path | None:
    cur = start.resolve()
    if cur.is_file():
        cur = cur.parent
    for folder in (cur, *cur.parents):
        if (folder / "tt-challenge" / "platform" / "evaluate_golden.py").is_file():
            return folder / "tt-challenge"
    return None


def run(cmd, cwd: Path | None = None):
    env = dict(os.environ)
    env.update(CHECK_ENV)
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


def relative_to_repo(path: Path) -> str:
    for folder in (path, *path.parents):
        if (folder / "tt-challenge").is_dir() or (folder / ".git").exists():
            try:
                return path.relative_to(folder).as_posix()
            except ValueError:
                return path.as_posix()
    return path.as_posix()


def collect_files(variant: Path) -> list[Path]:
    """Файлы варианта, которые попадут в архив (относительные пути, отсортированы)."""
    files: list[Path] = []
    for path in sorted(variant.rglob("*")):
        rel = path.relative_to(variant)
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        if not path.is_file():
            continue
        if rel.name in EXCLUDED_FILES or rel.name.lower().endswith(EXCLUDED_SUFFIXES):
            continue
        if rel.as_posix() in EXCLUDED_RELATIVE:
            continue
        files.append(rel)
    return files


def expected_scenarios(challenge: Path) -> list[str]:
    """Сценарии задания — по файлам tt-challenge/scenarios/ (S0–S7)."""
    folder = challenge / "scenarios"
    if not folder.is_dir():
        return []
    return sorted(path.stem for path in folder.glob("S*.json") if path.is_file())


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        return exc


def main() -> int:
    force_utf8()
    parser = argparse.ArgumentParser(
        description="Сборка и проверка посылки (zip) из папки варианта",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--variant", required=True, help="папка варианта с submission.json")
    parser.add_argument("--out", help="куда положить архив (по умолчанию <вариант>/solution.zip)")
    parser.add_argument("--force", action="store_true", help="перезаписать существующий архив")
    parser.add_argument("--challenge", help="путь к tt-challenge (по умолчанию ищется вверх по дереву)")
    parser.add_argument("--python", default=sys.executable, help="интерпретатор для дочерних запусков")
    args = parser.parse_args()

    variant = Path(args.variant).resolve()
    if not variant.is_dir():
        print(f"нет папки варианта: {variant}", file=sys.stderr)
        return 2
    submission = variant / "submission.json"
    if not submission.is_file():
        print(f"нет ответа: {submission}", file=sys.stderr)
        return 2
    if not (variant / "code").is_dir():
        print(f"нет кода решения: {variant / 'code'}", file=sys.stderr)
        return 2
    out = Path(args.out).resolve() if args.out else variant / "solution.zip"
    if out.exists() and not args.force:
        print(f"архив уже есть: {out} (пересборка — с --force)", file=sys.stderr)
        return 2
    challenge = Path(args.challenge).resolve() if args.challenge else find_challenge(variant)
    if challenge is None or not (challenge / "platform" / "evaluate_golden.py").is_file():
        print("не найден пакет организаторов tt-challenge (укажите --challenge)", file=sys.stderr)
        return 2

    failures: list[str] = []
    lines: list[str] = []

    answer = submission.read_bytes()
    parsed = load_json(submission)
    if isinstance(parsed, Exception):
        failures.append(f"submission.json не читается как JSON: {parsed}")
    elif not isinstance(parsed, dict) or not isinstance(parsed.get("scenarios"), dict):
        failures.append("submission.json без словаря scenarios")

    files = collect_files(variant)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in files:
            zf.write(variant / rel, rel.as_posix())
    archive_bytes = out.stat().st_size
    archive_hash = sha256(out.read_bytes())

    lines.append(f"вариант:  {relative_to_repo(variant)}")
    lines.append(f"архив:    {relative_to_repo(out)} ({archive_bytes} байт)")
    lines.append(f"файлов:   {len(files)}")
    lines.append(f"sha256 ответа:   {sha256(answer)}")
    lines.append(f"sha256 ответа (LF): {sha256(to_lf(answer))}")
    lines.append(f"sha256 архива:   {archive_hash}")

    # --- проверка самого архива, а не папки
    lines.append("")
    lines.append("ПРОВЕРКА АРХИВА")
    lines.append("---------------")
    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
        if "submission.json" in names:
            lines.append("  submission.json в корне: да")
        else:
            lines.append("  submission.json в корне: НЕТ")
            failures.append("в архиве нет submission.json в корне")
        inside = zf.read("submission.json") if "submission.json" in names else b""
        if inside == answer:
            lines.append("  ответ в архиве совпадает с ответом на диске: да")
        else:
            lines.append("  ответ в архиве совпадает с ответом на диске: НЕТ")
            failures.append("ответ в архиве отличается от ответа на диске")
        junk = [
            name for name in names
            if any(part in EXCLUDED_DIRS for part in Path(name).parts)
            or Path(name).name in EXCLUDED_FILES
            or name.lower().endswith(EXCLUDED_SUFFIXES)
        ]
        lines.append(f"  запрещённых файлов: {len(junk)}" + (f" — {'; '.join(junk[:5])}" if junk else ""))
        if junk:
            failures.append("в архиве запрещённые файлы")

    # --- официальная проверка формата по копии из архива
    format_report = None
    accepted = 0
    rejected: dict[str, int] = {}
    warnings = 0
    if inside:
        with tempfile.TemporaryDirectory(prefix="pack-check-") as tmp:
            extracted = Path(tmp) / "submission.json"
            extracted.write_bytes(inside)
            code, out_text, err_text = run([
                args.python, "-B", challenge / "platform" / "evaluate_golden.py",
                "--check", challenge / "skeleton" / "trainticket.json.gz", extracted, "--json",
            ])
            try:
                format_report = json.loads(out_text)
            except ValueError:
                format_report = None
            if format_report is None:
                lines.append(f"  официальная проверка формата: не разобрана (код {code})")
                if err_text.strip():
                    lines.append(f"    stderr: {err_text.strip()[:200]}")
                failures.append("формат по копии из архива не проверен")
            else:
                for block in (format_report.get("scenarios") or {}).values():
                    accepted += block.get("accepted", 0)
                    for reason, count in (block.get("rejected") or {}).items():
                        rejected[reason] = rejected.get(reason, 0) + count
                    warnings += len(block.get("warnings") or [])
                status = format_report.get("status")
                lines.append(
                    f"  официальная проверка формата: {status}, принято рёбер {accepted}, "
                    f"отклонено {sum(rejected.values())}, предупреждений {warnings}"
                )
                for reason, count in sorted(rejected.items(), key=lambda kv: -kv[1]):
                    lines.append(f"    {reason}: {count}")
                if format_report.get("status") == "invalid":
                    for message in format_report.get("errors", []):
                        lines.append(f"    ошибка: {message}")
                    failures.append("формат: сдача не принята")
                if rejected:
                    failures.append(f"формат: отклонённых рёбер {sum(rejected.values())}")

    # --- полнота набора сценариев
    expected = expected_scenarios(challenge)
    scenarios = sorted((parsed or {}).get("scenarios", {}) if isinstance(parsed, dict) else {})
    if expected:
        missing = [sid for sid in expected if sid not in scenarios]
        lines.append(f"  сценарии: {', '.join(scenarios) if scenarios else 'нет'}"
                     + (f"; нет ответа на {', '.join(missing)}" if missing else ""))
        if missing:
            failures.append(f"нет ответа на сценарии: {', '.join(missing)}")

    # --- акт
    pack_act = {
        "created": datetime.now().astimezone().isoformat(timespec="seconds"),
        "variant": relative_to_repo(variant),
        "archive": relative_to_repo(out),
        "archive_sha256": archive_hash,
        "archive_bytes": archive_bytes,
        "submission": {
            "sha256": sha256(answer),
            "sha256_lf": sha256(to_lf(answer)),
            "bytes": len(answer),
            "scenarios": scenarios,
        },
        "files": [rel.as_posix() for rel in files],
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "format_check": None if format_report is None else {
            "status": format_report.get("status"),
            "accepted": accepted,
            "rejected": rejected,
            "warnings": warnings,
        },
        "scenarios_expected": expected,
    }
    act_path = variant / "benchmark" / "pack.json"
    act_path.parent.mkdir(parents=True, exist_ok=True)
    act_path.write_text(json.dumps(pack_act, ensure_ascii=False, indent=1), encoding="utf-8")

    lines.append("")
    lines.append(f"акт: {relative_to_repo(act_path)}")
    lines.append("")
    lines.append("ИТОГ")
    lines.append("-----")
    if failures:
        for reason in failures:
            lines.append(f"  не пройдено: {reason}")
        lines.append("  ВЕРДИКТ: посылка не прошла проверку")
    else:
        lines.append("  ВЕРДИКТ: посылка собрана и проверена")

    print("\n".join(lines))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
