# 任务与进度

## 当前任务（2026-11-25 / 双击安装与 UAC）

提供双击和命令行安装入口。自动定位 Notepad++ 并复制 DLL，写入权限不足时请求 UAC，升级遇到运行中的宿主时提示用户保存并退出。

## 当前进度

- 已实现 `tools/Install.cmd` 和 `tools/install.ps1`，x64 二进制包包含双击入口，保留根目录 DLL。
- 解压安装、真实宿主加载、运行中拒绝更新、替换和备份、PE 位数与文件占用检查通过。写入拒绝、UAC 参数和返回结果通过隔离测试，Windows 提权同意界面留待实际安装。
- 实现与本地打包已完成。二进制包位于 `dist/folderpad++-1.3.0-x64.zip`，验证报告位于 `build/install-check-20261125-052633/result.json`。此前文件列表改动已记录在 `docs/validation.md`。
