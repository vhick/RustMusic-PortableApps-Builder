# RustMusic upstream/source audit — 2026-11-14

Evidence labels below mean **SOURCE-INSPECTED** when actual upstream file text was examined and **INFERRED** when behavior is based on framework APIs but not observed under Windows GUI runtime. `NOT YET VERIFIED` means no interactive Windows test has been performed.

## Release and architecture

- Repo: https://github.com/larevuegeek/rustmusic-desktop
- Latest stable release identified: **v0.4.4**, published 2026-11-13; GitHub release short commit `aba0351`. The workflow obtains and records its *full* tag commit during real execution, rather than inventing a full SHA at kit-creation time.
- Source: Svelte 5/TypeScript frontend, Tauri 2/Rust backend. The `src-tauri/Cargo.lock` and `package-lock.json` are expected at the release tag. Rust/Tauri WebView2 Windows stack and the release configuration have been inspected. `npm ci` then `npm run tauri build -- --no-bundle --ci` compiles a real Windows application from source.
- Windows 10/11 x64, WebView2 runtime external dependency. Upstream docs require Rust stable, Node 20+, CMake, C++ Build Tools.
- Upstream GPL-3.0-only license; separate rights for branding must still be respected. Icons in source `src-tauri/icons/*` reused with attribution. No commercial code signing is claimed.
- Normal upstream releases offer Windows installers, NOT a verified standalone PortableApps package. The builder therefore builds the binary from tagged source.

## Findings (selected PORTABLEAPPS mode)

| Finding / Evidence | Location / responsible component | NATIVE remedy (not implemented) | PORTABLEAPPS remedy | Data safety / tradeoff | Test / limitation |
|---|---|---|---|---|---|
| SOURCE-INSPECTED SQLite uses `dirs::data_dir()` | `src-tauri/src/helper/database/sqlite.rs`, `.../com.larevuegeek.rustmusic/rustmusic.db`; RustMusic | Direct EXE native data override required | Replace Rust storage calls with portable `Data/Store` resolver before open | No host DB migration or overwrite | Inspect `Data/Store` DB on a real Windows run; path not runtime-confirmed |
| SOURCE-INSPECTED log initialization uses same user-data resolver | `src-tauri/src/lib.rs`, normal user-data `.../logs/rustmusic.log`; RustMusic | In-process portable logs | Source patch moves logs to `Data/Store/.../logs` | Log retention / rotation retained | Verify logs after startup, failure and restart |
| SOURCE-INSPECTED JSON preferences use `USERPROFILE` fallback | `src-tauri/src/core/settings_manager/settings_manager.rs`; `%USERPROFILE%/.rust-music/config.json` | Direct executable in-process path | Explicitly replace local `config_path` base with portable Store | Existing Windows config untouched | Verify selected audio volume/device persists in `Data/Store/.rust-music/config.json` |
| SOURCE-INSPECTED Tauri `app.path().app_config_dir()` | `src-tauri/src/core/window_geometry.rs`, window state; Tauri | Direct EXE Tauri path override required | `app.appDirectoriesOverride=../../Data/Tauri` | Existing window state not moved; different portable identifier | Tauri 2.12 documentation supports override; runtime observation outstanding |
| INFERRED Windows WebView2 cache and web storage | WebView2/Tauri WebView child, path resolved by Tauri | Native Tauri config | Same Tauri override before webview creation | No global APPDATA / TEMP overwrite | Inspect with Process Monitor; do not claim zero OS caches |
| SOURCE-INSPECTED `tauri_plugin_single_instance` | `src-tauri/src/lib.rs` | Separate native identity if needed | Distinct Tauri portable identifier; launcher forwards CLI | Avoids deliberate identifier reuse with installed RustMusic | Test installed-app coexistence and /play, --next, second instance |
| SOURCE-INSPECTED tray + quit menu, SMTC/media control, DLNA startup | `src-tauri/src/lib.rs`, backend services; RustMusic / OS | Keep underlying services | Keep full source functionality and wait for primary process termination | No blind killing of playing app | Windows tray close/quit and media controls are NOT YET VERIFIED |
| SOURCE-INSPECTED optional autostart plugin | `src-tauri/src/lib.rs` and JS plugin dependencies; Tauri | Opt-in owned startup mechanism | Leave user option opt-in; do not enable by default, warn relocation | Startup entry may point to moved inner EXE; do not remove unrelated Run entries | Test explicit enable/disable and relocation; no automatic registry cleanup |
| SOURCE-INSPECTED signed updater for normal installer | `src/lib/services/updater/updater.service.ts`, `src-tauri/src/lib.rs`; upstream updater | Native updater integration would need direct source control | Replace JS updater service with safe manual package-update message; unregister backend plugin | Protects managed binaries and `Data`, but loses in-app installation | Confirm no updater installation prompt, update via PAF/ZIP |
| INFERRED notification AUMID/Windows shell artifacts | `tauri_plugin_notification`, Tauri/OS | Document OS-managed activity | Different portable app identifier; no ungrounded registry deletion | Native notifications kept; shell caches may survive | Test toast and click-to-open with installed RustMusic; runtime attribution needed before ShellGuard |
| SOURCE-INSPECTED playlists use relative media path exports in 0.4.4 | v0.4.4 release notes; RustMusic | No source change | No change to playlist user exports | Music folders outside Data remain user-owned | Test `.m3u8`, drive relocation separately |

## Why TraceGuard/ShellGuard are not blindly installed

- Tauri 2.12 explicitly added `appDirectoriesOverride` for all `app_*_dir` APIs and default Windows WebView2 app storage. This is a supported **pre-start redirection**, so post-exit harvesting would be less safe.
- Additional `dirs`-based and HOME-based code found above is patched at the source level.
- Native Windows notifications/SMTC can leave OS-managed caches, user-owned registration, or permission state that are NOT proven to be exclusive app-owned. Deleting those blindly would risk installed applications. A future ShellGuard must be based on Windows before/after registry/shortcut evidence and exact owner checks.
- Global `%TEMP%`, `%APPDATA%`, `%LOCALAPPDATA%`, `%USERPROFILE%`, Documents, Desktop, Downloads and music directories remain untouched by the launcher.
- The developer allows playlists and file tags to be written wherever the user chooses; these are **intentional user-file modifications**, not traces to relocate into Data. Never move external music into the portable folder automatically.

## Verified references

- Upstream tag: https://github.com/larevuegeek/rustmusic-desktop/releases/tag/v0.4.4
- SQLite: https://raw.githubusercontent.com/larevuegeek/rustmusic-desktop/v0.4.4/src-tauri/src/helper/database/sqlite.rs
- Main Rust library: https://raw.githubusercontent.com/larevuegeek/rustmusic-desktop/v0.4.4/src-tauri/src/lib.rs
- JSON preferences: https://raw.githubusercontent.com/larevuegeek/rustmusic-desktop/v0.4.4/src-tauri/src/core/settings_manager/settings_manager.rs
- Windows Tauri configuration: https://raw.githubusercontent.com/larevuegeek/rustmusic-desktop/v0.4.4/src-tauri/tauri.conf.json
- Tauri 2.12 override feature: https://v2.tauri.app/release/tauri/v2.12.0/
- Tauri config reference: https://v2.tauri.app/reference/config/#appdirectoriesoverride
- Shared Package Builder: https://raw.githubusercontent.com/vhick/Portable-Package-Builder/v1.0.0/action.yml
- Shared Publisher: https://raw.githubusercontent.com/vhick/portable-release-publisher/v1.1.1/action.yml
