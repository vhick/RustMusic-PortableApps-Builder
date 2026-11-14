#!/usr/bin/env python3
"""Source-built PortableApps staging/zip validation; no GUI execution claims."""
import argparse,configparser,hashlib,json,re,struct,sys,zipfile
from pathlib import Path
from package_portable import check_pe,png_dimensions
ROOT='RustMusicPortable'
REQUIRED=['RustMusicPortable.exe','App/RustMusic/RustMusic.exe','App/AppInfo/appinfo.ini',
 'App/AppInfo/appicon.ico','App/AppInfo/appicon_16.png','App/AppInfo/appicon_32.png',
 'Data/Store/','Data/Tauri/','Other/Source/BUILD-IDENTITY.json',
 'Other/Source/PORTABLE-ADAPTER-EVIDENCE.json','Other/Source/SHARED-ACTIONS-EVIDENCE.json',
 'Other/Source/LICENSE-RustMusic-GPL-3.0.txt']

def validate_stage(path):
    assert path.name==ROOT and path.is_dir()
    for name in REQUIRED:
        assert (path/name.rstrip('/')).exists(),f'Missing {name}'
    # Refuse staging that redirects through a junction, symlink or reparse point.
    # Junctions are represented as symlinks by pathlib on supported Windows Python.
    assert not path.is_symlink(), 'Portable root is a symlink'
    for entry in path.rglob('*'):
        assert not entry.is_symlink(), f'Unexpected symlink/junction {entry}' 
    for name in ('RustMusicPortable.exe','App/RustMusic/RustMusic.exe'):
        check_pe(path/name)
    for size in (16,32):
        assert png_dimensions(path/f'App/AppInfo/appicon_{size}.png')==(size,size)
    ini=configparser.ConfigParser(interpolation=None)
    ini.read(path/'App/AppInfo/appinfo.ini',encoding='utf-8')
    assert ini.get('Details','AppID')=='RustMusicPortable'
    assert ini.get('Control','Start')=='RustMusicPortable.exe'
    assert re.fullmatch(r'\d+\.\d+\.\d+\.\d+',ini.get('Version','PackageVersion'))
    identity=json.loads((path/'Other/Source/BUILD-IDENTITY.json').read_text(encoding='utf-8'))
    assert len(identity['commit_sha'])==40
    assert identity['upstream_tag']=='v'+identity['version']
    assert hashlib.sha256((path/'App/RustMusic/RustMusic.exe').read_bytes()).hexdigest()==identity['application_binary_sha256']
    assert hashlib.sha256((path/'RustMusicPortable.exe').read_bytes()).hexdigest()==identity['portable_launcher_sha256']
    assert not (path/'App/RustMusic'/'Data').exists()
    assert not (path/'App/AppInfo'/'Launcher').exists(), 'No unused dummy PortableApps Launcher configuration'
    return identity

def validate_zip(path):
    assert path.is_file() and path.suffix.lower()=='.zip'
    with zipfile.ZipFile(path,'r') as z:
        assert z.testzip() is None,'CRC failure'
        members=z.infolist(); names={x.filename for x in members}
        assert len(names)==len(members),'Duplicate ZIP members'
        assert len({n.replace('\\','/').casefold() for n in names})==len(names),'Case-colliding Windows ZIP members' 
        for rel in REQUIRED:
            assert ROOT+'/'+rel in names,f'ZIP missing {rel}'
        for m in members:
            n=m.filename.replace('\\','/')
            assert n.startswith(ROOT+'/') and not n.startswith('/'),'Wrong ZIP root'
            assert not any(p in ('.','..') for p in n.split('/')),'Zip path traversal'
            assert ((m.external_attr>>16)&0o170000)!=0o120000,'Symlink in ZIP'
        exe=z.read(ROOT+'/RustMusicPortable.exe')
        assert exe[:2]==b'MZ'
        pe=struct.unpack_from('<I',exe,0x3c)[0]
        assert exe[pe:pe+4]==b'PE\0\0' and struct.unpack_from('<H',exe,pe+4)[0]==0x8664
        ini=z.read(ROOT+'/App/AppInfo/appinfo.ini').decode('utf-8')
        assert 'Start=RustMusicPortable.exe' in ini and 'AppID=RustMusicPortable' in ini
        evidence=json.loads(z.read(ROOT+'/Other/Source/BUILD-IDENTITY.json'))
        assert evidence['source_kind']=='git-tag-from-official-GitHub'
        assert evidence['application_binary_sha256']==hashlib.sha256(z.read(ROOT+'/App/RustMusic/RustMusic.exe')).hexdigest()
        return evidence

def safe_extract(path,destination):
    with zipfile.ZipFile(path) as z:
        validate_zip(path)
        target=destination.resolve()
        for i in z.infolist():
            dest=(target/i.filename).resolve()
            assert dest==target or target in dest.parents, 'Unsafe ZIP path'
            z.extract(i,target)
    validate_stage(target/ROOT)

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--stage'); ap.add_argument('--zip'); ap.add_argument('--extract')
    a=ap.parse_args()
    if not a.stage and not a.zip: ap.error('Specify --stage or --zip')
    if a.stage:print('STAGING STATIC VALID:',validate_stage(Path(a.stage)))
    if a.zip:
        print('ZIP STATIC VALID:',validate_zip(Path(a.zip)))
        if a.extract:safe_extract(Path(a.zip),Path(a.extract))
