# 辅助脚本

在仓库根目录运行。PowerShell 脚本遇错终止；不自动申请管理员权限、不关闭用户程序。

| 脚本 | 用途 | 示例 |
| --- | --- | --- |
| setup-toolchain.ps1 | 下载固定版本便携 llvm-mingw，可指定代理 | `./tools/setup-toolchain.ps1 -Proxy http://host:port` |
| build.ps1 | 编译资源、DLL、路径测试并运行 x64 测试 | `./tools/build.ps1 -Toolchain C:/tools/llvm-mingw` |
| install.ps1 | 核对 PE 位数后复制 DLL，已有 DLL 备份为 .bak | `./tools/install.ps1 -NotepadDirectory C:/Apps/Notepad++` |
| smoke-test.py | 复制宿主到独立测试目录，执行跨进程真实 GUI/API 测试 | `python tools/smoke-test.py --notepad-dir "C:/Program Files/Notepad++"` |
| package.ps1 | 将当前 x64 DLL 及对应完整源码分别打包 | `./tools/package.ps1` |

`build.ps1` 默认自动查找 `.cache/toolchain` 下的工具链；`-Arch` 可选 `x86_64`、`i686`、`aarch64`。只有 x64 自动执行测试。

宿主测试需要 64 位 Python（仅使用标准库），通过 PID 限定窗口并读取测试进程内控件；不扫描或操作用户已有 Notepad++ 实例。测试样例、配置和报告保留在 `build/smoke-*`，可检查后手动清理。

安装到 Program Files 需要管理员权限。首次安装允许宿主继续运行，下次启动加载；更新已有 DLL 时须先保存文档并关闭对应宿主。
