#!/usr/bin/env python3
"""Apply current Safari fixes and optional sender hiding to the exact 1.8.0 baseline."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile

HASHES = {
    'manifest.json': '96af435d2aafcae40cbc6419f36463cd1b1846ba1cccc6ef132d040ef7334f62',
    'dist/background/index.js': '420a3e1e2191fb818a0b25af6570babd2767f4ab696bee42f92699bf64dc0fc4',
    'dist/contentScripts/index.global.js': 'f8b4c0c27453041206be96e3ee78d7d3086e6ce087a274314ece7165c1ba2d22',
    'dist/contentScripts/style.css': '7108719ac4cf4bfd362826b5e99fa8a44b11826fc6cd11e5a7fb2c6f71781fa9',
}
ASSETS = Path(__file__).resolve().parents[1] / 'assets'


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f'Expected one structural match: {old}')
    return text.replace(old, new, 1)


def patch(source, output, version, hide_widescreen_sender=False):
    source, output = source.resolve(), output.absolute()
    if output.exists() or output.is_symlink():
        raise ValueError('Output already exists; refusing to overwrite')
    if output.resolve().is_relative_to(source):
        raise ValueError('Output must not be inside immutable source')
    if not re.fullmatch(r'1\.8\.0\.[1-9][0-9]*', version) or int(version.split('.')[-1]) > 65535:
        raise ValueError('This baseline requires a local version 1.8.0.N, N=1..65535')
    if any(p.is_symlink() for p in source.rglob('*')):
        raise ValueError('Source contains symlinks; inspect before patching')
    texts = {}
    for name, digest in HASHES.items():
        data = (source / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError(f'Unknown or already patched baseline: {name}. '
                             'No changes made. Read references/compatibility.md and adapt semantically.')
        texts[name] = data.decode('utf-8')
    manifest = json.loads(texts['manifest.json'])
    if manifest['version'] != '1.8.0':
        raise ValueError('Unexpected upstream version')
    background = texts['dist/background/index.js']
    background = once(background,
        'cookies.onChanged.addListener(({cookie})=>{let normalizedDomain=',
        'cookies.onChanged.addListener((changeInfo)=>{const cookie=changeInfo?.cookie;if(!cookie){scheduleBroadcastLoginStateChanged();return}let normalizedDomain=')
    signature = 'async function doCachedRequest(message,api,tab,cookies,signal){'
    background = once(background, signature, signature + 'api={...api,_safariTabId:tab?.id};')
    background = once(background, 'fetch(requestUrl,fetchOpt)',
                      'bewlySafariFetch(requestUrl,fetchOpt,api._safariTabId)')
    texts['dist/background/index.js'] = background.rstrip() + '\n\n' + (ASSETS / 'safari-background-helper.js').read_text()
    texts['dist/contentScripts/index.global.js'] = once(
        texts['dist/contentScripts/index.global.js'], 'const mr="1.8.0";', f'const mr="{version}";')
    css = once(texts['dist/contentScripts/style.css'], ':host,:root{', ':root{')
    texts['dist/contentScripts/style.css'] = css.rstrip() + '''

/* Safari: comment cards follow their current container in both themes.
   Widescreen drawer tokens are inherited only while inside that drawer. */
:host(bili-comment-renderer),
:host(bili-comment-renderer) #body {
  background-color: var(--bewly-widescreen-sidebar-bg, var(--bew-bg)) !important;
}
'''
    if hide_widescreen_sender:
        texts['dist/contentScripts/style.css'] += '''
/* Bewly widescreen: hide the sender dock; its ResizeObserver reclaims the
   measured height for the player and keeps the existing drawer layout intact. */
#bewly-widescreen-root .bewly-widescreen-danmaku-dock {
  display: none !important;
}
'''
    manifest['version'] = version
    if manifest['content_scripts'][0].get('world', 'ISOLATED') != 'ISOLATED':
        raise ValueError('Unexpected content-script world')
    manifest['content_scripts'][0]['js'].insert(0, './dist/contentScripts/safari-fetch.js')
    texts['manifest.json'] = json.dumps(manifest, ensure_ascii=False, indent=2) + '\n'
    texts['dist/contentScripts/safari-fetch.js'] = (ASSETS / 'safari-fetch.js').read_text()
    if (source / 'dist/contentScripts/safari-fetch.js').exists():
        raise ValueError('Adapter already exists')
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.bewlycat-patch-', dir=output.parent))
    try:
        shutil.copytree(source, staging, dirs_exist_ok=True)
        for name, value in texts.items():
            (staging / name).write_text(value)
        staging.rename(output)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return {'upstream_version': '1.8.0', 'local_version': version,
            'hide_widescreen_sender': hide_widescreen_sender,
            'output': str(output), 'modified': list(HASHES),
            'added': ['dist/contentScripts/safari-fetch.js']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--version', required=True)
    parser.add_argument('--hide-widescreen-sender', action='store_true',
                        help='Preserve the requested custom widescreen layout without its sender dock')
    args = parser.parse_args()
    try:
        print(json.dumps(patch(args.source, args.output, args.version,
                               args.hide_widescreen_sender), indent=2))
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f'Patch refused: {error}\n')
