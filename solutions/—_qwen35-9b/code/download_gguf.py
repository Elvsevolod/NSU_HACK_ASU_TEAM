"""HTTP range fallback for a stalled Hub download; verifies the Hub LFS digest."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import urllib.request
from huggingface_hub import HfApi, hf_hub_url


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--directory', type=Path, required=True)
    ap.add_argument('--manifest', type=Path, default=Path(__file__).resolve().parents[1] / 'models-manifest.json')
    args = ap.parse_args()
    spec = json.loads(args.manifest.read_text())['parser']
    repo, filename = spec['repo'], Path(spec['path']).name
    info = HfApi().model_info(repo, revision=spec['revision'], files_metadata=True)
    item = next(f for f in info.siblings if f.rfilename == filename)
    expected, size = spec['sha256'][filename], item.size
    if item.lfs.sha256 != expected:
        raise ValueError('Pinned manifest and Hub LFS metadata disagree')
    url = hf_hub_url(repo, filename, revision=info.sha)
    parts = args.directory / '.http-parts'
    parts.mkdir(parents=True, exist_ok=True)
    block = 16 * 1024 * 1024

    def fetch(start):
        end = min(size, start + block) - 1
        target = parts / str(start)
        if target.exists() and target.stat().st_size == end - start + 1:
            return target
        request = urllib.request.Request(url, headers={'Range': f'bytes={start}-{end}'})
        with urllib.request.urlopen(request, timeout=90) as response:
            if response.status != 206 or response.headers.get('Content-Range') != f'bytes {start}-{end}/{size}':
                raise ValueError('Server did not honor the requested byte range')
            with target.open('wb') as stream:
                while data := response.read(1024 * 1024):
                    stream.write(data)
        if target.stat().st_size != end - start + 1:
            raise ValueError('Incomplete weight chunk')
        print('Downloaded', end + 1, '/', size, flush=True)
        return target

    with ThreadPoolExecutor(max_workers=8) as pool:
        ordered = list(pool.map(fetch, range(0, size, block)))
    output = args.directory / filename
    digest = hashlib.sha256()
    with output.open('wb') as stream:
        for path in ordered:
            with path.open('rb') as part:
                while data := part.read(1024 * 1024):
                    digest.update(data)
                    stream.write(data)
    if digest.hexdigest() != expected:
        raise ValueError('GGUF checksum differs from the pinned Hub LFS object')
    for path in ordered:
        path.unlink()
    parts.rmdir()
    print('Verified', output, expected, flush=True)


if __name__ == '__main__':
    main()
