#!/usr/bin/env python3
"""Stage source-built x64 RustMusic as PortableApps, validate, zip, and archive GPL source."""
import argparse, configparser, hashlib, json, os, shutil, struct, zipfile
from pathlib import Path

ROOT='RustMusicPortable'
APP='RustMusic.exe'

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def check_pe(p, arch=0x8664):
    data=p.read_bytes()
    assert len(data)>512 and data[:2]==b'MZ',f'Invalid PE: {p}'
    e=struct.unpack_from('<I',data,0x3c)[0]
    assert e+24<len(data) and data[e:e+4]==b'PE\0\0',f'Missing PE signature: {p}'
    assert struct.unpack_from('<H',data,e+4)[0]==arch,f'Not x64: {p}'

def zadd(z, src, name):
    # Zip supports empty directories independently of file content.
    if src.is_symlink(): raise RuntimeError(f'Symlinks/junctions not permitted in portable ZIP: {src}')
    if src.is_dir():
        z.writestr(name.rstrip('/')+'/',b'')
        for child in sorted(src.iterdir(), key=lambda p:p.name.lower()):
            zadd(z,child,name.rstrip('/')+'/'+child.name)
    elif src.is_file():
        z.write(src,name,compress_type=zipfile.ZIP_DEFLATED,compresslevel=6)
    else: raise RuntimeError(f'Symlinks or missing entries not allowed in package: {src}')

def mkicon(source, dest, size):
    # Use Windows' built-in System.Drawing; no counterfeit/recreated artwork.
    import subprocess
    ps=r'''Add-Type -AssemblyName System.Drawing
$im=[System.Drawing.Image]::FromFile($args[0])
try {
 $out=[System.Drawing.Bitmap]::new([int]$args[2],[int]$args[2]);
 $g=[System.Drawing.Graphics]::FromImage($out)
 try { $g.InterpolationMode='HighQualityBicubic';$g.DrawImage($im,0,0,[int]$args[2],[int]$args[2]);$out.Save($args[1],[System.Drawing.Imaging.ImageFormat]::Png) }
 finally { $g.Dispose();$out.Dispose() }
} finally {$im.Dispose()}'''
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        script=Path(d)/'scale_icon.ps1'
        script.write_text(ps,encoding='utf-8')
        result=subprocess.run(['pwsh','-NoProfile','-File',str(script),str(source),str(dest),str(size)],capture_output=True,text=True)
    if result.returncode or not dest.exists():
        raise RuntimeError('Windows PNG resizing failed: '+result.stderr)

def png_dimensions(path):
    b=path.read_bytes()[:24]
    assert b[:8]==b'\x89PNG\r\n\x1a\n', f'Not PNG: {path}'
    return struct.unpack('>II',b[16:24])

def make(root, executable, launcher, source, identity, evidence, dist):
    if root.exists(): raise RuntimeError('Refusing to overwrite existing staging root')
    appdir=root/'App'/'RustMusic'; info=root/'App'/'AppInfo'; others=root/'Other'/'Source' 
    appdir.mkdir(parents=True);info.mkdir(parents=True);others.mkdir(parents=True)
    (root/'Data'/'Store').mkdir(parents=True)
    (root/'Data'/'Tauri').mkdir(parents=True)
    check_pe(executable); check_pe(launcher)
    shutil.copy2(executable,appdir/APP)
    shutil.copy2(launcher,root/'RustMusicPortable.exe')
    cfg=json.loads((source/'src-tauri'/'tauri.conf.json').read_text(encoding='utf-8'))
    assert cfg['app']['appDirectoriesOverride']=='../../Data/Tauri'
    assert cfg['identifier']=='com.larevuegeek.rustmusic.portable.vhick'
    version=identity['version']; revision=identity['package_revision']
    assert cfg['version']==version
    ini=f'''[Format]
Type=PortableApps.comFormat
Version=3.8

[Details]
Name=RustMusic Portable
AppID=RustMusicPortable
Publisher=LaRevueGeeK (PortableApps community build)
Homepage=https://github.com/larevuegeek/rustmusic-desktop
Category=Music & Video
Description=RustMusic music player, source-built portable edition
Language=Multilingual

[License]
Shareable=true
OpenSource=true
Freeware=true
CommercialUse=true
EULAVersion=1

[Version]
PackageVersion={version}.0
DisplayVersion={version} ({revision})

[Control]
Icons=1
Start=RustMusicPortable.exe
'''
    (info/'appinfo.ini').write_text(ini,encoding='utf-8')
    icons=source/'src-tauri'/'icons'
    ico=icons/'icon.ico'; assert ico.is_file(), 'Official upstream ICO missing'
    shutil.copy2(ico,info/'appicon.ico')
    png=icons/'32x32.png'
    assert png.is_file(), 'Official upstream 32x32.png missing'
    assert png_dimensions(png)==(32,32), 'Upstream icon dimensions changed'
    shutil.copy2(png,info/'appicon_32.png')
    small=icons/'16x16.png'
    if small.is_file() and png_dimensions(small)==(16,16):
        shutil.copy2(small,info/'appicon_16.png')
    else: mkicon(png,info/'appicon_16.png',16)
    assert png_dimensions(info/'appicon_16.png')==(16,16)
    assert (source/'LICENSE').is_file()
    shutil.copy2(source/'LICENSE',others/'LICENSE-RustMusic-GPL-3.0.txt')
    for name in ('README.md','CHANGELOG.md'):
        f=source/name
        if f.is_file():shutil.copy2(f,others/name)
    shutil.copy2(evidence,others/'PORTABLE-ADAPTER-EVIDENCE.json')
    actions_report=Path('work/action-contracts.json')
    assert actions_report.is_file(), 'Pinned action commit/interface evidence missing'
    shutil.copy2(actions_report,others/'SHARED-ACTIONS-EVIDENCE.json')
    builder_adapter=Path(__file__).with_name('portable_adapter.py')
    shutil.copy2(builder_adapter,others/'portable_adapter.py')
    identity=dict(identity)
    identity['application_binary_sha256']=sha(appdir/APP)
    identity['portable_launcher_sha256']=sha(root/'RustMusicPortable.exe')
    (others/'BUILD-IDENTITY.json').write_text(json.dumps(identity,indent=2)+'\n',encoding='utf-8')
    (others/'SOURCE-AND-UPGRADE.txt').write_text('''RustMusic is GPL-3.0-only; see LICENSE-RustMusic-GPL-3.0.txt.
Corresponding source is the pinned tag/commit recorded in BUILD-IDENTITY.json,
modified with portable_adapter.py (provided here and in the builder repository).
This release should also provide the complete patched source ZIP as a separate asset.
Executable: App/RustMusic/RustMusic.exe. Tauri 2.12+ stores plugin/WebView
state in Data/Tauri. RustMusic DB/logs/home config: Data/Store.
DO NOT use the ordinary RustMusic in-app updater. Upgrade this package through
its PortableApps-style installer or replace App/ and Other/ after app exits.
NEVER delete Data. Do not overwrite music folders, installed RustMusic, or profiles.
Windows WebView2 Runtime is an external OS dependency.
This is a community PortableApps-style build, not official PortableApps certification.
''',encoding='utf-8')
    dist.mkdir(parents=True,exist_ok=True)
    binary_zip=dist/f'RustMusicPortable_{version}_{revision}_Win64.zip'
    if binary_zip.exists():raise RuntimeError('Output already exists')
    with zipfile.ZipFile(binary_zip,'w',allowZip64=True) as z:
        zadd(z,root,root.name)
    with zipfile.ZipFile(binary_zip,'r') as z:
        assert z.testzip() is None
        files=set(z.namelist())
        assert f'{ROOT}/Data/Store/' in files and f'{ROOT}/Data/Tauri/' in files
    source_zip=dist/f'RustMusicPortable_{version}_{revision}_ModifiedSource.zip'
    IGNORE_DIRS={'.git','node_modules','target','build','dist','.svelte-kit','.turbo','coverage'}
    with zipfile.ZipFile(source_zip,'w',allowZip64=True) as z:
        for p in sorted(source.rglob('*')):
            rel=p.relative_to(source)
            if any(part in IGNORE_DIRS for part in rel.parts):continue
            if p.is_symlink():raise RuntimeError('Source symlink requires review: '+str(p))
            if p.is_file():z.write(p,'rustmusic-modified-source/'+rel.as_posix(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=6)
    with zipfile.ZipFile(source_zip,'r') as z: assert z.testzip() is None
    print(json.dumps({'portable_zip':str(binary_zip),'sha256':sha(binary_zip),
                      'modified_source_zip':str(source_zip),'source_sha256':sha(source_zip)},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ['root','executable','launcher','source','identity','evidence','dist']:p.add_argument('--'+k,required=True)
    a=p.parse_args()
    make(Path(a.root),Path(a.executable),Path(a.launcher),Path(a.source),
         json.loads(Path(a.identity).read_text(encoding='utf-8')),Path(a.evidence),Path(a.dist))
