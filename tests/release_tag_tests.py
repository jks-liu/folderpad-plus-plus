"""Check release guards in a temporary Git repository; never change real tags.
Usage: python tests/release_tag_tests.py (requires Git and PowerShell 7).
"""
from pathlib import Path
import shutil
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
checks = 0
with tempfile.TemporaryDirectory(prefix='folderpad-release-tag-') as temp:
    repo = Path(temp)
    for name in ('tools', 'src', 'docs/releases'):
        (repo / name).mkdir(parents=True)
    for name in ('version-lib.ps1', 'validate-release-tag.ps1'):
        shutil.copy2(root / 'tools' / name, repo / 'tools' / name)
    (repo / 'src/version.h').write_text(
        '#define FOLDERPAD_VERSION_MAJOR 1\n'
        '#define FOLDERPAD_VERSION_MINOR 2\n'
        '#define FOLDERPAD_VERSION_PATCH 3\n', encoding='utf-8')
    notes = repo / 'docs/releases/1.2.3.md'
    notes.write_text('Release notes / 发布说明\n', encoding='utf-8')

    def git(*args):
        return subprocess.run(['git', '-C', str(repo), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def guard(tag, success, message='', expected=None):
        global checks
        args = ['pwsh', '-NoProfile', '-File', str(repo / 'tools/validate-release-tag.ps1'),
                '-Tag', tag]
        if expected:
            args += ['-ExpectedCommit', expected]
        result = subprocess.run(args, capture_output=True, text=True, encoding='utf-8')
        output = result.stdout + result.stderr
        assert (result.returncode == 0) == success, output
        assert message in output, output
        checks += 1

    git('init')
    git('config', 'user.name', 'Release Guard Test')
    git('config', 'user.email', 'release-test@example.invalid')
    git('config', 'tag.gpgSign', 'false')
    git('config', 'commit.gpgSign', 'false')
    git('add', '.')
    git('commit', '-m', 'Seed release')
    commit = git('rev-parse', 'HEAD')
    tag = 'releases/v1.2.3'
    guard(tag, False, 'annotated tag')
    git('tag', tag)
    guard(tag, False, 'annotated tag')
    git('tag', '-d', tag)
    git('tag', '-a', tag, '-m', 'Release 1.2.3')
    guard(tag, True, 'Validated', expected=commit)
    # Accept a triggering SHA that resolves to the annotated tag object, too.
    guard(tag, True, 'Validated', expected=git('rev-parse', f'refs/tags/{tag}'))
    for bad in ('v1.2.3', 'releases/v01.2.3', 'releases/v1.2.3-beta',
                'releases/v1.2.3/extra', 'Releases/v1.2.3'):
        guard(bad, False, 'Release tag must be')
    guard('releases/v1.2.4', False, 'Tag version differs')
    notes.unlink()
    guard(tag, False, 'Missing or empty release notes')
    notes.write_text(' \n', encoding='utf-8')
    guard(tag, False, 'Missing or empty release notes')
    notes.write_text('Release notes / 发布说明\n', encoding='utf-8')
    git('commit', '--allow-empty', '-m', 'New commit')
    other_commit = git('rev-parse', 'HEAD')
    guard(tag, False, 'Checked-out source does not match')
    git('checkout', '--detach', commit)
    guard(tag, False, 'does not match the triggering commit', expected=other_commit)
    guard(tag, True, 'Validated', expected=commit)
print(f'{checks} release tag checks passed')
