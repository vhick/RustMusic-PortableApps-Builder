# Source licensing, security and distribution

This kit's original launcher, source adapters, workflows and validation scripts are distributed under **GPL-3.0-only** (see `LICENSE`). Upstream RustMusic is GPL-3.0-only and the build must retain the upstream notice and make the corresponding modified source available to recipients. To meet this, the source-build workflow also outputs `RustMusicPortable_<version>_<revision>_ModifiedSource.zip` containing the complete source checkout after applying the portable modifications, excluding downloaded `node_modules` and generated build output. It also copies upstream `LICENSE` and adapter evidence into the package.

Using the RustMusic icon does not grant an unqualified endorsement or PortableApps.com certification. Do not claim the application/installer is officially signed, and follow original developers' branding terms and PortableApps.com branding rules.

Builder pins in this kit (not auto-upgrade suggestions):
- `vhick/Portable-Package-Builder@v1.0.0` community `custom-nsis` engine.
- `vhick/portable-release-publisher@v1.1.1` publisher dry-run then live.
- `actions/checkout@v4` and `actions/setup-node@v4` first-party GitHub actions.

The pinned action.yml contracts were inspected publicly while producing the kit, but immutable Git commit SHA tags have not been independently resolved in the creation environment. Revalidate and pin full commit SHAs in production for stronger supply-chain guarantees. `scripts/check_action_contracts.py` rechecks action.yml field names before a source build; it does **not** prove that a malicious moved tag or a compromised remote is safe. All compilation takes place on GitHub-hosted Windows; never run an untrusted GitHub PR branch with publication permissions.

There is no credential collection, registry enumeration, driver installation, service, elevation, injection, AV disabling, global file redirection, or uncontrolled profile harvesting in the compiled launcher. Tauri, WebView2, Windows toast and System Media Transport Controls may still generate OS-managed or consented Windows entries. Test and attribute these before considering optional bounded ShellGuard behavior.

Reproducibility here means a recorded source SHA, locked dependencies and builder revision. It is **not** a promise of byte-identical Rust/MSVC outputs across changing hosted Windows images or toolchains. Build tools are not themselves binary-pin locked.

Reference: https://www.gnu.org/licenses/gpl-3.0.html
