#!/usr/bin/env python3
"""Verify pinned shared Actions by the official GitHub API at workflow runtime.

This records the actual SHA behind each requested release tag, fetches action.yml
by immutable commit SHA, verifies the required contract, and fails closed if the
pinned interface changes. YAML `uses` remains at the user-requested tags; the
recorded SHAs enable a future explicit reviewed switch to immutable uses lines.
"""
import argparse
import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

ACTIONS = {
    'package_builder': {
        'repo': 'vhick/Portable-Package-Builder', 'tag': 'v1.0.0',
        'fields': ('source-dir:', 'output-dir:', 'engine:', 'running-exe:',
                   'timeout-seconds:', 'package-revision:', 'installer-file:',
                   'installer-sha256:', 'app-id:', 'app-version:'),
    },
    'release_publisher': {
        'repo': 'vhick/portable-release-publisher', 'tag': 'v1.1.1',
        'fields': ('files:', 'tag:', 'release-title:', 'tag-prefix:',
                   'keep-releases:', 'prune:', 'dry-run:'),
    }
}

def fetch_json(url):
    headers = {
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'RustMusicPortable-Builder/b1r1',
        'X-GitHub-Api-Version': '2022-11-28',
    }
    if os.getenv('GITHUB_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GITHUB_TOKEN']
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=45) as r:
        return json.load(r)

def fetch_bytes(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={
        'User-Agent': 'RustMusicPortable-Builder/b1r1',
    }), timeout=45) as r:
        return r.read()

def check(output: Path):
    evidence = {}
    for identity, item in ACTIONS.items():
        repo, tag = item['repo'], item['tag']
        result = fetch_json(f'https://api.github.com/repos/{repo}/commits/{tag}')
        sha = result.get('sha', '')
        if not re.fullmatch(r'[0-9a-f]{40}', sha):
            raise RuntimeError(f'{repo}@{tag}: could not resolve a verified full commit SHA')
        data = fetch_bytes(f'https://raw.githubusercontent.com/{repo}/{sha}/action.yml')
        src = data.decode('utf-8-sig')
        for field in item['fields']:
            if field not in src:
                raise RuntimeError(f'{repo}@{tag} ({sha}): pinned action.yml lacks {field}')
        evidence[identity] = {
            'repository': repo, 'tag': tag, 'resolved_commit_sha': sha,
            'action_yml_sha256': hashlib.sha256(data).hexdigest(),
            'fields_confirmed': list(item['fields']),
            'method': 'GitHub official commit endpoint + raw commit-SHA action.yml',
        }
        print(f'VERIFIED PIN INTERFACE: {repo}@{tag} -> {sha}')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out', default='work/action-contracts.json')
    args = p.parse_args()
    check(Path(args.out))
