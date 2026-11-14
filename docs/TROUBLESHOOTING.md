# Troubleshooting

**Workflow missing from GitHub Actions**: Confirm `.github/workflows/build-rustmusic-portable.yml` appears in GitHub repository root, not in a nested folder. Commit and push the hidden `.github` directory.

**Failed stable release discovery**: GitHub releases API must return a numeric stable tag; authentication/rate-limit/server errors intentionally cause failure. Set `version=v0.4.4` for a specific verified version. This project never builds an unknown `main` checkout.

**Tag/lockfile mismatch**: The builder requires `package.json`, `tauri.conf.json`, `package-lock.json`, `Cargo.lock` identity for chosen tag. Resolve upstream version conflict rather than editing version numbers to fake a pass. Dependency-lock drift fails the build.

**Tauri / Rust version error**: Upstream versions may change; do not blindly update Tauri dependencies. Read the actual error and inspect updated Tauri config/schema. The adapter requires Tauri 2.12+ for `appDirectoriesOverride`. The source guard is deliberately strict; revise adapter and bump builder revision only after auditing newer upstream.

**Missing linker or MSVC**: Windows-2022 runners require Desktop C++ Build Tools. `compile_launcher.ps1` resolves Visual Studio through vswhere and imports Developer PowerShell. If broken, log the exact Visual Studio or `cl.exe` error. Do not use placeholder EXEs.

**RustMusic.exe not found**: Upstream may change its `mainBinaryName` or output directory. Check the actual Tauri build output and update the packager after verifying the new source; never guess a different executable.

**PNG generation fails**: The build requires official `src-tauri/icons/icon.ico`, `32x32.png`, and either an official 16x16 PNG or resizing via Windows PowerShell/System.Drawing. Keep original developer artwork, not screenshots/stock icons.

**Installer failed but ZIP released**: Intentional safety design. Review the `Shared installer builder` and `validate_installer.ps1` logs. The `.paf.exe` is quarantined when invalid, the workflow ends in failure, and the validated ZIP stays published. Installer-only workflow can retry without rebuilding upstream.

**Windows SmartScreen warning**: The kit does not sign the root launcher or the custom NSIS installer. Verify SHA256SUMS and your builder repository provenance. A warning alone does not prove malware or safety.

**Music plays but changes disappear**: Check write permissions of `Data/Store` and `Data/Tauri`; removable drive can be read-only. Inspect `Data/Store/com.larevuegeek.rustmusic/logs/rustmusic.log`. Existing installed settings are NOT copied automatically.

**Database migration breaks rollback**: Restore a full Data backup saved *before* the upgrade. Never delete or silently rewrite the current DB.

**Windows startup persists after folder moved**: If you manually enabled autostart, disable it before moving the portable folder. Inspect exact user-owned entry; do not blindly delete matching keys for installed RustMusic.

**Tray process remains**: The root launcher waits for RustMusic's primary process. Test actual Windows tray Quit and the media server; never force-close app while a DB transaction is active except in a controlled recovery test.

**WebView2 missing or broken**: Install/repair the official Microsoft WebView2 Runtime on the host Windows computer. It is an allowed OS prerequisite, not bundled here.
