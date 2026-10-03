#!/usr/bin/env python3
"""Extract a CRX2/CRX3/ZIP into a new directory; does not verify CRX signatures."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import struct
import tempfile
import zipfile


def extract(source, output):
    output = output.absolute()
    if output.exists() or output.is_symlink():
        raise ValueError('Output already exists; choose a new directory')
    data = source.read_bytes()
    offset = 0
    if data[:4] == b'Cr24':
        if len(data) < 12:
            raise ValueError('Truncated CRX header')
        version = struct.unpack_from('<I', data, 4)[0]
        if version == 3:
            offset = 12 + struct.unpack_from('<I', data, 8)[0]
        elif version == 2 and len(data) >= 16:
            public_key, signature = struct.unpack_from('<II', data, 8)
            offset = 16 + public_key + signature
        else:
            raise ValueError(f'Unsupported or truncated CRX version {version}')
    if data[offset:offset + 4] != b'PK\x03\x04':
        raise ValueError('Missing ZIP payload')
    with zipfile.ZipFile(io.BytesIO(data[offset:])) as archive:
        names = set()
        total = 0
        for item in archive.infolist():
            path = PurePosixPath(item.filename)
            mode = item.external_attr >> 16
            if (path.is_absolute() or '..' in path.parts or '\\' in item.filename
                    or ':' in item.filename or not path.parts
                    or stat.S_ISLNK(mode)):
                raise ValueError(f'Unsafe archive entry: {item.filename!r}')
            normalized = str(path).casefold()
            if normalized in names:
                raise ValueError(f'Duplicate archive entry: {item.filename!r}')
            names.add(normalized)
            total += item.file_size
        if total > 512 * 1024 * 1024:
            raise ValueError('Unexpected payload over 512 MiB; inspect before extracting')
        bad = archive.testzip()
        if bad:
            raise ValueError(f'ZIP checksum failed: {bad}')
        manifest = json.loads(archive.read('manifest.json'))
        output.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix='.bewlycat-extract-', dir=output.parent))
        try:
            archive.extractall(staging)
            staging.rename(output)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    return {'source': str(source), 'sha256': hashlib.sha256(data).hexdigest(),
            'name': manifest.get('name'), 'version': manifest.get('version'),
            'output': str(output), 'signature_verified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(extract(args.input, args.output), ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, zipfile.BadZipFile) as error:
        parser.exit(1, f'Extraction refused: {error}\n')
