"""Run version-bump CLI checks against a disposable repository, never the real version.
Usage: python tests/version_tests.py (requires PowerShell 7 / pwsh).
"""
from pathlib import Path
import shutil
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
checks = 0
with tempfile.TemporaryDirectory(prefix='folderpad-version-') as temp:
    repo = Path(temp)
    (repo / 'tools').mkdir()
    (repo / 'src').mkdir()
    for name in ('version-lib.ps1', 'version-bump.ps1', 'package.ps1'):
        shutil.copy2(root / 'tools' / name, repo / 'tools' / name)
    header = repo / 'src/version.h'
    original = (root / 'src/version.h').read_text(encoding='utf-8')

    def seed():
        import re
        text = original
        for key, value in zip(('MAJOR', 'MINOR', 'PATCH'), (1, 2, 3)):
            text = re.sub(rf'(#define FOLDERPAD_VERSION_{key} )\d+', rf'\g<1>{value}', text)
        header.write_text(text, encoding='utf-8')

    def run(*args, success=True, script='version-bump.ps1'):
        result = subprocess.run(['pwsh', '-NoProfile', '-File', str(repo / 'tools' / script), *args],
                                capture_output=True, text=True, encoding='utf-8')
        assert (result.returncode == 0) == success, result.stdout + result.stderr
        return result.stdout.strip()

    for args, expected in [((), '1.2.4'), (('patch', '-NoBuild'), '1.2.4'),
                           (('minor',), '1.3.0'), (('major',), '2.0.0'),
                           (('3.4.5',), '3.4.5'), (('0.0.0',), '0.0.0')]:
        seed()
        run(*args)
        assert run('current') == expected
        checks += 1
    for args in [('01.2.3',), ('1.2',), ('1.2.3-beta',), ('65536.0.0',),
                 ('patch', '-Build', '-NoBuild'), ('current', '-Build'), ('unknown',)]:
        seed()
        before = header.read_bytes()
        run(*args, success=False)
        assert header.read_bytes() == before
        checks += 1
    seed()
    before = (header.read_bytes(), header.stat().st_mtime_ns)
    assert run('current') == '1.2.3'
    assert before == (header.read_bytes(), header.stat().st_mtime_ns)
    checks += 1
    run('-Version', '1.2.4', script='package.ps1', success=False)
    checks += 1
    # Stubs check orchestration without downloading or compiling in this test.
    for script in ('build', 'package'):
        (repo / f'tools/{script}.ps1').write_text(
            f"Add-Content -LiteralPath \"$PSScriptRoot/../calls.txt\" -Value '{script}'\n", encoding='utf-8')
    seed()
    run('patch', '-Build')
    assert (repo / 'calls.txt').read_text().splitlines() == ['build', 'package']
    assert run('current') == '1.2.4'
    checks += 1
    (repo / 'tools/build.ps1').write_text("throw 'test failure'\n", encoding='utf-8')
    run('minor', '-Build', success=False)
    assert run('current') == '1.3.0'
    assert (repo / 'calls.txt').read_text().splitlines() == ['build', 'package']
    checks += 1
print(f'{checks} version CLI checks passed')
