# Validation stages and actual evidence

Do not report compilation or GUI runtime as tested merely because a synthetic source adapter unit test passes.

| Stage | Kit creation status | What a successful Windows GitHub workflow proves | Further acceptance |
|---|---|---|---|
| Upstream version/tag/commit | SOURCE-INSPECTED; full SHA requires checkout | Exact tagged source commit is recorded and stable release chosen | Confirm tag is the intended trusted developer release |
| GitHub Action interfaces | SOURCE-INSPECTED at v1.0.0/v1.1.1 | Contracts re-fetched and checked at runtime | Inspect exact action implementation changes / immutable SHA pin later |
| Static unit tests | STATIC-VALIDATED (5 synthetic tests) | Source adapter fixture, YAML text, basic invalid-PE and path checks | Repeat on Windows |
| Actual RustMusic x64 compilation | NOT YET VERIFIED | Tauri built a PE with source patches | Open app on Windows and exercise music playback |
| C++ launcher x64 compilation | NOT YET VERIFIED | Real PE compiled with MSVC; binary SHA recorded | Launch from movable folder, CLI forwarding, tray exit |
| SQLite/log/user settings under Data | SOURCE-INSPECTED design, NOT YET VERIFIED on Windows | Embedded patch and config static checks | Use Process Monitor; verify no `installed` DB read/write |
| Tauri/WebView2/window-state persistence | SOURCE-INSPECTED Tauri API; runtime NOT YET VERIFIED | Tauri override embedded in config | Inspect `Data/Tauri`, webview cache, layout/geometry, drive moves |
| TraceGuard empty-dir/registry recovery | NOT IMPLEMENTED (no source-evidenced unavoidable app-owned Windows host folder) | N/A | If real attributable host storage is found, create a bounded design and tests before claiming success |
| ShellGuard + notification registration | NOT IMPLEMENTED (actual attributable shell trace unproven) | Distinct Tauri identity static check only | Test real notifications, activation and installed-app registry coexistence |
| Windows background/tray lifecycle | NOT YET VERIFIED | Root launcher waits on main RustMusic process | Close window to tray, quit tray, DLNA server exit, no leftover app child |
| Default autostart | No automatic OS setup coded | Tauri option remains user-initiated | Enable/disable explicitly and check HKCU entry ownership |
| Portable ZIP validation | NOT YET VERIFIED for application; validator implemented | ZIP root, PE x64, CRC, metadata, empty directory entries, original icons, SHA | Extract to Unicode/spaces/USB path and run |
| Installer compilation + embedded payload | NOT YET VERIFIED | Shared builder creates PE and 7z payload listing inspected | Fresh install, overwrite, upgrade/rollback with Data backups |
| Published release | NOT YET VERIFIED | Shared publisher preflight then live publishes only chosen validated ZIP/source and validated PAF | Confirm download, hash and browser access |

## Real Windows acceptance procedure (not executable headless)

1. On a clean Windows 10/11 x64 test VM with WebView2 installed, create an ordinary **installed** RustMusic profile first, play some tracks, save its preferences. Back up the host profile for testing.
2. Extract a validated RustMusicPortable ZIP to e.g. `C:\Users\Public\Portable Tests\Music ü\RustMusicPortable\`. Do not run an installer's temporary EXE as the app.
3. Open `RustMusicPortable.exe`, import a test music folder (a copy of non-sensitive files), play music, adjust volume/output, create favorites and a playlist, close and re-open. Confirm the SQLite DB, logs, `.rust-music` settings, and window/webview state are under Data and persist.
4. From another command prompt start root launcher with `/play`, `--next`, `--pause`, `/show`; note any double-instance startup conflicts. Keep normal main process open and test all allowed CLI forwarding.
5. Close the window to tray, restore from tray, exit using **Quitter/Quit**. Confirm `RustMusicPortable.exe` process exits after the application, and no RustMusic main processes remain.
6. Inspect in Process Monitor file and registry writes for `RustMusic.exe` and WebView2 children, compare before/after snapshots of `%APPDATA%`, `%LOCALAPPDATA%`, `%USERPROFILE%\.rust-music`, `%PROGRAMDATA%`, Windows Startup/Start Menu/notification keys. Do **not** delete these paths. Distinguish Windows-managed caches, browser runtime, installed copy, user-chosen music writes, and portable application's real data.
7. While normal installed RustMusic is also running, verify profiles remain separate, single-instance behavior, notifications and SMTC controls. Check toast clicking behavior and AUMID collisions.
8. Confirm Windows autostart is **not** created by first run. If testing opt-in, enable it in RustMusic's settings, inspect its exact registration, disable it, verify registration removed, and ensure installed entries are untouched.
9. Re-extract same ZIP into a different drive/root and confirm Data persists; inspect saved library file paths after relocation. Repeat in paths containing spaces and non-ASCII characters.
10. In a test copy only, create completely empty subdirectories in Data, nested trees, and files; perform upgrade with next package; confirm full Data remains. Create a SQLite backup and test failed/rollback upgrade, comparing bytes and hashes.
11. Run PAF installer fresh to a test directory, reinstall same build, install older/newer build, confirm managed obsolete App binaries are replaced, all Data and empty dirs survive, and existing unrelated destination is rejected.
12. Run a controlled abrupt termination of the launched app, restart, validate DB integrity and no host profile corruption. Repeat with normal Windows sign-out. Do not force-kill production profiles for this test.
13. Report each result as MANUAL-WINDOWS-TESTED or FAILED with screenshots, logs, paths and before/after evidence. Do not mark other stages complete by association.

These tests are not claimed to have been run in the kit-creation environment.
