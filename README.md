# RustMusic PortableApps Builder Kit — b1r1

**Mode:** PORTABLEAPPS only. **Upstream:** https://github.com/larevuegeek/rustmusic-desktop.
**Build target:** Windows x64 (Windows 10/11). **Upstream v0.4.4 at inspection:** 2026-11-14.
**Delivery status:** Ready-to-run GitHub Actions builder **source kit**, not a precompiled app. Windows compilation and real Windows GUI/installer tests have NOT been performed in the creation environment. This kit MUST be evaluated by a real Windows runner and then on a Windows desktop before declaring it verified portable.

The kit is self-contained in terms of its source adapters, original C++ launcher, resolver, validation scripts, workflows, and documentation. It intentionally downloads official upstream source and locked dependencies at build time; the two requested shared pinned actions are external documented dependencies, not local project dependencies.

## Quick start using GitHub Desktop (no local compiler)

1. Sign in to https://github.com and create a **new repository** called `RustMusic-PortableApps-Builder`. Select **Public** for the most generous GitHub-hosted Actions usage where appropriate; source visibility does not grant permission to redistribute binaries or branding. Do not fork the RustMusic upstream repository.
2. In GitHub Desktop: **File > Clone repository**, select the new empty builder repository, and clone it.
3. Open **Repository > Show in Explorer**. Extract **the contents** of this builder-kit ZIP into that folder. Ensure `.github/workflows/` exists. Do not place an extra `kit` folder around the files.
4. In GitHub Desktop, enter a commit summary such as `Initial RustMusic PortableApps builder b1r1`; click **Commit to main**, then **Push origin**. No manual Git initialization, terminal, or local build is required.
5. Open your builder repository on GitHub, then **Actions > RustMusic PortableApps - Source Build > Run workflow**.
6. Keep `version=latest`; set `publish=true` when you want the verified ZIP and installer published. Click **Run workflow**.
7. Read job logs. Successful **Resolve**, **Apply patches**, **Compile RustMusic**, **Compile launcher**, **Validate ZIP**, **Build installer**, **Validate installer**, and **Publisher** steps each report a separate stage. A green job does *not* prove runtime portability.
8. Open **Releases** in **your builder repository**. The latest release is tagged using the RustMusic version, upstream commit, and builder revision. Download the `RustMusicPortable_*_Win64.zip` (extraction) or `.paf.exe` (installer). The release also offers the complete **modified source ZIP** and automatically published `SHA256SUMS.txt`.
9. For ZIP: extract so the `RustMusicPortable` folder contains `RustMusicPortable.exe`; run that EXE. For PAF: run the installer and choose your PortableApps location; refresh PortableApps Platform menu if needed. The installer is **community PortableApps-style**, not official PortableApps.com certification.
10. Exit RustMusic completely using the **tray > Quitter/Quit** action before replacing or upgrading binaries. **Never delete `Data`**.

## Directory layout after a successful build

```text
RustMusicPortable/
  RustMusicPortable.exe                 genuine compiled native Windows launcher
  App/
    AppInfo/appinfo.ini
    AppInfo/appicon.ico
    AppInfo/appicon_16.png
    AppInfo/appicon_32.png
    RustMusic/RustMusic.exe             actual upstream application built from tagged source
  Data/
    Tauri/                             Tauri WebView2, window/plugin state
    Store/                             SQLite, logs, RustMusic user preferences
  Other/
    Source/                            source identity, GPL license, adapter, evidence
```

The RustMusic application is built from the latest stable GitHub tag, not from unverified `main`. The resolver checks tag/commit and records npm/Cargo lockfile hashes. It fails on unstable release tags or changed upstream patch anchors.

## What the source adaptation actually does

- Uses the new Tauri 2.12 `app.appDirectoriesOverride = "../../Data/Tauri"`, resolved relative to `App/RustMusic/RustMusic.exe`. Tauri app-specific data, window-state, WebView2 and supporting plugins use this portable path.
- Replaces Rust `dirs::data_dir()` (and any other enumerated *app-data* resolver calls) with a source-level adapter that derives `Data/Store` from the **running app EXE**, not current directory, HOME, or the launcher environment.
- Redirects upstream `.rust-music/config.json` from the normal Windows user profile to `Data/Store/.rust-music/config.json`.
- Uses a separate portable Tauri identifier so its single-instance identity and Windows-generated identity do not deliberately overlap an installed RustMusic copy.
- Disables RustMusic's normal Tauri in-app updater (backend registration and frontend install service), because ordinary signed updates are built for the upstream installer and bypass PortableApps Data/upgrade safeguards. Use a new builder release for updates.
- Preserves tray, SMTC media controls, optional DLNA server, notification functionality, and normal launch command forwarding. Windows OS registrations and notifications still require manual inspection.
- Preserves the autostart plugin, but it should not be enabled for a movable USB application: when explicitly enabled in the application's settings, it may write a Windows user login startup entry referencing the current inner EXE. Before moving the folder, disable that option. Do not run cleanup scripts against another installed RustMusic app.

**There is deliberately no broad AppData/registry scavenger.** App-controlled data is redirected *before* startup in source and the verified Tauri 2.12 configuration. If Windows GUI tests reveal another specific attributable host write, fail acceptance and implement a bounded documented fix; do not delete arbitrary files or registry keys.

## Additional workflow: Installer Only

For a successful validated ZIP that needs a new installer without recompiling upstream:

1. Open **Actions > RustMusic PortableApps - Installer Only > Run workflow**.
2. `source_tag`: the exact existing release tag in your builder repo, starting `portable-rustmusic-v...`.
3. `source_asset`: exact filename `RustMusicPortable_<version>_<revision>_Win64.zip`, copied from that release.
4. `output_tag`: a **new** tag beginning `portable-` and different from `source_tag`, e.g. `portable-rustmusic-v0.4.4-installer-b1r1a`.
5. `publish=true` only when ready. The workflow verifies the publisher's `SHA256SUMS.txt`, checks the ZIP's internal binary/source identity, extracts it safely, builds the installer through the pinned action, checks the installer payload, runs dry-run, and then publishes.

If the installer fails, the ZIP remains validated and available; the workflow ends in failure instead of pretending the installer passed.

## Upgrade and rollback, simplified

- Create a **copy** of the whole `RustMusicPortable/Data` folder before upgrading.
- Completely quit from the tray, including background playback/DLNA activity.
- Preferred: use the next builder-generated `.paf.exe` to upgrade the **same** PortableApps folder. Shared Package Builder should replace managed `App`, `Other`, and the launcher while preserving `Data`; do not assume actual installation tests passed until verified locally.
- Alternative manual ZIP upgrade: while closed, keep your existing `Data`, replace `App` and `Other` and the root launcher from the new ZIP. Do not nest two `RustMusicPortable` folders.
- Rolling back application binaries does **not** roll back a newly migrated SQLite database. Restore an old matching Data backup if necessary, preserving any newer copy separately.
- Moving to a new drive letter should work for application state based on its executable path. Music library paths that point to external drives may need to be relinked in RustMusic settings.
- Never import or migrate the existing installed RustMusic user profile automatically. If migration is desired, make a backup and test on a separate copy.

## Important sources and limitations

See `docs/AUDIT.md`, `docs/VALIDATION.md`, `docs/TROUBLESHOOTING.md`, and `docs/SECURITY_AND_LICENSE.md`.

**Honest status:** Linux/static tests for the kit are run separately. Windows application compilation, actual SQLite and WebView2 runtime state, notifications, tray lifecycle, installer execution/upgrade, source ZIP publication, and release publishing are **NOT YET VERIFIED** in the creation session.
