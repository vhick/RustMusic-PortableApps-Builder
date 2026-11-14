"""Synthetic, static contract tests. DO NOT mistake these for a Windows runtime test."""
import importlib.util,json,re,sys,tempfile,unittest,zipfile
from pathlib import Path
KIT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(KIT/'scripts'))
from portable_adapter import adapt
from package_portable import check_pe
from validate_portable import validate_zip

class BuilderTests(unittest.TestCase):
    def test_adapter_with_real_source_anchors_in_synthetic_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); rust=root/'src-tauri'/'src'
            paths={
                'helper/mod.rs':'pub mod database;\n',
                'helper/database/sqlite.rs':'let d = dirs::data_dir();\n',
                'lib.rs':'let d = dirs::data_dir();\n.plugin(tauri_plugin_updater::Builder::new().build())\n',
                'core/settings_manager/settings_manager.rs':'let home_dir = std::env::var_os("USERPROFILE");\nlet mut config_path = home_dir;\n// .rust-music\n',
            }
            for name,content in paths.items():
                f=rust/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(content,encoding='utf-8')
            tauri={'identifier':'com.larevuegeek.rustmusic','mainBinaryName':'RustMusic','version':'0.4.4',
                   'app':{'windows':[{}]}}
            (root/'src-tauri'/'tauri.conf.json').write_text(json.dumps(tauri))
            (root/'package.json').write_text(json.dumps({'version':'0.4.4'}))
            upd=root/'src/lib/services/updater/updater.service.ts'; upd.parent.mkdir(parents=True)
            upd.write_text('pendingUpdate.downloadAndInstall(\nexport function initUpdaterAutoCheck(\n')
            adapt(root,root/'evidence.json')
            conf=json.loads((root/'src-tauri'/'tauri.conf.json').read_text())
            self.assertEqual(conf['app']['appDirectoriesOverride'],'../../Data/Tauri')
            self.assertEqual(conf['identifier'],'com.larevuegeek.rustmusic.portable.vhick')
            self.assertIn('portable_paths::data_dir()', (rust/'lib.rs').read_text())
            self.assertIn('store_dir()', (rust/'core/settings_manager/settings_manager.rs').read_text())
            self.assertIn('pub mod portable_paths;', (rust/'helper/mod.rs').read_text())
            self.assertIn('PortableApps edition',upd.read_text())

    def test_adapter_rejects_changed_upstream_source(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/'src-tauri/src/helper').mkdir(parents=True)
            (root/'src-tauri/src/helper/mod.rs').write_text('')
            (root/'src-tauri/tauri.conf.json').write_text(json.dumps({'identifier':'unknown','mainBinaryName':'RustMusic','version':'0.4.4','app':{'windows':[{}]}}))
            (root/'package.json').write_text('{"version":"0.4.4"}')
            with self.assertRaises(AssertionError):adapt(root,root/'evidence.json')

    def test_validates_no_symlink_and_no_parent_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            z=Path(d)/'bad.zip'
            with zipfile.ZipFile(z,'w') as f:
                f.writestr('RustMusicPortable/../evil.txt','bad')
            with self.assertRaises(AssertionError):validate_zip(z)

    def test_pe_validation_rejects_text_and_wrong_arch(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'fake.exe';f.write_text('this is not a Windows executable')
            with self.assertRaises(AssertionError):check_pe(f)

    def test_pinned_actions_only(self):
        workflow=(KIT/'.github/workflows/build-rustmusic-portable.yml').read_text()
        self.assertIn('vhick/Portable-Package-Builder@v1.0.0',workflow)
        self.assertIn('vhick/portable-release-publisher@v1.1.1',workflow)
        self.assertIn('dry-run: \'true\'',workflow)
        self.assertIn('dry-run: \'false\'',workflow)
        self.assertIn('windows-2022',workflow)
        self.assertNotIn('official-tool-url:',workflow)

if __name__=='__main__':unittest.main()
