#!/usr/bin/env python3
"""Application-specific source adaptation for larevuegeek/rustmusic-desktop.
Fail closed on changed/unknown source features rather than silently packaging a leaky build.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

IDENTIFIER = 'com.larevuegeek.rustmusic.portable.vhick'
STORAGE_CALLS = {
    'dirs::data_dir()': 'crate::helper::portable_paths::data_dir()',
    'dirs::data_local_dir()': 'crate::helper::portable_paths::data_local_dir()',
    'dirs::config_dir()': 'crate::helper::portable_paths::config_dir()',
    'dirs::cache_dir()': 'crate::helper::portable_paths::cache_dir()',
}
PORTABLE_HELPER = r'''// Portability adapter: source-built RustMusic PortableApps edition.
// The binary always lives at Root/App/RustMusic/RustMusic.exe.
// This does NOT alter HOME, USERPROFILE, or global TEMP for other programs.
use std::path::PathBuf;

pub fn store_dir() -> PathBuf {
    let exe = std::env::current_exe().expect("RustMusic portable: current executable missing");
    let bin_dir = exe.parent().expect("RustMusic portable: binary parent missing");
    assert_eq!(bin_dir.file_name().unwrap().to_string_lossy().to_ascii_lowercase(), "rustmusic",
        "RustMusic portable: misplaced application binary");
    let app_dir = bin_dir.parent().expect("RustMusic portable: App folder missing");
    assert_eq!(app_dir.file_name().unwrap().to_string_lossy().to_ascii_lowercase(), "app",
        "RustMusic portable: misplaced application directory");
    let portable_root = app_dir.parent().expect("RustMusic portable: root missing");
    let result = portable_root.join("Data").join("Store");
    std::fs::create_dir_all(&result).expect("RustMusic portable: cannot create Data/Store");
    result
}
pub fn data_dir() -> Option<PathBuf> { Some(store_dir()) }
pub fn data_local_dir() -> Option<PathBuf> { Some(store_dir().join("Local")) }
pub fn config_dir() -> Option<PathBuf> { Some(store_dir().join("Config")) }
pub fn cache_dir() -> Option<PathBuf> { Some(store_dir().join("Cache")) }
'''
UPDATER = '''// PortableApps build: normal Tauri updater must not overwrite managed package files.
import { updaterState } from "#lib/stores/updater/updater.store";
const message = "This PortableApps edition updates through a new RustMusicPortable ZIP or .paf.exe. Your Data directory is retained.";
export async function checkForUpdate(silent = true): Promise<void> {
  if (!silent) updaterState.set({ kind: "error", message });
}
export async function downloadAndInstall(): Promise<void> {
  updaterState.set({ kind: "error", message });
}
export function dismissUpdate(): void { updaterState.set({ kind: "idle" }); }
export function initUpdaterAutoCheck(_delayMs = 5000): void { /* update via package builder */ }
'''

def replace_exact(p: Path, old: str, new: str, label: str):
    s = p.read_text(encoding='utf-8')
    n = s.count(old)
    if n != 1:
        raise RuntimeError(f'{label}: expected exactly one anchor, found {n}: {p}')
    p.write_text(s.replace(old, new), encoding='utf-8', newline='\n')


def adapt(root: Path, evidence: Path):
    rust = root / 'src-tauri' / 'src'
    conf = root / 'src-tauri' / 'tauri.conf.json'
    package = root / 'package.json'
    assert rust.is_dir() and conf.is_file() and package.is_file(), 'Not a RustMusic source tree'
    cfg = json.loads(conf.read_text(encoding='utf-8'))
    assert cfg['identifier'] == 'com.larevuegeek.rustmusic', 'Unexpected upstream identifier'
    assert cfg['mainBinaryName'].lower() == 'rustmusic', 'Unexpected RustMusic EXE identity'
    assert cfg['version'] == json.loads(package.read_text(encoding='utf-8'))['version'], 'Upstream package versions differ'
    assert cfg['app'].get('appDirectoriesOverride') is None, 'Unreviewed upstream app directory override'
    assert not cfg['app']['windows'][0].get('dataDirectory'), 'Unreviewed per-webview dataDirectory override'
    cfg['identifier'] = IDENTIFIER
    cfg['app']['appDirectoriesOverride'] = '../../Data/Tauri'
    # Keep all functionality except the self-updater's installer invocation.
    # It is replaced with an accurate message in the frontend service below.
    conf.write_text(json.dumps(cfg, indent=2, ensure_ascii=False)+'\n', encoding='utf-8', newline='\n')

    helper_mod = rust / 'helper' / 'mod.rs'
    text = helper_mod.read_text(encoding='utf-8')
    assert 'portable_paths' not in text, 'Portable module already present: source drift'
    helper_mod.write_text(text.rstrip() + '\npub mod portable_paths;\n', encoding='utf-8', newline='\n')
    (rust / 'helper' / 'portable_paths.rs').write_text(PORTABLE_HELPER, encoding='utf-8', newline='\n')

    counts = {key:0 for key in STORAGE_CALLS}
    changed = []
    for path in rust.rglob('*.rs'):
        if path.name == 'portable_paths.rs': continue
        content = path.read_text(encoding='utf-8')
        original = content
        for old, new in STORAGE_CALLS.items():
            n = content.count(old)
            if n:
                counts[old] += n
                content = content.replace(old, new)
        if content != original:
            path.write_text(content, encoding='utf-8', newline='\n')
            changed.append(str(path.relative_to(root)))
    assert counts['dirs::data_dir()'] >= 2, 'Expected at least SQLite and logger data_dir paths; upstream drift'

    # User settings are saved separately under %USERPROFILE%/.rust-music/config.json.
    sm = rust / 'core' / 'settings_manager' / 'settings_manager.rs'
    source = sm.read_text(encoding='utf-8')
    anchor = 'let mut config_path = home_dir;'
    assert source.count(anchor) == 1 and '.rust-music' in source, 'Expected upstream user settings path missing'
    sm.write_text(source.replace(anchor, 'let mut config_path = crate::helper::portable_paths::store_dir();'), encoding='utf-8', newline='\n')
    changed.append(str(sm.relative_to(root)))

    # Remove backend updater registration too; never allow a regular installer to
    # bypass portable ZIP/PAF upgrade and data-preservation handling.
    libfile = rust / 'lib.rs'
    replace_exact(libfile, '.plugin(tauri_plugin_updater::Builder::new().build())',
                  '/* PortableApps edition: normal Tauri updater intentionally unregistered. */',
                  'Tauri updater plugin registration')
    changed.append(str(libfile.relative_to(root)))

    updater = root / 'src' / 'lib' / 'services' / 'updater' / 'updater.service.ts' 
    original = updater.read_text(encoding='utf-8')
    assert 'pendingUpdate.downloadAndInstall(' in original and 'export function initUpdaterAutoCheck(' in original, 'Upstream updater drift: fail closed'
    updater.write_text(UPDATER, encoding='utf-8', newline='\n')
    changed.append(str(updater.relative_to(root)))

    # Verify after writing. Keep HOME/music paths unmodified, do NOT change global process env.
    for path in rust.rglob('*.rs'):
        if path.name == 'portable_paths.rs': continue
        code = path.read_text(encoding='utf-8')
        for call in STORAGE_CALLS:
            if call in code:
                raise AssertionError(f'Unpatched storage call {call} in {path}')
    if 'appDirectoriesOverride' not in conf.read_text(encoding='utf-8'):
        raise AssertionError('Tauri directory override missing')
    evidence.parent.mkdir(parents=True, exist_ok=True)
    payload = {'identifier': IDENTIFIER, 'tauri_override':'../../Data/Tauri', 'storage_replacements':counts,
               'changed_paths': sorted(set(changed)), 'portable_updater':'disabled for package integrity',
               'host_userprofile_settings_redirect':'Data/Store/.rust-music/config.json',
               'adapter_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    evidence.write_text(json.dumps(payload,indent=2)+'\n', encoding='utf-8')
    print(json.dumps(payload, indent=2))

if __name__ == '__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--source',required=True); ap.add_argument('--evidence',required=True)
    a=ap.parse_args(); adapt(Path(a.source),Path(a.evidence))
