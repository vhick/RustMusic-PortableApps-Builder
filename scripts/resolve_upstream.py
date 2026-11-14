#!/usr/bin/env python3
"""Select numbered STABLE RustMusic release, check out its tagged source, record SHA.
Do not use main, prereleases, unverifiable ZIPs, or undocumented mirrors.
"""
import argparse, hashlib, json, os, re, subprocess, sys, urllib.request, urllib.error
from pathlib import Path

REPO='larevuegeek/rustmusic-desktop'
BASE=f'https://api.github.com/repos/{REPO}'
STABLE=re.compile(r'^v?(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?$')

def api(path, missing_ok=False):
    req=urllib.request.Request(BASE+path,headers={
        'Accept':'application/vnd.github+json',
        'User-Agent':'RustMusicPortable-Builder/1',
        'X-GitHub-Api-Version':'2022-11-28',
        **({'Authorization':'Bearer '+os.environ['GITHUB_TOKEN']} if os.getenv('GITHUB_TOKEN') else {})})
    try:
        with urllib.request.urlopen(req,timeout=45) as f: return json.load(f)
    except urllib.error.HTTPError as e:
        if e.code==404 and missing_ok: return None
        raise RuntimeError(f'GitHub API {path} failed (HTTP {e.code}); refusing unverified fallback') from e

def git(*args):
    r=subprocess.run(['git',*args],encoding='utf-8',capture_output=True)
    if r.returncode: raise RuntimeError(f'git {args} failed: {r.stderr}')
    return r.stdout.strip()

def main():
    p=argparse.ArgumentParser(); p.add_argument('--version',default='latest'); p.add_argument('--source',required=True);
    p.add_argument('--revision',default='b1r1'); p.add_argument('--evidence',required=True); a=p.parse_args()
    chosen=None
    if a.version=='latest':
        choices=[]
        for page in range(1,6):
            entries=api(f'/releases?per_page=100&page={page}')
            if not isinstance(entries,list): raise ValueError('Expected GitHub releases array')
            for item in entries:
                tag=item.get('tag_name',''); match=STABLE.fullmatch(tag)
                if match and not item.get('draft') and not item.get('prerelease'):
                    choices.append((tuple(int(g or 0) for g in match.groups()),tag))
            if len(entries)<100: break
        if not choices: raise RuntimeError('No published stable RustMusic releases, refuse main fallback')
        _,chosen=max(choices)
    else:
        if not STABLE.fullmatch(a.version): raise ValueError('Explicit version must be numeric stable (e.g. v0.4.4)')
        chosen=a.version if a.version.startswith('v') else 'v'+a.version
        released=api('/releases/tags/'+chosen,missing_ok=True)
        if released is not None and (released.get('draft') or released.get('prerelease')):
            raise RuntimeError('Requested release is not stable')
        if released is None:
            # Unpublished stable tag is accepted only when GitHub confirms that ref.
            if api('/git/ref/tags/'+chosen,missing_ok=True) is None:
                raise RuntimeError('Requested stable version has neither a release nor a tag')
    directory=Path(a.source).resolve()
    if directory.exists(): raise RuntimeError('Source destination already exists: '+str(directory))
    git('clone','--quiet','--filter=blob:none','--no-checkout','--depth=1',f'https://github.com/{REPO}.git',str(directory))
    git('-C',str(directory),'fetch','--quiet','--depth=1','origin',f'refs/tags/{chosen}:refs/tags/{chosen}')
    commit=git('-C',str(directory),'rev-parse',f'{chosen}^{{commit}}')
    assert re.fullmatch(r'[0-9a-f]{40}',commit)
    git('-C',str(directory),'checkout','--quiet','--detach',commit)
    assert git('-C',str(directory),'rev-parse','HEAD')==commit
    # Use the version from actual tagged source, never README/main/version guess.
    version=chosen.lstrip('v')
    for f,expected in [('package.json',version),('src-tauri/tauri.conf.json',version)]:
        data=json.loads((directory/f).read_text(encoding='utf-8'))
        if data['version'] != expected: raise RuntimeError(f'Tag/version mismatch in {f}: {data["version"]} != {expected}')
    locks={}
    for f in ['package-lock.json','src-tauri/Cargo.lock']:
        path=directory/f
        if not path.exists(): raise RuntimeError(f'Locked dependencies unavailable: {f}')
        locks[f]=hashlib.sha256(path.read_bytes()).hexdigest()
    revision=a.revision
    if not re.fullmatch(r'[A-Za-z0-9._-]+',revision): raise ValueError('Invalid revision')
    release_tag=f'portable-rustmusic-v{version}-g{commit[:8]}-{revision}'
    exists=None
    # Check same builder-repository tag independently; GITHUB_REPOSITORY must be caller, not upstream.
    own=os.environ.get('GITHUB_REPOSITORY')
    if own:
        owner_req=urllib.request.Request(f'https://api.github.com/repos/{own}/releases/tags/{release_tag}',headers={
           'Accept':'application/vnd.github+json', 'User-Agent':'RustMusicPortable-Builder/1',
           **({'Authorization':'Bearer '+os.environ['GITHUB_TOKEN']} if os.getenv('GITHUB_TOKEN') else {})})
        try:
            with urllib.request.urlopen(owner_req,timeout=35) as r: json.load(r)
            exists=True
        except urllib.error.HTTPError as e:
            if e.code==404: exists=False
            else: raise RuntimeError(f'Cannot test existing builder release (HTTP {e.code})') from e
    data={'upstream_repository':REPO,'version':version,'upstream_tag':chosen,'commit_sha':commit,
          'dependency_lock_sha256':locks,'builder_revision':revision,'builder_commit_sha':os.environ.get('GITHUB_SHA',''), 'package_revision':revision,
          'release_tag':release_tag,'existing_release':bool(exists),'source_kind':'git-tag-from-official-GitHub',
          'source_verified_at_build':'GitHub Actions Git remote + SHA'}
    Path(a.evidence).parent.mkdir(parents=True, exist_ok=True)
    Path(a.evidence).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    out=os.environ.get('GITHUB_OUTPUT')
    if out:
        with open(out,'a',encoding='utf-8') as f:
            for k,v in [('version',version),('tag',chosen),('sha',commit),('release_tag',release_tag),('exists',str(bool(exists)).lower())]:
                f.write(f'{k}={v}\n')
    print(json.dumps(data,indent=2))
if __name__=='__main__':
    try: main()
    except Exception as e: print('RESOLUTION FAILED:',e,file=sys.stderr); sys.exit(1)
