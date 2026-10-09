# 辅助脚本

在仓库根目录运行。PowerShell 脚本遇错终止；不自动申请管理员权限、不关闭用户程序。

| 脚本 | 用途 | 示例 |
| --- | --- | --- |
| setup-toolchain.ps1 | 下载固定版本便携 llvm-mingw，可指定代理 | `./tools/setup-toolchain.ps1 -Proxy http://host:port` |
| build.ps1 | 编译资源、DLL、路径测试并运行 x64 测试 | `./tools/build.ps1 -Toolchain C:/tools/llvm-mingw` |
| install.ps1 | 核对 PE 位数后复制 DLL，已有 DLL 备份为 .bak | `./tools/install.ps1 -NotepadDirectory C:/Apps/Notepad++` |
| smoke-test.py | 复制宿主到独立测试目录，执行跨进程真实 GUI/API 测试 | `python tools/smoke-test.py --notepad-dir "C:/Program Files/Notepad++"` |
| package.ps1 | 将当前 x64 DLL 及对应完整源码分别打包 | `./tools/package.ps1` |
| prepare-release.ps1 | 校验现有 ZIP、生成哈希、官方列表条目、发布说明与 PR 草稿 | `./tools/prepare-release.ps1` |
| plugin-admin-test.py | 隔离 Debug 宿主中测试真实插件管理器安装、移除和升级 | 见下方 |
| validate-plugin-list.py | 用官方 schema 与 validator 校验本地发布包及名称唯一性 | 见下方 |
| version-bump.ps1 | 默认升级 patch，可选构建打包；current 只读 | `./tools/version-bump.ps1 minor -Build` |
| version-lib.ps1 | 共享版本解析函数 | 由其它脚本加载 |

`build.ps1` 默认自动查找 `.cache/toolchain` 下的工具链；`-Arch` 可选 `x86_64`、`i686`、`aarch64`。只有 x64 自动执行测试。

宿主测试需要 64 位 Python（仅使用标准库），通过 PID 限定窗口并读取测试进程内控件；不扫描或操作用户已有 Notepad++ 实例。测试样例、配置和报告保留在 `build/smoke-*`，可检查后手动清理。

双击目录测试调用系统 Windows PowerShell 的 Shell.Application COM 接口，核对 Explorer 的完整目录位置；仅匹配本次新建的测试路径，完成后关闭测试窗口，不输出其它目录信息。

安装到 Program Files 需要管理员权限。首次安装允许宿主继续运行，下次启动加载；更新已有 DLL 时须先保存文档并关闭对应宿主。

版本命令见 README。`python tests/version_tests.py` 在临时目录验证 CLI，不改工作区版本。打包会比对 DLL ProductVersion 和 `src/version.h`，并创建独立打包目录，防止混入旧文件。

## 发布准备与安装验证

`package.ps1` 核对 DLL FileVersion/ProductVersion，二进制 ZIP 根目录直接放 DLL；源码包排除 Python 缓存。`prepare-release.ps1` 不重新打包，默认生成本仓库作者和下载地址的元数据，标签默认为 `releases/v<版本>`；支持 `-Repository`、`-Author`、`-CompatibleVersions`、`-Tag`。下载地址保留标签中的 `/`，并编码附件名中的特殊字符。上传后使用 `-VerifyPublished` 校验公开下载内容。所有脚本均不上传、提交、创建 Git 标签。

从[官方手册](https://github.com/notepad-plus-plus/npp-usermanual/blob/master/content/docs/plugins.md#test-your-plugins-locally)获取 x64 Debug Notepad++ 和 Debug GUP，解压后运行：

```powershell
python tools/plugin-admin-test.py --debug-exe <Debug-Notepad++.exe路径> --debug-gup <Debug-GUP.exe路径> --old-package <旧版ZIP路径>
```

此测试在 `build/plugin-admin-*` 创建副本，通过仅监听 `127.0.0.1` 的 HTTP 服务下载现有发布 ZIP。验证安装并加载、卸载、旧版更新、旧文件清理和配置保留。隔离副本强制多实例，避免 GUP 重启转到其它编辑器。报告记录所用 ZIP 哈希；公网地址需上传后另行验证。

从 nppPluginList 官方仓库下载 `validator.py`、`pl.schema`、`pl.x64.json`、`requirements.txt` 到 `.cache/release-tools`，在独立 venv 安装官方依赖：

```powershell
python -m venv .cache/release-validator
./.cache/release-validator/Scripts/python.exe -m pip install -r .cache/release-tools/requirements.txt
./.cache/release-validator/Scripts/python.exe tools/validate-plugin-list.py --official-dir .cache/release-tools
```

包装脚本先对当前官方 x64 列表检查名称和下载地址唯一性，再在独立 `build/plugin-list-validation-*` 运行官方 validator，仅验证本次条目，避免下载整个列表。报告记录官方脚本、schema 和列表的哈希。
