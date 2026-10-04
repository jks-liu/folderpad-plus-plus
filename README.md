# folderpad++

Notepad++ 原生插件：在左侧停靠面板中，用文件夹标签组织**已经打开的文档**。添加文件夹只记录路径，不扫描目录，也不批量打开文件。

## 使用

1. 将 `folderpad++.dll` 放到 Notepad++ 安装目录下的 `plugins/folderpad++/`，重新启动 Notepad++。
2. 打开 **插件 → folderpad++ → Show / Hide panel | 显示 / 隐藏面板**。
3. 点击“添加文件夹…”，选择要组织的目录。目录中的已打开文件会自动出现在对应标签。
4. 点击列表中的文件激活文档；键盘选择后按 Enter 或空格也可以激活。
5. 在语言下拉框选择跟随 Notepad++、English 或简体中文。

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

可用 `-Arch i686` 或 `-Arch aarch64` 交叉编译其它位数；这些产物需要在对应宿主上自行验证。当前发布验证针对 Windows x64 / Notepad++ 8.9.8.1。

## 开发资料

- [当前计划与进度](docs/plan.md)
- [关键修改](docs/changes.md)
- [问题记录](docs/issues/)
- [经验总结](docs/lessons/)
- [脚本说明](tools/README.md)

原生 API 依据 [Notepad++ 插件通信文档](https://npp-user-manual.org/docs/plugin-communication/) 和官方 [插件模板](https://github.com/npp-plugins/plugintemplate)。接口头文件的来源、版本及许可见 [vendor/README.md](vendor/README.md)。项目许可：GPL-3.0-or-later。
