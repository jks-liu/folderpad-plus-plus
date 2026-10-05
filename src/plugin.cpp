#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <windowsx.h>
#include <commctrl.h>
#include <shobjidl.h>
#include <filesystem>
#include <string>
#include <vector>
#include <algorithm>
#include "PluginInterface.h"
#include "Docking.h"
#include "dockingResource.h"
#include "model.h"
#include "version.h"

namespace {
HINSTANCE module;
NppData host;
FuncItem commands[4];
HWND panel, tabs, files, addButton, removeButton, pathLabel, emptyLabel;
HFONT font;
std::wstring config;
std::vector<std::wstring> folders;
struct Document { UINT_PTR id; std::wstring path; int group; };
std::vector<Document> documents;
std::vector<UINT_PTR> rows;
int language = 0; // 0: host, 1: English, 2: Chinese
bool chinese = false, visible = true, ready = false, rebuilding = false, followPending = false;
constexpr UINT_PTR refreshTimer = 1;
const wchar_t* tr(const wchar_t* en, const wchar_t* zh) { return chinese ? zh : en; }
LRESULT npp(UINT msg, WPARAM w = 0, LPARAM l = 0) { return SendMessageW(host._nppHandle, msg, w, l); }
void error(const wchar_t* en, const wchar_t* zh) { MessageBoxW(panel ? panel : host._nppHandle, tr(en, zh), L"folderpad++", MB_OK | MB_ICONERROR); }

void detectLanguage() {
    char native[256]{};
    npp(NPPM_GETNATIVELANGFILENAME, sizeof(native), reinterpret_cast<LPARAM>(native));
    std::string name(native);
    chinese = language == 2 || (language == 0 && (name.find("chinese") != std::string::npos || name.find("Chinese") != std::string::npos));
}
bool save() {
    if (config.empty()) return false;
    auto temp = config + L".tmp";
    HANDLE f = CreateFileW(temp.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (f == INVALID_HANDLE_VALUE) { error(L"Cannot save folderpad++ settings.", L"无法保存 folderpad++ 设置。"); return false; }
    std::wstring text = L"\xFEFF[Settings]\r\nLanguage=" + std::to_wstring(language) + L"\r\nVisible=" + (visible ? L"1" : L"0") +
        L"\r\nCount=" + std::to_wstring(folders.size()) + L"\r\n[Folders]\r\n";
    for (size_t i = 0; i < folders.size(); ++i) text += std::to_wstring(i) + L"=" + folders[i] + L"\r\n";
    DWORD written = 0, size = static_cast<DWORD>(text.size() * sizeof(wchar_t));
    bool ok = WriteFile(f, text.data(), size, &written, nullptr) && written == size;
    if (ok) ok = FlushFileBuffers(f) != FALSE;
    CloseHandle(f);
    if (ok) ok = MoveFileExW(temp.c_str(), config.c_str(), MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH) != FALSE;
    if (!ok) error(L"Cannot save folderpad++ settings.", L"无法保存 folderpad++ 设置。");
    return ok;
}
void load() {
    int n = static_cast<int>(npp(NPPM_GETPLUGINSCONFIGDIR, 0, 0));
    if (n <= 0) return;
    std::wstring dir(n + 2, L'\0');
    npp(NPPM_GETPLUGINSCONFIGDIR, dir.size(), reinterpret_cast<LPARAM>(dir.data()));
    dir.resize(wcslen(dir.c_str()));
    std::error_code ec;
    std::filesystem::create_directories(dir, ec);
    config = dir + L"\\folderpad++.ini";
    language = GetPrivateProfileIntW(L"Settings", L"Language", 0, config.c_str());
    if (language < 0 || language > 2) language = 0;
    visible = GetPrivateProfileIntW(L"Settings", L"Visible", 1, config.c_str()) != 0;
    int count = std::min(4096, static_cast<int>(GetPrivateProfileIntW(L"Settings", L"Count", 0, config.c_str())));
    for (int i = 0; i < count; ++i) {
        wchar_t value[32768]{};
        GetPrivateProfileStringW(L"Folders", std::to_wstring(i).c_str(), L"", value, 32768, config.c_str());
        auto p = folderpad::normalize(value);
        if (!p.empty() && std::none_of(folders.begin(), folders.end(), [&](const auto& v) { return folderpad::equal(v, p); })) folders.push_back(p);
    }
}
int selectedGroup() { int i = TabCtrl_GetCurSel(tabs); return i >= 0 && i < static_cast<int>(folders.size()) ? i : -1; }
void layout() {
    if (!panel || !tabs) return;
    RECT r{}; GetClientRect(panel, &r);
    const int w = r.right, h = r.bottom;
    // Dialog units scale with the font/DPI used by the host.
    RECT units{0, 0, 100, 14}; MapDialogRect(panel, &units);
    int row = units.bottom + 6, gap = 6;
    int half = std::max(1, (w - 3 * gap) / 2);
    MoveWindow(addButton, gap, gap, half, row, TRUE);
    MoveWindow(removeButton, 2 * gap + half, gap, half, row, TRUE);
    int top = row + 2 * gap;
    MoveWindow(tabs, gap, top, std::max(1, w - 2 * gap), std::max(1, h - top - gap), TRUE);
    RECT inner{}; GetClientRect(tabs, &inner); TabCtrl_AdjustRect(tabs, FALSE, &inner);
    MapWindowPoints(tabs, panel, reinterpret_cast<POINT*>(&inner), 2);
    MoveWindow(pathLabel, inner.left + 4, inner.top + 4, std::max(1L, inner.right - inner.left - 8), row, TRUE);
    int listTop = inner.top + row + 6;
    MoveWindow(files, inner.left + 4, listTop, std::max(1L, inner.right - inner.left - 8), std::max(1L, inner.bottom - listTop - 4), TRUE);
    MoveWindow(emptyLabel, inner.left + 10, listTop + row, std::max(1L, inner.right - inner.left - 20), row * 3, TRUE);
    ListView_SetColumnWidth(files, 0, std::max(30L, inner.right - inner.left - 28));
    // Tab and page controls are siblings. Keep the tab background behind the
    // page, otherwise resizing/repainting the tab covers the file list.
    SetWindowPos(tabs, HWND_BOTTOM, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
    RedrawWindow(panel, nullptr, nullptr, RDW_INVALIDATE | RDW_ERASE | RDW_ALLCHILDREN);
}
void renderRows() {
    rebuilding = true;
    SendMessageW(files, WM_SETREDRAW, FALSE, 0);
    ListView_DeleteAllItems(files); rows.clear();
    int group = selectedGroup();
    auto active = static_cast<UINT_PTR>(npp(NPPM_GETCURRENTBUFFERID));
    for (const auto& d : documents) {
        if (d.group != group) continue;
        std::wstring label = d.path;
        if (group >= 0) {
            auto normalized = folderpad::normalize(d.path);
            size_t start = folders[group].size();
            if (start < normalized.size() && normalized[start] == L'\\') ++start;
            label = normalized.substr(start);
        }
        LVITEMW item{}; item.mask = LVIF_TEXT; item.iItem = static_cast<int>(rows.size()); item.pszText = label.data();
        ListView_InsertItem(files, &item); rows.push_back(d.id);
        if (d.id == active) ListView_SetItemState(files, item.iItem, LVIS_SELECTED | LVIS_FOCUSED, LVIS_SELECTED | LVIS_FOCUSED);
    }
    SetWindowTextW(pathLabel, group >= 0 ? folders[group].c_str() : tr(L"Unassigned and unsaved documents", L"未归属文件和未保存文档"));
    SetWindowTextW(emptyLabel, tr(L"No open documents in this tab.", L"此标签中没有已打开的文档。"));
    EnableWindow(removeButton, group >= 0);
    ShowWindow(emptyLabel, rows.empty() ? SW_SHOW : SW_HIDE);
    SendMessageW(files, WM_SETREDRAW, TRUE, 0); InvalidateRect(files, nullptr, TRUE);
    rebuilding = false;
}
void refresh(bool follow) {
    if (!panel) return;
    int selected = selectedGroup();
    documents.clear();
    for (int view = 0; view < 2; ++view) {
        // The hidden second view still owns a placeholder "new 1" buffer.
        // Check child visibility styles, not IsWindowVisible: the whole host
        // may itself be hidden/minimized during startup or automation.
        bool displayed = true;
        for (HWND child = view == 0 ? host._scintillaMainHandle : host._scintillaSecondHandle;
             child && child != host._nppHandle; child = GetParent(child)) {
            if (!(GetWindowLongPtrW(child, GWL_STYLE) & WS_VISIBLE)) { displayed = false; break; }
        }
        if (!displayed) continue;
        int count = static_cast<int>(npp(NPPM_GETNBOPENFILES, 0, view + 1));
        for (int i = 0; i < count; ++i) {
            auto id = static_cast<UINT_PTR>(npp(NPPM_GETBUFFERIDFROMPOS, i, view));
            if (!id || std::any_of(documents.begin(), documents.end(), [id](const auto& d) { return d.id == id; })) continue;
            auto len = npp(NPPM_GETFULLPATHFROMBUFFERID, id, 0);
            if (len <= 0) continue;
            std::wstring p(static_cast<size_t>(len) + 1, L'\0');
            npp(NPPM_GETFULLPATHFROMBUFFERID, id, reinterpret_cast<LPARAM>(p.data())); p.resize(wcslen(p.c_str()));
            documents.push_back({id, p, folderpad::owner(p, folders)});
        }
    }
    auto active = static_cast<UINT_PTR>(npp(NPPM_GETCURRENTBUFFERID));
    if (follow) for (const auto& d : documents) if (d.id == active) selected = d.group;
    TabCtrl_DeleteAllItems(tabs);
    for (size_t i = 0; i <= folders.size(); ++i) {
        int group = i == folders.size() ? -1 : static_cast<int>(i);
        auto count = std::count_if(documents.begin(), documents.end(), [group](const auto& d) { return d.group == group; });
        auto label = group < 0 ? std::wstring(tr(L"Other", L"其它")) : folderpad::leaf(folders[i]);
        label += L" (" + std::to_wstring(count) + L")";
        TCITEMW item{}; item.mask = TCIF_TEXT; item.pszText = label.data(); TabCtrl_InsertItem(tabs, static_cast<int>(i), &item);
    }
    TabCtrl_SetCurSel(tabs, selected >= 0 && selected < static_cast<int>(folders.size()) ? selected : static_cast<int>(folders.size()));
    layout(); renderRows();
}
void translate() {
    detectLanguage();
    SetWindowTextW(addButton, tr(L"Add folder...", L"添加文件夹…"));
    SetWindowTextW(removeButton, tr(L"Remove tab", L"移除标签"));
    refresh(false);
}
INT_PTR CALLBACK settingsProc(HWND hwnd, UINT msg, WPARAM w, LPARAM) {
    if (msg == WM_INITDIALOG) {
        SetWindowTextW(hwnd, tr(L"folderpad++ Settings", L"folderpad++ 设置"));
        SetDlgItemTextW(hwnd, 301, tr(L"Language:", L"语言："));
        SetDlgItemTextW(hwnd, IDOK, tr(L"OK", L"确定"));
        SetDlgItemTextW(hwnd, IDCANCEL, tr(L"Cancel", L"取消"));
        HWND combo = GetDlgItem(hwnd, 302);
        for (const auto* s : {tr(L"Follow Notepad++", L"跟随 Notepad++"), L"English", L"简体中文"})
            SendMessageW(combo, CB_ADDSTRING, 0, reinterpret_cast<LPARAM>(s));
        SendMessageW(combo, CB_SETCURSEL, language, 0);
        RECT owner{}, dialog{};
        GetWindowRect(host._nppHandle, &owner); GetWindowRect(hwnd, &dialog);
        SetWindowPos(hwnd, nullptr, owner.left + (owner.right - owner.left - dialog.right + dialog.left) / 2,
                     owner.top + (owner.bottom - owner.top - dialog.bottom + dialog.top) / 2,
                     0, 0, SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE);
        return TRUE;
    }
    if (msg == WM_COMMAND) {
        if (LOWORD(w) == IDOK) {
            int choice = static_cast<int>(SendDlgItemMessageW(hwnd, 302, CB_GETCURSEL, 0, 0));
            if (choice < 0 || choice > 2) return TRUE;
            int previous = language; language = choice;
            if (!save()) { language = previous; return TRUE; }
            translate(); EndDialog(hwnd, IDOK); return TRUE;
        }
        if (LOWORD(w) == IDCANCEL) { EndDialog(hwnd, IDCANCEL); return TRUE; }
    }
    if (msg == WM_CLOSE) { EndDialog(hwnd, IDCANCEL); return TRUE; }
    return FALSE;
}
void settings() {
    if (DialogBoxParamW(module, MAKEINTRESOURCEW(102), host._nppHandle, settingsProc, 0) == -1)
        error(L"Cannot open settings.", L"无法打开设置窗口。");
}

void openFiles(const std::wstring& folder) {
    HRESULT init = CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED);
    IFileOpenDialog* dialog = nullptr;
    HRESULT result = CoCreateInstance(CLSID_FileOpenDialog, nullptr, CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&dialog));
    std::vector<std::wstring> selected;
    if (SUCCEEDED(result)) {
        DWORD flags = 0; result = dialog->GetOptions(&flags);
        if (SUCCEEDED(result)) result = dialog->SetOptions(flags | FOS_FORCEFILESYSTEM | FOS_FILEMUSTEXIST | FOS_PATHMUSTEXIST | FOS_ALLOWMULTISELECT | FOS_NOCHANGEDIR);
        dialog->SetTitle(tr(L"Open files", L"打开文件"));
        const COMDLG_FILTERSPEC filters[]{{tr(L"All files", L"所有文件"), L"*.*"}};
        dialog->SetFileTypes(1, filters);
        if (SUCCEEDED(result) && !folder.empty()) {
            IShellItem* item = nullptr;
            result = SHCreateItemFromParsingName(folder.c_str(), nullptr, IID_PPV_ARGS(&item));
            if (SUCCEEDED(result)) {
                // SetFolder overrides the shell's remembered location on every invocation.
                result = dialog->SetFolder(item); item->Release();
            }
        }
        if (SUCCEEDED(result)) result = dialog->Show(host._nppHandle);
        if (SUCCEEDED(result)) {
            IShellItemArray* items = nullptr;
            result = dialog->GetResults(&items);
            if (SUCCEEDED(result)) {
                DWORD count = 0; result = items->GetCount(&count);
                for (DWORD i = 0; SUCCEEDED(result) && i < count; ++i) {
                    IShellItem* item = nullptr; result = items->GetItemAt(i, &item);
                    if (SUCCEEDED(result)) {
                        PWSTR path = nullptr; result = item->GetDisplayName(SIGDN_FILESYSPATH, &path);
                        if (SUCCEEDED(result)) { selected.emplace_back(path); CoTaskMemFree(path); }
                        item->Release();
                    }
                }
                items->Release();
            }
        }
        dialog->Release();
    }
    if (SUCCEEDED(init)) CoUninitialize();
    if (FAILED(result)) {
        if (result != HRESULT_FROM_WIN32(ERROR_CANCELLED))
            error(L"Cannot open the file picker in this folder. Check that the folder is accessible.", L"无法在此文件夹中打开文件选择窗口，请检查目录是否可访问。");
        return;
    }
    bool failed = false;
    for (const auto& path : selected) if (!npp(NPPM_DOOPEN, 0, reinterpret_cast<LPARAM>(path.c_str()))) failed = true;
    if (failed) error(L"Some selected files could not be opened.", L"部分所选文件无法打开。");
}
LRESULT CALLBACK tabProc(HWND hwnd, UINT msg, WPARAM w, LPARAM l, UINT_PTR, DWORD_PTR) {
    if (msg == WM_RBUTTONUP || msg == WM_CONTEXTMENU) {
        int index;
        if (msg == WM_CONTEXTMENU && l == -1) index = TabCtrl_GetCurSel(hwnd);
        else {
            TCHITTESTINFO hit{}; hit.pt = {GET_X_LPARAM(l), GET_Y_LPARAM(l)};
            if (msg == WM_CONTEXTMENU) ScreenToClient(hwnd, &hit.pt);
            index = TabCtrl_HitTest(hwnd, &hit);
        }
        if (index >= 0 && index <= static_cast<int>(folders.size())) {
            const auto folder = index < static_cast<int>(folders.size()) ? folders[index] : std::wstring{};
            TabCtrl_SetCurSel(hwnd, index); layout(); renderRows();
            openFiles(folder);
        }
        return 0;
    }
    if (msg == WM_NCDESTROY) RemoveWindowSubclass(hwnd, tabProc, 1);
    return DefSubclassProc(hwnd, msg, w, l);
}
void queueRefresh(bool follow) { if (panel) { followPending |= follow; SetTimer(panel, refreshTimer, 30, nullptr); } }
void activateRow() {
    if (rebuilding) return;
    int row = ListView_GetNextItem(files, -1, LVNI_SELECTED);
    if (row < 0 || row >= static_cast<int>(rows.size())) return;
    UINT_PTR id = rows[row]; int currentView = 0;
    npp(NPPM_GETCURRENTSCINTILLA, 0, reinterpret_cast<LPARAM>(&currentView));
    for (int v : {currentView, 1 - currentView}) {
        int count = static_cast<int>(npp(NPPM_GETNBOPENFILES, 0, v + 1));
        for (int i = 0; i < count; ++i) if (static_cast<UINT_PTR>(npp(NPPM_GETBUFFERIDFROMPOS, i, v)) == id) {
            npp(NPPM_ACTIVATEDOC, v, i); return;
        }
    }
    queueRefresh(true);
}
void showPanel();
void addFolder() {
    showPanel();
    HRESULT init = CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED);
    IFileOpenDialog* dialog = nullptr;
    if (SUCCEEDED(CoCreateInstance(CLSID_FileOpenDialog, nullptr, CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&dialog)))) {
        DWORD flags = 0; dialog->GetOptions(&flags);
        dialog->SetOptions(flags | FOS_PICKFOLDERS | FOS_FORCEFILESYSTEM | FOS_PATHMUSTEXIST | FOS_NOCHANGEDIR);
        dialog->SetTitle(tr(L"Add folder (open documents only)", L"添加文件夹（仅显示已打开文档）"));
        if (SUCCEEDED(dialog->Show(host._nppHandle))) {
            IShellItem* item = nullptr;
            if (SUCCEEDED(dialog->GetResult(&item))) {
                PWSTR raw = nullptr;
                if (SUCCEEDED(item->GetDisplayName(SIGDN_FILESYSPATH, &raw))) {
                    auto path = folderpad::normalize(raw); CoTaskMemFree(raw);
                    if (!path.empty()) {
                        auto it = std::find_if(folders.begin(), folders.end(), [&](const auto& p) { return folderpad::equal(p, path); });
                        int index = static_cast<int>(it - folders.begin());
                        if (it == folders.end()) { folders.push_back(path); save(); }
                        refresh(false); TabCtrl_SetCurSel(tabs, index); renderRows();
                    }
                }
                item->Release();
            }
        }
        dialog->Release();
    } else error(L"Cannot open the folder picker.", L"无法打开文件夹选择窗口。");
    if (SUCCEEDED(init)) CoUninitialize();
}
INT_PTR CALLBACK dialogProc(HWND hwnd, UINT msg, WPARAM w, LPARAM l) {
    switch (msg) {
    case WM_INITDIALOG: {
        panel = hwnd;
        font = reinterpret_cast<HFONT>(SendMessageW(hwnd, WM_GETFONT, 0, 0));
        auto control = [&](const wchar_t* cls, DWORD style, int id) {
            HWND c = CreateWindowExW(0, cls, L"", WS_CHILD | WS_VISIBLE | WS_CLIPSIBLINGS | style, 0, 0, 1, 1, hwnd, reinterpret_cast<HMENU>(static_cast<INT_PTR>(id)), module, nullptr);
            SendMessageW(c, WM_SETFONT, reinterpret_cast<WPARAM>(font), TRUE); return c;
        };
        addButton = control(L"BUTTON", WS_TABSTOP | BS_PUSHBUTTON, 201);
        removeButton = control(L"BUTTON", WS_TABSTOP | BS_PUSHBUTTON, 202);
        tabs = control(WC_TABCONTROLW, WS_TABSTOP | WS_CLIPSIBLINGS | TCS_MULTILINE, 204);
        SetWindowSubclass(tabs, tabProc, 1, 0);
        pathLabel = control(L"STATIC", SS_PATHELLIPSIS, 205);
        files = control(WC_LISTVIEWW, WS_TABSTOP | LVS_REPORT | LVS_SINGLESEL | LVS_NOCOLUMNHEADER | LVS_SHOWSELALWAYS, 206);
        ListView_SetExtendedListViewStyle(files, LVS_EX_FULLROWSELECT | LVS_EX_DOUBLEBUFFER | LVS_EX_INFOTIP);
        LVCOLUMNW col{}; col.mask = LVCF_WIDTH; col.cx = 250; ListView_InsertColumn(files, 0, &col);
        emptyLabel = control(L"STATIC", SS_CENTER, 207);
        SetWindowPos(emptyLabel, HWND_TOP, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
        translate(); return TRUE;
    }
    case WM_SIZE: layout(); return TRUE;
    case WM_TIMER:
        if (w == refreshTimer) { KillTimer(hwnd, refreshTimer); bool follow = followPending; followPending = false; refresh(follow); }
        return TRUE;
    case WM_COMMAND:
        if (LOWORD(w) == 201) addFolder();
        else if (LOWORD(w) == 202) {
            int group = selectedGroup();
            if (group >= 0) { folders.erase(folders.begin() + group); save(); refresh(true); }
        }
        return TRUE;
    case WM_NOTIFY: {
        auto* nm = reinterpret_cast<NMHDR*>(l);
        if (nm->code == DMN_CLOSE) { visible = false; save(); npp(NPPM_SETMENUITEMCHECK, commands[0]._cmdID, FALSE); return TRUE; }
        if (nm->hwndFrom == tabs && nm->code == TCN_SELCHANGE) { layout(); renderRows(); return TRUE; }
        if (nm->hwndFrom == files && (nm->code == NM_CLICK || nm->code == NM_DBLCLK)) { activateRow(); return TRUE; }
        if (nm->hwndFrom == files && nm->code == LVN_KEYDOWN) {
            auto* key = reinterpret_cast<NMLVKEYDOWN*>(l);
            if (key->wVKey == VK_RETURN || key->wVKey == VK_SPACE) activateRow();
        }
        if (nm->hwndFrom == files && nm->code == LVN_GETINFOTIPW) {
            auto* tip = reinterpret_cast<NMLVGETINFOTIPW*>(l);
            if (tip->iItem >= 0 && tip->iItem < static_cast<int>(rows.size())) for (const auto& d : documents) if (d.id == rows[tip->iItem]) lstrcpynW(tip->pszText, d.path.c_str(), tip->cchTextMax);
        }
        break;
    }
    case WM_DESTROY: KillTimer(hwnd, refreshTimer); panel = nullptr; break;
    }
    return FALSE;
}
void ensurePanel() {
    if (panel) return;
    INITCOMMONCONTROLSEX controls{sizeof(controls), ICC_TAB_CLASSES | ICC_LISTVIEW_CLASSES}; InitCommonControlsEx(&controls);
    auto hwnd = CreateDialogParamW(module, MAKEINTRESOURCEW(101), host._nppHandle, dialogProc, 0);
    if (!hwnd) { error(L"Cannot create folderpad++ panel.", L"无法创建 folderpad++ 面板。"); return; }
    DockedWidgetData dock{}; dock.hClient = hwnd; dock.pszName = L"folderpad++"; dock.dlgID = 0;
    dock.uMask = DWS_DF_CONT_LEFT; dock.pszModuleName = L"folderpad++.dll";
    npp(NPPM_DMMREGASDCKDLG, 0, reinterpret_cast<LPARAM>(&dock));
}
void showPanel() { ensurePanel(); if (panel) { visible = true; npp(NPPM_DMMSHOW, 0, reinterpret_cast<LPARAM>(panel)); npp(NPPM_SETMENUITEMCHECK, commands[0]._cmdID, TRUE); refresh(true); if (ready) save(); } }
void togglePanel() {
    if (!panel || !visible) showPanel();
    else { visible = false; npp(NPPM_DMMHIDE, 0, reinterpret_cast<LPARAM>(panel)); npp(NPPM_SETMENUITEMCHECK, commands[0]._cmdID, FALSE); save(); }
}
void about() { MessageBoxW(host._nppHandle, tr(L"folderpad++ " FOLDERPAD_VERSION_WSTRING L"\nOrganize open documents by folder.\nFolders are never scanned.\nGPL-3.0-or-later", L"folderpad++ " FOLDERPAD_VERSION_WSTRING L"\n按文件夹组织已打开文档，不扫描文件夹。\n移除标签不会关闭或删除文件。\nGPL-3.0-or-later"), L"folderpad++", MB_OK); }
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID) { if (reason == DLL_PROCESS_ATTACH) { module = h; DisableThreadLibraryCalls(h); } return TRUE; }
extern "C" __declspec(dllexport) BOOL isUnicode() { return TRUE; }
extern "C" __declspec(dllexport) const wchar_t* getName() { return L"folderpad++"; }
extern "C" __declspec(dllexport) void setInfo(NppData data) {
    host = data;
    const wchar_t* names[]{L"Show / Hide panel | 显示 / 隐藏面板", L"Add folder... | 添加文件夹…", L"About | 关于", L"Settings... | 设置…"};
    PFUNCPLUGINCMD funcs[]{togglePanel, addFolder, about, settings};
    for (int i = 0; i < 4; ++i) { lstrcpynW(commands[i]._itemName, names[i], menuItemSize); commands[i]._pFunc = funcs[i]; }
}
extern "C" __declspec(dllexport) FuncItem* getFuncsArray(int* count) { *count = 4; return commands; }
extern "C" __declspec(dllexport) LRESULT messageProc(UINT, WPARAM, LPARAM) { return TRUE; }
extern "C" __declspec(dllexport) void beNotified(SCNotification* notification) {
    if (!notification) return;
    switch (notification->nmhdr.code) {
    case NPPN_READY: load(); detectLanguage(); ready = true; ensurePanel(); if (visible) showPanel(); else npp(NPPM_DMMHIDE, 0, reinterpret_cast<LPARAM>(panel)); break;
    case NPPN_SHUTDOWN: ready = false; if (panel) { KillTimer(panel, refreshTimer); DestroyWindow(panel); } break;
    case NPPN_NATIVELANGCHANGED: if (panel && language == 0) translate(); break;
    case NPPN_BUFFERACTIVATED: case NPPN_FILESAVED: case NPPN_FILERENAMED: queueRefresh(true); break;
    case NPPN_FILEOPENED: case NPPN_FILECLOSED: case NPPN_FILEDELETED: case NPPN_DOCORDERCHANGED: queueRefresh(false); break;
    }
}
