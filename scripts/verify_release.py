#!/usr/bin/env python3
"""Verify exact already-published ZIP + publisher checksum file before installer-only packaging."""
import argparse,hashlib,re,sys
from pathlib import Path
from validate_portable import validate_zip

def verify(folder,asset):
    if not re.fullmatch(r'RustMusicPortable_[0-9]+\.[0-9]+\.[0-9]+_[A-Za-z0-9._-]+_Win64\.zip',asset):
        raise RuntimeError('Not a RustMusic PortableApps ZIP asset')
    file=folder/asset;ums=folder/'SHA256SUMS.txt'
    if not file.is_file() or not ums.is_file():raise FileNotFoundError('Missing ZIP or checksum manifest')
    lines=ums.read_text(encoding='utf-8-sig').splitlines()
    matched=[]
    for line in lines:
        m=re.fullmatch(r'([0-9a-fA-F]{64})\s+\*?(.+)',line.strip())
        if m and m.group(2)==asset:matched.append(m.group(1).lower())
    if len(matched)!=1:raise RuntimeError('Expected exactly one checksum for '+asset)
    sha=hashlib.sha256(file.read_bytes()).hexdigest()
    if sha!=matched[0]:raise RuntimeError(f'SHA256 mismatch {asset}')
    data=validate_zip(file)
    name_ver=re.search(r'^RustMusicPortable_([\d.]+)_',asset).group(1)
    if name_ver!=data['version']:raise RuntimeError('ZIP name / source version mismatch')
    print('TRUSTED RELEASE ASSET:',asset,sha,data['release_tag'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--folder',required=True);p.add_argument('--asset',required=True)
    a=p.parse_args()
    try:verify(Path(a.folder),a.asset)
    except Exception as e:print(e,file=sys.stderr);sys.exit(1)
