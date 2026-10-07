# 任务与进度

## 当前任务（2026-10-07 / 1.1.1 发布准备）
完成本地发布准备，公开上传与官方 PR 为后续发布操作。

## 已完成
- 版本升级到 1.1.1；添加文件夹默认使用当前活动文件目录。
- ZIP 根目录直接包含 DLL；打包核对 FileVersion/ProductVersion，源码排除 Python 缓存。
- 发布说明、SHA-256、官方列表 JSON、发布清单及 PR 草稿由 tools/prepare-release.ps1 生成。
- 16 项路径检查、17 项版本 CLI 检查、23 项真实宿主功能检查通过。
- 插件管理器安装、移除、从 1.1.0 升级及配置保留通过；官方 validator/schema 通过，名称及下载地址未与当前 x64 列表冲突。
- 测试报告见 docs/validation.md；用户已有 folderpad++prompts.md 修改未改动。

## 交付状态
- 发布源码包、二进制包和提交元数据位于 dist；最终二进制哈希与安装测试及官方校验所用包一致。
- 交付入口：docs/release-preparation.md，提交要求：docs/official-plugin-list.md。

## 后续发布操作
尚未提交、打标签、推送、公开上传或提交官方 PR。发布仓库 https://github.com/jks-liu/folderpad-plus-plus，作者 Jks Liu；预定标签 v1.1.1。
上传冻结包后运行 tools/prepare-release.ps1 -VerifyPublished，确认公网下载字节；再提交 src/pl.x64.json 条目。

## 约束
只交付已验证 x64，最低支持基线 Notepad++ 8.9.8.1；不宣称更早宿主、x86、ARM64 可用。插件不扫描目录，以已打开 buffer 为数据源；嵌套目录最长匹配，双视图去重，移除标签不关闭文件。不操作用户已有宿主。
