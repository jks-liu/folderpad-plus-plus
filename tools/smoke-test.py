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

    def click_item(self, hwnd, rect_message, index):
        self.write(bytes(16))
        assert send(hwnd, rect_message, index, self.address)
        buf = C.create_string_buffer(16)
        assert k.ReadProcessMemory(self.handle, self.address, buf, 16, None)
        left, top, right, bottom = struct.unpack('<4i', buf.raw)
        point = ((top + bottom) // 2 << 16) | ((left + right) // 2)
        # ListView may enter a drag-detection loop on button-down, so post both
        # messages before waiting for the resulting selection/activation.
        u.PostMessageW(hwnd, 0x201, 1, point)
        u.PostMessageW(hwnd, 0x202, 0, point)

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
        combo = u.GetDlgItem(panel, 203)
        send(combo, 0x14e, 2, 0)
        send(panel, 0x111, 203 | (1 << 16), combo)
        check(labels()[-1] == '其它 (1)', 'Chinese language switches immediately')
        send(hwnd, 0x111, 41003, 0)
        wait_for(lambda: labels()[0] == '项目 (1)', 'Closed file remained listed')
        check(True, 'close notification removes file')
        send(hwnd, NPP + 28, 0, 1)
        wait_for(lambda: send(tab, 0x130b, 0, 0) == 1, 'Cannot select nested document')
        send(u.GetDlgItem(panel, 202), 0xf5, 0, 0)
        wait_for(lambda: labels() == ['项目 (2)', '其它 (1)'], 'Remove tab failed to reassign')
        check(send(hwnd, NPP + 7, 0, 0) >= 3, 'remove tab leaves documents open')
        remote.close()
        send(hwnd, 0x10, 0, 0)
        proc.wait(timeout=10)
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
        wait_for(lambda: row_text() == ['一.txt', 'nested\\二.txt'], 'Folder tab did not change')
        assert send(listing, 0x102b, 1, remote.write(bytes(selected)))
        remote.click_item(listing, 0x100e, 1)
        expected = send(hwnd, NPP + 59, 1, 0)
        wait_for(lambda: send(hwnd, NPP + 60, 0, 0) == expected, 'Clicked file did not activate')
        checks.append('clicking file row activates the matching host buffer')
        report = {'passed': len(checks), 'checks': checks, 'artifacts': str(base)}
        (base / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        remote.close()
        if proc.poll() is None:
            send(hwnd, 0x10, 0, 0)
            proc.wait(timeout=10)


if __name__ == '__main__':
    main()
