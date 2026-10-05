"""Exercise the DLL inside an isolated copy of installed Notepad++ (Windows x64).

Usage: python tools/smoke-test.py [--notepad-dir "C:/Program Files/Notepad++"]
Creates build/smoke-<timestamp>; keeps artifacts for inspection. Uses only its own
process and sample files. Never sends commands to a user's existing editor.
"""
import argparse
import ctypes as C
from ctypes import wintypes as W
from pathlib import Path
import shutil
import subprocess
import time
import json
import sys
import os
import struct

sys.stdout.reconfigure(encoding='utf-8')

u = C.WinDLL('user32', use_last_error=True)
k = C.WinDLL('kernel32', use_last_error=True)
u.SendMessageW.argtypes = [W.HWND, W.UINT, C.c_size_t, C.c_ssize_t]
u.SendMessageW.restype = C.c_ssize_t
u.GetDlgItem.argtypes = [W.HWND, C.c_int]
u.GetDlgItem.restype = W.HWND
u.GetParent.argtypes = [W.HWND]
u.GetParent.restype = W.HWND
u.SetWindowTextW.argtypes = [W.HWND, W.LPCWSTR]
u.PostMessageW.argtypes = [W.HWND, W.UINT, C.c_size_t, C.c_ssize_t]
u.GetWindowThreadProcessId.argtypes = [W.HWND, C.POINTER(W.DWORD)]
u.SetWindowPos.argtypes = [W.HWND, W.HWND, C.c_int, C.c_int, C.c_int, C.c_int, W.UINT]
u.ChildWindowFromPointEx.argtypes = [W.HWND, W.POINT, W.UINT]
u.ChildWindowFromPointEx.restype = W.HWND
u.GetMenu.argtypes = [W.HWND]
u.GetMenu.restype = W.HMENU
u.GetSubMenu.argtypes = [W.HMENU, C.c_int]
u.GetSubMenu.restype = W.HMENU
u.GetMenuItemCount.argtypes = [W.HMENU]
u.GetMenuItemID.argtypes = [W.HMENU, C.c_int]
u.GetMenuStringW.argtypes = [W.HMENU, W.UINT, W.LPWSTR, C.c_int, W.UINT]
k.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]
k.OpenProcess.restype = W.HANDLE
k.VirtualAllocEx.argtypes = [W.HANDLE, C.c_void_p, C.c_size_t, W.DWORD, W.DWORD]
k.VirtualAllocEx.restype = C.c_void_p
k.VirtualFreeEx.argtypes = [W.HANDLE, C.c_void_p, C.c_size_t, W.DWORD]
k.WriteProcessMemory.argtypes = [W.HANDLE, C.c_void_p, C.c_void_p, C.c_size_t, C.c_void_p]
k.ReadProcessMemory.argtypes = [W.HANDLE, C.c_void_p, C.c_void_p, C.c_size_t, C.c_void_p]
k.CloseHandle.argtypes = [W.HANDLE]
callback_type = C.WINFUNCTYPE(W.BOOL, W.HWND, C.c_ssize_t)
send = u.SendMessageW
NPP = 1024 + 1000


def windows(parent=None):
    result = []
    @callback_type
    def cb(hwnd, _):
        result.append(hwnd)
        return True
    if parent:
        u.EnumChildWindows(parent, cb, 0)
    else:
        u.EnumWindows(cb, 0)
    return result


def classname(hwnd):
    buf = C.create_unicode_buffer(256)
    u.GetClassNameW(hwnd, buf, 256)
    return buf.value


class Remote:
    def __init__(self, pid):
        self.handle = k.OpenProcess(0x38 | 0x400, False, pid)
        if not self.handle:
            raise C.WinError(C.get_last_error())
        self.address = k.VirtualAllocEx(self.handle, None, 65536, 0x3000, 4)
        if not self.address:
            raise C.WinError(C.get_last_error())

    def write(self, data, offset=0):
        buf = C.create_string_buffer(data)
        if not k.WriteProcessMemory(self.handle, self.address + offset, buf, len(data), None):
            raise C.WinError(C.get_last_error())
        return self.address + offset

    def read_text(self, offset=4096):
        buf = C.create_string_buffer(32768)
        if not k.ReadProcessMemory(self.handle, self.address + offset, buf, len(buf), None):
            raise C.WinError(C.get_last_error())
        return buf.raw.decode('utf-16-le').split('\0', 1)[0]

    def click_item(self, hwnd, rect_message, index, right=False):
        self.write(bytes(16))
        assert send(hwnd, rect_message, index, self.address)
        buf = C.create_string_buffer(16)
        assert k.ReadProcessMemory(self.handle, self.address, buf, 16, None)
        left, top, right, bottom = struct.unpack('<4i', buf.raw)
        point = ((top + bottom) // 2 << 16) | ((left + right) // 2)
        # ListView may enter a drag-detection loop on button-down, so post both
        # messages before waiting for the resulting selection/activation.
        u.PostMessageW(hwnd, 0x204 if right else 0x201, 2 if right else 1, point)
        u.PostMessageW(hwnd, 0x205 if right else 0x202, 0, point)

    def close(self):
        k.VirtualFreeEx(self.handle, self.address, 0, 0x8000)
        k.CloseHandle(self.handle)


class TCITEM(C.Structure):
    _fields_ = [('mask', W.UINT), ('state', W.DWORD), ('stateMask', W.DWORD),
                ('text', C.c_void_p), ('size', C.c_int), ('image', C.c_int), ('param', C.c_ssize_t)]


class LVITEM(C.Structure):
    _fields_ = [('mask', W.UINT), ('item', C.c_int), ('sub', C.c_int), ('state', W.UINT),
               ('stateMask', W.UINT), ('text', C.c_void_p), ('size', C.c_int), ('image', C.c_int),
               ('param', C.c_ssize_t), ('indent', C.c_int), ('group', C.c_int), ('cols', W.UINT),
               ('columns', C.c_void_p), ('formats', C.c_void_p), ('groupIndex', C.c_int)]


class NMHDR(C.Structure):
    _fields_ = [('hwnd', W.HWND), ('id', C.c_size_t), ('code', W.UINT)]


def wait_for(fn, message):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        result = fn()
        if result:
            return result
        time.sleep(.1)
    raise AssertionError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--notepad-dir', default='C:/Program Files/Notepad++')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    base = root / 'build' / ('smoke-' + time.strftime('%Y%m%d-%H%M%S'))
    app = base / 'app'
    app.mkdir(parents=True)
    original = Path(args.notepad_dir)
    shutil.copytree(original, app, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('plugins', 'updater', 'uninstall.exe'))
    (app / 'doLocalConf.xml').touch()
    plugin = app / 'plugins' / 'folderpad++'
    plugin.mkdir(parents=True)
    shutil.copy2(root / 'build/x86_64/folderpad++.dll', plugin)
    conf = app / 'plugins/config/folderpad++.ini'
    conf.parent.mkdir(parents=True)
    plugin_list = original / 'plugins/Config/nppPluginList.dll'
    if plugin_list.exists():
        shutil.copy2(plugin_list, conf.parent)
    project = base / '项目'
    nested = project / 'nested'
    nested.mkdir(parents=True)
    outside = base / '项目-other'
    outside.mkdir()
    paths = [project / '一.txt', nested / '二.txt', outside / 'other.txt']
    for p in paths:
        p.write_text('folderpad smoke test\n', encoding='utf-8')
    conf.write_text(f'[Settings]\nLanguage=1\nVisible=1\nCount=2\n[Folders]\n0={project}\n1={nested}\n', encoding='utf-16')
    checks = []

    def launch(documents):
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0
        # Codex/shells may export the POSIX locale C.UTF-8, which MSVC's
        # std::locale does not recognize. Keep the editor's native Windows locale.
        env = {key: value for key, value in os.environ.items()
               if key not in ('LANG', 'LC_ALL', 'LC_CTYPE')}
        proc = subprocess.Popen([str(app / 'notepad++.exe'), '-multiInst', '-nosession', *map(str, documents)],
                                startupinfo=startup, cwd=app, env=env)
        def find():
            if proc.poll() is not None:
                raise RuntimeError(f'Notepad++ exited during startup: {proc.returncode:#x}; app={app}')
            for hwnd in windows():
                pid = W.DWORD()
                u.GetWindowThreadProcessId(hwnd, C.byref(pid))
                if pid.value == proc.pid and classname(hwnd) == 'Notepad++':
                    return hwnd
        hwnd = wait_for(find, 'Notepad++ window not found')
        tab = wait_for(lambda: next((h for h in windows(hwnd) if classname(h) == 'SysTabControl32' and u.GetDlgItem(u.GetParent(h), 204) == h), None), 'Plugin did not load')
        return proc, hwnd, tab, Remote(proc.pid)

    proc, hwnd, tab, remote = launch(paths)
    try:
        panel = u.GetParent(tab)
        listing = u.GetDlgItem(panel, 206)

        def owned_dialog(control=None):
            for candidate in windows():
                pid = W.DWORD()
                u.GetWindowThreadProcessId(candidate, C.byref(pid))
                if pid.value == proc.pid and classname(candidate) == '#32770' and candidate != panel:
                    if control is None or u.GetDlgItem(candidate, control):
                        return candidate

        def menu_command(menu, label):
            for index in range(u.GetMenuItemCount(menu)):
                text = C.create_unicode_buffer(256)
                u.GetMenuStringW(menu, index, text, 256, 0x400)
                child = u.GetSubMenu(menu, index)
                if child:
                    found = menu_command(child, label)
                    if found is not None:
                        return found
                elif label in text.value:
                    return u.GetMenuItemID(menu, index)

        def settings_window():
            command = menu_command(u.GetMenu(hwnd), 'Settings... |')
            assert command is not None
            u.PostMessageW(hwnd, 0x111, command, 0)
            return wait_for(lambda: owned_dialog(302), 'Settings dialog missing')

        def labels():
            result = []
            for i in range(send(tab, 0x1304, 0, 0)):
                item = TCITEM(mask=1, text=remote.address + 4096, size=16000)
                remote.write(bytes(item))
                send(tab, 0x133c, i, remote.address)
                result.append(remote.read_text())
            return result

        def row_text():
            result = []
            for i in range(send(listing, 0x1004, 0, 0)):
                item = LVITEM(sub=0, text=remote.address + 4096, size=16000)
                remote.write(bytes(item))
                send(listing, 0x1073, i, remote.address)
                result.append(remote.read_text())
            return result

        def check(condition, name):
            assert condition, f'{name}: tabs={labels()}, rows={row_text()}'
            checks.append(name)

        time.sleep(.4)
        print('Initial tabs:', labels(), 'rows:', row_text(), flush=True)
        wait_for(lambda: labels() == ['项目 (1)', 'nested (1)', 'Other (1)'], 'Initial ownership incorrect')
        check(True, 'load DLL; Unicode folders; nested ownership; prefix boundary')
        send(hwnd, NPP + 28, 0, 1)
        wait_for(lambda: send(tab, 0x130b, 0, 0) == 1, 'Active document tab did not follow')
        wait_for(lambda: row_text() == ['二.txt'], 'Relative file row missing')
        check(row_text() == ['二.txt'], 'relative file labels; follow active document')
        original_rect = W.RECT()
        u.GetWindowRect(panel, C.byref(original_rect))
        for width in (420, 180, 560, 260):
            assert u.SetWindowPos(panel, None, 0, 0, width, 500, 0x16)
            u.RedrawWindow(panel, None, None, 0x185)  # invalidate, erase, all children, update now
            rect = W.RECT()
            u.GetWindowRect(listing, C.byref(rect))
            point = W.POINT(rect.left + 12, rect.top + 12)
            u.ScreenToClient(panel, C.byref(point))
            assert u.ChildWindowFromPointEx(panel, point, 7) == listing, 'File list is covered after panel resize'
            check(row_text() == ['二.txt'], f'file list remains exposed after resize to {width}px')
        u.SetWindowPos(panel, None, 0, 0, original_rect.right - original_rect.left,
                       original_rect.bottom - original_rect.top, 0x16)
        send(hwnd, 0x111, 10002, 0)
        time.sleep(.25)
        check(labels() == ['项目 (1)', 'nested (1)', 'Other (1)'], 'clone into second view is deduplicated')
        send(hwnd, 0x111, 41001, 0)
        wait_for(lambda: labels()[-1] == 'Other (2)', 'Unsaved document missing')
        wait_for(lambda: send(tab, 0x130b, 0, 0) == 2, 'Unsaved document tab not selected')
        check(send(tab, 0x130b, 0, 0) == 2, 'unsaved document belongs to Other')
        target = project / 'saved.txt'
        ptr = remote.write((str(target) + '\0').encode('utf-16-le'))
        check(send(hwnd, NPP + 78, 0, ptr) != 0, 'save new document')
        wait_for(lambda: labels()[0] == '项目 (2)', 'Save As did not update ownership')
        wait_for(lambda: send(tab, 0x130b, 0, 0) == 0, 'Saved document tab not selected')
        check(send(tab, 0x130b, 0, 0) == 0, 'Save As automatically regroups document')
        check(not u.GetDlgItem(panel, 203), 'language selector removed from panel')
        dialog = settings_window()
        combo = u.GetDlgItem(dialog, 302)
        send(combo, 0x14e, 2, 0)
        send(dialog, 0x111, 2, 0)
        check(labels()[-1] == 'Other (1)', 'cancel settings leaves language unchanged')
        dialog = settings_window()
        combo = u.GetDlgItem(dialog, 302)
        check(send(combo, 0x147, 0, 0) == 1, 'settings reloads persisted language')
        send(combo, 0x14e, 2, 0)
        send(dialog, 0x111, 1, 0)
        check(labels()[-1] == '其它 (1)', 'Chinese language switches immediately')
        send(hwnd, 0x111, 41003, 0)
        wait_for(lambda: labels()[0] == '项目 (1)', 'Closed file remained listed')
        check(True, 'close notification removes file')
        # The selected tab is elsewhere: right-click must use the hit tab,
        # and override the shell dialog's previous location.
        for index, directory in ((0, project), (1, nested)):
            name = f'right-click-{index}.txt'
            (directory / name).write_text('opened via tab\n', encoding='utf-8')
            remote.click_item(tab, 0x130a, index, right=True)
            picker = wait_for(lambda: owned_dialog(), 'Right-click file picker missing')
            time.sleep(.8)
            input_box = wait_for(lambda: next((c for c in windows(picker)
                                               if classname(c) == 'Edit' and u.GetDlgCtrlID(c) == 1148
                                               and u.IsWindowVisible(c)), None), 'Filename input missing')
            # Typing sends edit-change notifications used by the shell dialog;
            # WM_SETTEXT alone does not reliably update its selected filename.
            send(input_box, 0xb1, 0, -1)  # EM_SETSEL
            send(input_box, 0x303, 0, 0)  # WM_CLEAR
            for char in name:
                send(input_box, 0x102, ord(char), 1)
            u.PostMessageW(picker, 0x111, 1, 0)
            def current_path():
                active = send(hwnd, NPP + 60, 0, 0)
                send(hwnd, NPP + 58, active, remote.address + 4096)
                return remote.read_text()
            wait_for(lambda: current_path() == str(directory / name), 'Relative filename did not open in clicked folder')
            checks.append(f'right-click tab {index} opens file relative to its folder')
            send(hwnd, 0x111, 41003, 0)
        remote.click_item(tab, 0x130a, 2, right=True)
        picker = wait_for(lambda: owned_dialog(), 'Other tab file picker missing')
        time.sleep(.3)
        send(picker, 0x111, 2, 0)
        checks.append('Other tab opens picker and cancellation is harmless')
        send(hwnd, NPP + 28, 0, 1)
        wait_for(lambda: send(tab, 0x130b, 0, 0) == 1, 'Cannot select nested document')
        send(u.GetDlgItem(panel, 202), 0xf5, 0, 0)
        wait_for(lambda: labels() == ['项目 (2)', '其它 (1)'], 'Remove tab failed to reassign')
        check(send(hwnd, NPP + 7, 0, 0) >= 3, 'remove tab leaves documents open')
        remote.close()
        send(hwnd, 0x10, 0, 0)
        proc.wait(timeout=30)
        proc, hwnd, tab, remote = launch(paths)
        wait_for(lambda: send(tab, 0x1304, 0, 0) == 2, 'Persisted folders not restored')
        saved = conf.read_text(encoding='utf-16')
        assert 'Language=2' in saved and 'Count=1' in saved
        checks.append('restart restores folders and language')
        panel = u.GetParent(tab)
        u.PostMessageW(u.GetDlgItem(panel, 201), 0xf5, 0, 0)
        def picker_window():
            for candidate in windows():
                pid = W.DWORD()
                u.GetWindowThreadProcessId(candidate, C.byref(pid))
                if pid.value == proc.pid and classname(candidate) == '#32770' and candidate != panel:
                    return candidate
        picker = wait_for(picker_window, 'Folder picker did not appear')
        time.sleep(.8)  # Native shell dialog initializes its filename controls asynchronously.
        wait_for(lambda: u.GetDlgItem(picker, 1), 'Folder picker accept button missing')
        u.PostMessageW(picker, 0x111, 1, 0)
        wait_for(lambda: send(tab, 0x1304, 0, 0) == 3, 'Adding folder through picker failed')
        time.sleep(.2)
        saved = conf.read_text(encoding='utf-16')
        assert 'Count=2' in saved
        checks.append('native folder picker adds and persists the selected folder')
        listing = u.GetDlgItem(panel, 206)
        # Native control input generates WM_NOTIFY inside the host. Windows
        # does not support synthesizing WM_NOTIFY across process boundaries.
        remote.click_item(tab, 0x130a, 0)
        selected = LVITEM(state=3, stateMask=3)
        # The native picker may remember the nested folder from the new
        # right-click tests, so only rely on the first folder's direct child.
        wait_for(lambda: bool(row_text()) and row_text()[0] == '一.txt', 'Folder tab did not change')
        assert send(listing, 0x102b, 0, remote.write(bytes(selected)))
        # Exercise native LVN_KEYDOWN without moving the user's real mouse.
        send(listing, 0x100, 0x0d, 0)
        wait_for(lambda: current_path() == str(paths[0]), 'Selected file did not activate')
        checks.append('Enter on file row activates the matching host buffer')
        report = {'passed': len(checks), 'checks': checks, 'artifacts': str(base)}
        (base / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        remote.close()
        if proc.poll() is None:
            send(hwnd, 0x10, 0, 0)
            proc.wait(timeout=30)


if __name__ == '__main__':
    main()
