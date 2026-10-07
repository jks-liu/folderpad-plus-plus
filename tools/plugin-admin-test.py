"""Test install/remove/update via the real Plugins Admin and Debug GUP (Windows x64).

Usage: python tools/plugin-admin-test.py --debug-exe <Notepad++.exe>
       --debug-gup <GUP.exe> --old-package <previous-release.zip>
Copies the installed host into build/plugin-admin-<timestamp>. Serves the frozen
release ZIP on loopback only; never changes a user's editor or publishes a file.
The Debug executables must come from the official Notepad++/WinGUp build artifacts.
"""
import argparse
import ctypes as C
from ctypes import wintypes as W
import hashlib
import http.server
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time
import zipfile
import xml.etree.ElementTree as ET

spec = importlib.util.spec_from_file_location('smoke', Path(__file__).with_name('smoke-test.py'))
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)
u, k, send = smoke.u, smoke.k, smoke.send
k.QueryFullProcessImageNameW.argtypes = [W.HANDLE, W.DWORD, W.LPWSTR, C.POINTER(W.DWORD)]
k.TerminateProcess.argtypes = [W.HANDLE, W.UINT]
u.IsWindowVisible.argtypes = [W.HWND]
u.IsWindowEnabled.argtypes = [W.HWND]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--notepad-dir', default='C:/Program Files/Notepad++')
    parser.add_argument('--debug-exe', required=True)
    parser.add_argument('--debug-gup', required=True)
    parser.add_argument('--old-package', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    entry = json.loads((root / 'dist/nppPluginList-entry-x64.json').read_text(encoding='utf-8'))
    package = root / 'dist' / f'folderpad++-{entry["version"]}-x64.zip'
    assert hashlib.sha256(package.read_bytes()).hexdigest() == entry['id'], 'Stale release metadata'
    with zipfile.ZipFile(package) as archive:
        expected_dll = archive.read('folderpad++.dll')
    with zipfile.ZipFile(args.old_package) as archive:
        candidates = [name for name in archive.namelist() if Path(name).name == 'folderpad++.dll']
        assert len(candidates) == 1, 'Previous ZIP must contain one plugin DLL'
        old_dll = archive.read(candidates[0])
    assert old_dll != expected_dll, 'Update requires a different previous DLL'
    base = root / 'build' / ('plugin-admin-' + time.strftime('%Y%m%d-%H%M%S'))
    app = base / 'app'
    app.mkdir(parents=True)
    original = Path(args.notepad_dir)
    shutil.copytree(original, app, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('plugins', 'uninstall.exe'))
    shutil.copy2(args.debug_exe, app / 'notepad++.exe')
    shutil.copy2(args.debug_gup, app / 'updater/GUP.exe')
    (app / 'doLocalConf.xml').touch()
    # GUP restarts without -multiInst: enforce it in this copy's local config
    # so the restarted editor cannot redirect to another running installation.
    config_xml = app / 'config.xml'
    tree = ET.parse(config_xml) if config_xml.exists() else ET.ElementTree(ET.Element('NotepadPlus'))
    gui = tree.getroot().find('GUIConfigs')
    if gui is None:
        gui = ET.SubElement(tree.getroot(), 'GUIConfigs')
    for name, text, attrs in [('multiInst', None, {'setting': '2'}),
                               ('RememberLastSession', 'no', {}), ('noUpdate', 'yes', {})]:
        node = gui.find(f"GUIConfig[@name='{name}']")
        if node is None:
            node = ET.SubElement(gui, 'GUIConfig', name=name)
        node.attrib.update(attrs)
        if text is not None:
            node.text = text
    tree.write(config_xml, encoding='utf-8', xml_declaration=True)
    config_dir = app / 'plugins/Config'
    config_dir.mkdir(parents=True)
    plugin_dir = app / 'plugins/folderpad++'
    dll = plugin_dir / 'folderpad++.dll'
    executable = app / 'notepad++.exe'
    checks, downloads, known_pids = [], [], set()
    env = {key: value for key, value in os.environ.items()
           if key not in ('LANG', 'LC_ALL', 'LC_CTYPE')}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != '/release.zip':
                self.send_error(404)
                return
            data = package.read_bytes()
            downloads.append(hashlib.sha256(data).hexdigest())
            self.send_response(200)
            self.send_header('Content-Type', 'application/zip')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *_):
            pass

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    local_entry = dict(entry, repository=f'http://127.0.0.1:{server.server_port}/release.zip')
    plugin_list = {'name': 'npp-pluginList', 'version': '1', 'arch': '64', 'npp-plugins': [local_entry]}
    (config_dir / 'nppPluginList.json').write_text(json.dumps(plugin_list), encoding='utf-8')

    def pid_of(hwnd):
        pid = W.DWORD()
        u.GetWindowThreadProcessId(hwnd, C.byref(pid))
        return pid.value

    def host_window():
        for hwnd in smoke.windows():
            if smoke.classname(hwnd) != 'Notepad++':
                continue
            pid = pid_of(hwnd)
            handle = k.OpenProcess(0x1000, False, pid)
            if not handle:
                continue
            try:
                path, size = C.create_unicode_buffer(32768), W.DWORD(32768)
                if k.QueryFullProcessImageNameW(handle, 0, path, C.byref(size)) and Path(path.value) == executable:
                    known_pids.add(pid)
                    return hwnd
            finally:
                k.CloseHandle(handle)

    def dialog_for(hwnd, control):
        pid = pid_of(hwnd)
        return next((candidate for candidate in smoke.windows()
                     if pid_of(candidate) == pid and smoke.classname(candidate) == '#32770'
                     and u.GetDlgItem(candidate, control) and u.IsWindowVisible(candidate)), None)

    def menu_command(menu):
        for index in range(u.GetMenuItemCount(menu)):
            child = u.GetSubMenu(menu, index)
            if child:
                found = menu_command(child)
                if found is not None:
                    return found
            else:
                # Official IDM_SETTING_PLUGINADM is 48015, independent of UI language.
                if u.GetMenuItemID(menu, index) == 48015:
                    return u.GetMenuItemID(menu, index)

    def launch():
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0
        proc = subprocess.Popen([str(executable), '-multiInst', '-nosession'], cwd=app, env=env, startupinfo=startup)
        known_pids.add(proc.pid)
        return smoke.wait_for(host_window, 'Isolated Debug Notepad++ did not start')

    def perform(hwnd, tab_index, button_id, label):
        command = smoke.wait_for(lambda: menu_command(u.GetMenu(hwnd)), 'Plugins Admin menu unavailable')
        u.PostMessageW(hwnd, 0x111, command, 0)
        admin = smoke.wait_for(lambda: dialog_for(hwnd, 5502), 'Plugins Admin did not open')
        tab = next(h for h in smoke.windows(admin) if smoke.classname(h) == 'SysTabControl32')
        remote = smoke.Remote(pid_of(hwnd))
        try:
            # Native keyboard input emits TCN_SELCHANGE without moving the real cursor.
            for _ in range(tab_index):
                send(tab, 0x100, 0x27, 0)  # WM_KEYDOWN / VK_RIGHT
                send(tab, 0x101, 0x27, 0)
            smoke.wait_for(lambda: send(tab, 0x130B, 0, 0) == tab_index, 'Plugins Admin tab did not switch')
            listing = smoke.wait_for(lambda: next((h for h in smoke.windows(admin)
                if smoke.classname(h) == 'SysListView32' and u.IsWindowVisible(h)), None), 'Plugin list missing')
            smoke.wait_for(lambda: send(listing, 0x1004, 0, 0) == 1, f'{label}: expected one plugin')
            item = smoke.LVITEM(state=0x2000, stateMask=0xF000)
            assert send(listing, 0x102b, 0, remote.write(bytes(item))), 'Cannot check plugin'
            button = u.GetDlgItem(admin, button_id)
            smoke.wait_for(lambda: u.IsWindowEnabled(button), 'Operation button not enabled')
            u.PostMessageW(button, 0xF5, 0, 0)
            confirmation = smoke.wait_for(lambda: dialog_for(hwnd, 6), 'Restart confirmation missing')
            u.PostMessageW(confirmation, 0x111, 6, 0)  # IDYES, within isolated test host
        finally:
            remote.close()
        old_pid = pid_of(hwnd)
        restarted = smoke.wait_for(lambda: (h if (h := host_window()) and pid_of(h) != old_pid else None),
                                    f'{label}: GUP did not restart host')
        print(label + ': restarted', flush=True)
        return restarted

    def close(hwnd):
        send(hwnd, 0x10, 0, 0)
        smoke.wait_for(lambda: not host_window(), 'Test host did not close')

    report = {'status': 'running', 'artifacts': str(base), 'checks': checks,
              'zipSHA256': entry['id'], 'downloadMode': 'loopback server; exact release ZIP bytes',
              'debugExecutable': str(Path(args.debug_exe).resolve()), 'debugGUP': str(Path(args.debug_gup).resolve())}
    try:
        hwnd = launch()
        hwnd = perform(hwnd, 0, 5503, 'install')
        smoke.wait_for(lambda: dll.exists(), 'Installed DLL missing')
        assert dll.read_bytes() == expected_dll
        smoke.wait_for(lambda: any(smoke.classname(h) == 'SysTabControl32'
            and u.GetDlgItem(u.GetParent(h), 204) == h for h in smoke.windows(hwnd)), 'Installed plugin not loaded')
        checks.append('Plugins Admin installs the exact release ZIP and loads the DLL after restart')
        hwnd = perform(hwnd, 2, 5505, 'remove')
        assert not dll.exists()
        checks.append('Plugins Admin removes the installed plugin and restarts normally')
        close(hwnd)
        plugin_dir.mkdir(exist_ok=True)
        dll.write_bytes(old_dll)
        config = config_dir / 'folderpad++.ini'
        config.write_text('[Settings]\nLanguage=2\nVisible=1\nCount=1\n[Folders]\n0=' + str(base) + '\n', encoding='utf-16')
        old_config = config.read_bytes()
        # A marker proves that the updater cleans the previous plugin folder.
        marker = plugin_dir / 'obsolete-test-file.txt'
        marker.write_text('old release', encoding='utf-8')
        hwnd = launch()
        hwnd = perform(hwnd, 1, 5504, 'update')
        assert dll.read_bytes() == expected_dll and not marker.exists()
        assert config.read_bytes() == old_config, 'Update altered existing settings'
        checks.append('Plugins Admin upgrades the previous DLL, cleans obsolete files, and preserves settings')
        assert downloads == [entry['id'], entry['id']], 'Unexpected download bytes/count'
        report['downloads'] = downloads
        report['status'] = 'passed'
    except Exception as exc:
        report['status'], report['error'] = 'failed', str(exc)
        raise
    finally:
        report['passed'] = len(checks)
        (base / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        server.shutdown()
        server.server_close()
        # Close only windows whose executable matches this test's app directory.
        if hwnd := host_window():
            send(hwnd, 0x10, 0, 0)
        print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
