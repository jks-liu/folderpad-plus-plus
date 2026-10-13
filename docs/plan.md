# 任务与进度

## 当前任务（2026-10-12 / GitHub 自动发布）

用户要求推送 releases/vX.Y.Z annotated tag 后自动编译、发布，并提供详细简练的中文 Markdown 文档。

## 当前进度

- 已新增 .github/workflows/release.yml，使用 Windows runner 复用工具链、x64 编译与打包脚本；附件上传到草稿成功后再公开。
- 已新增 tools/validate-release-tag.ps1 和隔离测试，检查 tag 类型、严格格式、版本、提交与非空发布说明。
- 源码包纳入 .github；新增 docs/automatic-release.md，README 与脚本说明已链接。
- 已完成：actionlint/PowerShell 语法检查、15 项 tag 校验、17 项版本 CLI 测试、16 项模型测试，以及隔离 x64 构建、打包、哈希和源码文件检查。证据见 docs/validation.md。
- 已更新修改记录、问题记录和经验记录；中文操作文档包含首次启用、日常发布、附件和失败恢复。
- 本地实现与验证已完成。下一步是提交并推送这些修改；首次实际 GitHub 发布需要新版本号、新发布说明和新 annotated tag，不应重发既有 1.2.0。

## 交接约束

- 当前源码版本为 1.2.0；已有 releases/v1.1.1 和 releases/v1.2.0。本次不修改版本、不移动 tag、不替换既有发布附件。
- 打包验证必须在临时副本执行，避免覆盖工作区 dist 中既有冻结包。
- 本次不新建正式发布、不推送远端；GitHub 实际运行待提交工作流后由下一个新版本 tag 触发。
- 正式发布仅 x64；真实 Notepad++ GUI、Plugins Admin 测试仍在打 tag 前完成。
