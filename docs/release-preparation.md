# 1.1.1 发布交接

## 准备结果

- 发布仓库：https://github.com/jks-liu/folderpad-plus-plus
- 版本及 Git 标签：`1.1.1` / `releases/v1.1.1`；作者：Jks Liu。
- 仅 x64；兼容范围 `[8.9.8.1,]`，最低支持基线为已验证的稳定宿主，更早版本暂不声明支持。
- DLL 功能、插件管理器安装/移除/旧版升级、官方列表格式/哈希/版本/唯一性检查通过，详见 [验证记录](validation.md)。
- 用户已创建标签并公开发布 [Release](https://github.com/jks-liu/folderpad-plus-plus/releases/tag/releases/v1.1.1)，二进制和源码 ZIP 已上传。本次标签修正仅更新文档、生成脚本与提交元数据，不重新打包或替换公开附件。

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

1. `releases/v1.1.1` 标签、Release 和两个 ZIP 已发布；后续文档修正单独提交，不移动标签或替换冻结包。
2. Release 说明可使用 `dist/RELEASE-NOTES.md`；`SHA256SUMS.txt` 可作为额外附件上传。
3. 已运行 `./tools/prepare-release.ps1 -VerifyPublished`，公开二进制 ZIP 与本地冻结包哈希一致，清单中的 `publicDownloadVerified` 为 true。
4. Fork nppPluginList，将完整条目插入最新 `src/pl.x64.json` 的合适位置，仅修改该 JSON；重新核对是否有名称冲突，提交 PR 并使用准备好的说明。
5. 处理官方检查和审核意见，等待合并及包含新条目的官方列表发布。

实际下载地址：
`https://github.com/jks-liu/folderpad-plus-plus/releases/download/releases/v1.1.1/folderpad%2B%2B-1.1.1-x64.zip`

本地安装测试使用仅监听 loopback 的 HTTP 服务；公网下载由步骤 3 单独核对。若 ZIP 有任何变化，需同步更新哈希、条目和验证结果。

## 重新准备

入口：`tools/build.ps1` → `tools/package.ps1` → `tools/prepare-release.ps1`。复现宿主、插件管理器和官方 validator 测试的方法见 [脚本说明](../tools/README.md)。已发布源码包保留原发布快照；本次文档及标签生成脚本修正另行提交，不重打已发布 ZIP。
