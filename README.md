# folderpad++

Notepad++ 原生插件：在左侧停靠面板中，用文件夹标签组织**已经打开的文档**。添加文件夹只记录路径，不扫描目录，也不批量打开文件。

## 使用

1. 将 `folderpad++.dll` 放到 Notepad++ 安装目录下的 `plugins/folderpad++/`，重新启动 Notepad++。
2. 打开 **插件 → folderpad++ → Show / Hide panel | 显示 / 隐藏面板**。
3. 点击“添加文件夹…”，默认定位到当前活动文件所在目录；未保存文档使用系统默认位置。选择目录后，其中已打开的文件会自动出现在对应标签。
4. 点击列表中的文件激活文档；键盘选择后按 Enter 或空格也可以激活。
5. 在 **插件 → folderpad++ → Settings... | 设置…** 中选择跟随 Notepad++、English 或简体中文，点击“确定”保存；“取消”不改变设置。
6. **右键文件夹标签**直接打开文件选择窗口，起始目录为该标签对应文件夹，可选择一个或多个文件交给 Notepad++ 打开。右键未选中的标签也以鼠标所在标签为准；右键空白区域无操作。“其它”没有绑定目录，使用系统文件选择窗口的默认位置。标签获得焦点后，也可按 Shift+F10 打开文件。
7. **左键双击文件夹标签**在资源管理器中打开该目录；“其它”和标签空白区域不执行此操作。

文件夹嵌套时，文件归入最深的目录。未匹配文件与未保存文档位于“其它”。列表显示相对路径；“其它”显示完整路径。移除标签只取消分组，不关闭、删除或修改文档。文件在两个视图中打开时只显示一次，点击时优先使用当前视图。

文件夹列表、语言和面板可见性保存到 Notepad++ 插件配置目录的 `folderpad++.ini`。面板停靠位置由 Notepad++ 管理。保留暂时不可访问的目录，不会为验证目录而访问网络。路径采用 Windows 大小写不敏感的词法匹配，不解析符号链接或目录联接。

## 构建与验证

要求 Windows、PowerShell 7 和 llvm-mingw。默认构建 x64，与本机 Notepad++ 位数一致。工具链仅下载到仓库 `.cache`，不修改系统 PATH。

```powershell
# 已有工具链时无需下载；代理地址按实际环境填写
./tools/setup-toolchain.ps1 -Proxy http://proxy-host:port
./tools/build.ps1
# 或指定现有工具链
./tools/build.ps1 -Toolchain C:/tools/llvm-mingw

# 在独立的便携实例内测试，不操作已有编辑器
python tools/smoke-test.py

# Program Files 目录需要管理员 PowerShell；下次启动生效
# 更新已有插件时，先自行保存文档并关闭 Notepad++
./tools/install.ps1

# 打包 x64 DLL 和对应源码
./tools/package.ps1
```

输出：`build/x86_64/folderpad++.dll`。路径核心测试随构建运行；宿主测试的配置与 JSON 报告保留在 `build/smoke-时间/`。

可用 `-Arch i686` 或 `-Arch aarch64` 交叉编译其它位数；这些产物需要在对应宿主上自行验证。正式发布仅提供 Windows x64；最低支持基线为已验证的 Notepad++ 8.9.8.1，更早版本暂不声明支持。

二进制 ZIP 根目录直接包含 `folderpad++.dll`，适配 Plugins Admin；手动安装时应将 DLL 放入 `plugins/folderpad++/`。发布准备运行 `./tools/prepare-release.ps1`，生成 SHA-256、官方列表条目、发布说明及 PR 草稿；公开上传后运行 `./tools/prepare-release.ps1 -VerifyPublished` 验证下载字节。脚本不上传或提交。

## 版本升级

使用 PowerShell 7，无需 npm，在项目目录运行：

```powershell
# 默认 patch，不构建：例如 1.0.1 -> 1.0.2
./tools/version-bump.ps1

# 升级、编译 DLL、运行核心测试、生成二进制和源码 ZIP
./tools/version-bump.ps1 patch -Build

./tools/version-bump.ps1 minor
./tools/version-bump.ps1 major
./tools/version-bump.ps1 2.0.0

# 显式跳过构建（默认行为）
./tools/version-bump.ps1 patch -NoBuild

# 只读显示源码版本，不改文件
./tools/version-bump.ps1 current
```

唯一版本来源为 `src/version.h`；关于窗口、DLL FileVersion/ProductVersion 和打包名称均从中派生。minor 清零 patch，major 清零 minor/patch。仅接受稳定版 `X.Y.Z`，每段 0–65535（Windows 版本资源限制），不接受前导零或预发布后缀。

`-Build` 与 `-NoBuild` 不能同时使用。构建失败保留已更新的版本；修复后运行 `tools/build.ps1` 和 `tools/package.ps1`，不必再次 bump。脚本不安装、不创建 Git 标签、不提交。DLL 版本与源码不同时，打包会报错，防止发布旧 DLL。`current` 不要求已有构建产物。

语言选项位于插件自己的独立“设置…”窗口，面板中不再显示语言下拉框。原有配置直接沿用，无需迁移。即使面板隐藏，也可以从插件菜单打开设置。

## 开发资料

- [当前计划与进度](docs/plan.md)
- [关键修改](docs/changes.md)
- [问题记录](docs/issues/)
- [经验总结](docs/lessons/)
- [脚本说明](tools/README.md)
- [官方插件列表提交指南](docs/official-plugin-list.md)
- [1.1.1 发布说明](docs/releases/1.1.1.md)

原生 API 依据 [Notepad++ 插件通信文档](https://npp-user-manual.org/docs/plugin-communication/) 和官方 [插件模板](https://github.com/npp-plugins/plugintemplate)。接口头文件的来源、版本及许可见 [vendor/README.md](vendor/README.md)。项目许可：GPL-3.0-or-later。
