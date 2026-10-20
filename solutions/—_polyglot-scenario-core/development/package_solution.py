"""Package the frozen variant; no source repositories or environments included."""
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

VARIANT = Path(__file__).resolve().parents[1]


def main():
    excluded = {"solution.zip", "benchmark/archive-manifest.json", "benchmark/archive-verification.json"}
    files = {}
    with ZipFile(VARIANT / "solution.zip", "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(VARIANT.rglob("*")):
            relative = path.relative_to(VARIANT)
            if not path.is_file() or path.is_symlink() or set(relative.parts) & {".venv", "__pycache__", ".pytest_cache"}:
                continue
            name = relative.as_posix()
            if name in excluded or name.endswith(".pyc") or path.name == ".DS_Store" or path.name == "ir-cache.json" or name.startswith("benchmark/standalone"):
                continue
            data = path.read_bytes()
            info = ZipInfo(name, (2026, 10, 17, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
            files[name] = hashlib.sha256(data).hexdigest()
    assert {"submission.json", "README.md", "requirements.lock.txt", "THIRD_PARTY.md", "code/offline_run.py"} <= set(files)
    report = {"sha256": hashlib.sha256((VARIANT / "solution.zip").read_bytes()).hexdigest(), "files": files}
    (VARIANT / "benchmark/archive-manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"sha256": report["sha256"], "files": len(files), "bytes": (VARIANT / "solution.zip").stat().st_size}))


if __name__ == "__main__":
    main()
