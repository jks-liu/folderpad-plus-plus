# 1.1.1 发布交接

## 准备结果

- 发布仓库：https://github.com/jks-liu/folderpad-plus-plus
- 版本及预定 Git 标签：`1.1.1` / `v1.1.1`；作者：Jks Liu。
- 仅 x64；兼容范围 `[8.9.8.1,]`，最低支持基线为已验证的稳定宿主，更早版本暂不声明支持。
- DLL 功能、插件管理器安装/移除/旧版升级、官方列表格式/哈希/版本/唯一性检查通过，详见 [验证记录](validation.md)。
- 工作区尚未提交、打标签或推送；未公开发布 Release，未提交 nppPluginList PR。

## 本地交付（dist）

| 文件 | 用途 |
| --- | --- |
| `folderpad++-1.1.1-x64.zip` | 发布二进制包，DLL 位于根目录 |
| `folderpad++-1.1.1-source.zip` | 对应源码及构建工具 |
| `SHA256SUMS.txt` | 两个 ZIP 的最终哈希 |
| `RELEASE-NOTES.md` | 中英发布说明 |
| `nppPluginList-entry-x64.json` | 加入官方 x64 列表的完整条目 |
| `NPPPLUGINLIST-PR.md` | 官方列表 PR 草稿 |
| `release-manifest.json` | DLL/ZIP 哈希、版本、架构、ZIP 内容及公开下载状态 |

二进制包 SHA-256：`18630bf6de8d2b51917c75a3d6822ec43d7f9adddccb81542140a3d345b3841a`。上传应使用此冻结包，不重新压缩。

## 发布时剩余操作

1. 审阅并提交发布相关源码和文档，保留用户已有 `folderpad++prompts.md` 修改的独立处理；创建 `v1.1.1` 标签并推送对应提交。
2. 在 GitHub 创建对应 Release，使用 `dist/RELEASE-NOTES.md`，上传二进制 ZIP、源码 ZIP 和 `SHA256SUMS.txt`。
3. 上传后运行 `./tools/prepare-release.ps1 -VerifyPublished`；脚本核对下载字节与本地 ZIP 的哈希，成功后清单中的 `publicDownloadVerified` 为 true。
4. Fork nppPluginList，将完整条目插入最新 `src/pl.x64.json` 的合适位置，仅修改该 JSON；重新核对是否有名称冲突，提交 PR 并使用准备好的说明。
5. 处理官方检查和审核意见，等待合并及包含新条目的官方列表发布。

预定下载地址：
`https://github.com/jks-liu/folderpad-plus-plus/releases/download/v1.1.1/folderpad++-1.1.1-x64.zip`

本地测试使用仅监听 loopback 的 HTTP 服务，尚不能证明此公网地址可下载。发布后必须完成步骤 3；若 ZIP 有任何变化，需同步更新哈希、条目和验证结果。

## 重新准备

入口：`tools/build.ps1` → `tools/package.ps1` → `tools/prepare-release.ps1`。复现宿主、插件管理器和官方 validator 测试的方法见 [脚本说明](../tools/README.md)。源码包与二进制包均由当前工作区生成，提交后可对照源码 ZIP 核对发布提交。
