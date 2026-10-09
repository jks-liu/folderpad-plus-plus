# folderpad++ 提交官方插件列表

核对日期：2026-10-07。目标仓库：[nppPluginList](https://github.com/notepad-plus-plus/nppPluginList)。

## 收录要求

- 提供公开可直接下载的 ZIP，建议使用 GitHub Release 固定版本附件。
- `folderpad++.dll` 必须位于 ZIP 根目录；`folder-name` 为 `folderpad++`，与 DLL 文件名一致且在列表中唯一。
- JSON 的 `version` 必须与 DLL 的 FileVersion 一致；`id` 是整个 ZIP 的 SHA-256。
- 必填字段：`folder-name`、`display-name`、`version`、`id`、`repository`、`description`、`author`、`homepage`。其中 `repository` 是 ZIP 下载地址。
- 按架构提交：x64 对应 `src/pl.x64.json`，x86 对应 `src/pl.x86.json`，ARM64 对应 `src/pl.arm64.json`；可先仅提交已验证的 x64。
- 确定兼容的 Notepad++ 版本范围，填写 `npp-compatible-versions`，例如 `[最低版本,]`；不应无依据地声明兼容全部版本。
- 提交前验证插件功能及插件管理器的安装、移除、更新。

## 提交步骤

1. 固定正式版本及源码，构建并测试 DLL。
2. 制作 ZIP：根目录放 `folderpad++.dll`，可附 README 和 LICENSE。
3. 上传 GitHub Release，取得固定下载地址；计算 ZIP 哈希：

   ```powershell
   Get-FileHash ./dist/folderpad++-<版本>-x64.zip -Algorithm SHA256
   ```

4. Fork nppPluginList，在对应架构 JSON 中添加元数据。
5. 按官方手册准备隔离便携环境、Notepad++ Debug 及 Debug `GUP.exe`；将修改后的列表放到 `plugins/Config/nppPluginList.json`，通过插件管理器验证安装、移除和更新。
6. 向官方仓库提交 PR，只修改对应 JSON 文件，说明用途、架构及测试结果；处理检查和审核意见。
7. 合并后等待官方列表发布，用户才能在插件管理器中看到。以后更新重复发布和提交流程，更新版本、下载地址、哈希；不要替换已提交哈希的同一下载包。

## 当前准备状态（1.1.1）

- 已修正为根目录 DLL，并生成包含最新修改的 1.1.1 二进制和对应源码包。
- 作者 Jks Liu，主页 `https://github.com/jks-liu/folderpad-plus-plus`；x64 兼容范围保守设为 `[8.9.8.1,]`。
- 23 项功能检查、插件管理器安装/移除/升级、官方 validator 校验通过；详见 [验证记录](validation.md)。
- 用户已公开发布 `releases/v1.1.1`，公网二进制 ZIP 哈希校验通过；官方 JSON 条目已修正下载地址，可用于后续 PR。交付文件和具体操作见 [发布交接](release-preparation.md)。

## 官方依据

- [收录规则及测试流程](https://github.com/notepad-plus-plus/npp-usermanual/blob/master/content/docs/plugins.md#plugin-list)
- [字段定义](https://github.com/notepad-plus-plus/nppPluginList/blob/master/pl.schema)
- [校验脚本](https://github.com/notepad-plus-plus/nppPluginList/blob/master/validator.py)
