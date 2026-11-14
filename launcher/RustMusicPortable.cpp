// RustMusic PortableApps launcher - original source, x64 Windows PE.
// We do not edit system APPDATA/LOCALAPPDATA/TEMP. Tauri appDirectoriesOverride
// and the audited Rust source adapter route application state into Data/.
#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#include <windows.h>
#include <shellapi.h>
#include <string>
#include <filesystem>
#include <vector>
#include <cwctype>

static std::wstring quote(const std::wstring& arg) {
  std::wstring out = L"\""; unsigned slashes=0;
  for (wchar_t c: arg) {
    if (c == L'\\') { ++slashes; continue; }
    if (c == L'"') { out.append(slashes*2+1,L'\\'); out.push_back(L'"'); slashes=0; continue; }
    out.append(slashes,L'\\'); slashes=0; out.push_back(c);
  }
  out.append(slashes*2,L'\\'); out.push_back(L'"'); return out;
}
static std::filesystem::path self_path() {
  std::vector<wchar_t> b(32768);
  DWORD n=GetModuleFileNameW(nullptr,b.data(),(DWORD)b.size());
  if (n==0 || n>=b.size()) return {};
  return std::filesystem::path(std::wstring(b.data(),n));
}
static bool has_reparse_point(const std::filesystem::path& p) {
  const DWORD attrs = GetFileAttributesW(p.c_str());
  return attrs != INVALID_FILE_ATTRIBUTES && (attrs & FILE_ATTRIBUTE_REPARSE_POINT) != 0;
}
static bool has_file(const std::filesystem::path& p) {
  std::error_code ec; return std::filesystem::is_regular_file(p,ec);
}
int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int) {
  try {
    auto exe=self_path();
    if (exe.empty()) { MessageBoxW(nullptr,L"Cannot resolve portable executable path.",L"RustMusic Portable",MB_ICONERROR);return 3; }
    auto root=exe.parent_path(), inner=root/L"App"/L"RustMusic"/L"RustMusic.exe";
    if (!has_file(inner)) {MessageBoxW(nullptr,L"App\\RustMusic\\RustMusic.exe is missing. Reinstall without deleting Data.",L"RustMusic Portable",MB_ICONERROR);return 3;}
    auto data=root/L"Data", store=data/L"Store", tauri=data/L"Tauri";
    // Refuse to follow attacker-controlled junctions/reparse points into host folders.
    for (const auto& component : {root/L"App", root/L"App"/L"RustMusic", data, store, tauri}) {
      if (has_reparse_point(component)) {
        MessageBoxW(nullptr,L"A portable App/Data folder is a Windows junction or symbolic link. Refusing to write through it.",L"RustMusic Portable",MB_ICONERROR);
        return 8;
      }
    }
    std::error_code ec;
    std::filesystem::create_directories(store,ec);
    if (ec) {MessageBoxW(nullptr,L"Cannot create Data\\Store. Check USB permissions.",L"RustMusic Portable",MB_ICONERROR);return 4;}
    std::filesystem::create_directories(tauri,ec);
    if (ec) {MessageBoxW(nullptr,L"Cannot create Data\\Tauri. Check USB permissions.",L"RustMusic Portable",MB_ICONERROR);return 4;}
    int argc=0; LPWSTR* argv=CommandLineToArgvW(GetCommandLineW(),&argc);
    if (!argv) return 5;
    std::wstring command=quote(inner.wstring());
    for (int i=1;i<argc;i++) {command+=L" ";command+=quote(argv[i]);}
    LocalFree(argv);
    std::vector<wchar_t> buffer(command.begin(),command.end()); buffer.push_back(L'\0');
    STARTUPINFOW si{}; si.cb=sizeof(si); PROCESS_INFORMATION pi{};
    std::wstring working=inner.parent_path().wstring();
    BOOL ok=CreateProcessW(inner.c_str(),buffer.data(),nullptr,nullptr,FALSE,0,nullptr,working.c_str(),&si,&pi);
    if (!ok) {MessageBoxW(nullptr,L"RustMusic could not start. Ensure Windows WebView2 is available.",L"RustMusic Portable",MB_ICONERROR);return 6;}
    CloseHandle(pi.hThread);
    // Keep launcher attached until the music player fully exits (including tray mode).
    DWORD w=WaitForSingleObject(pi.hProcess,INFINITE);
    DWORD code=1;
    if (w==WAIT_OBJECT_0) GetExitCodeProcess(pi.hProcess,&code);
    CloseHandle(pi.hProcess);
    return static_cast<int>(code);
  } catch (...) {
    MessageBoxW(nullptr,L"Portable launcher path error.",L"RustMusic Portable",MB_ICONERROR);
    return 7;
  }
}
