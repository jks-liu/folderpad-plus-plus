# GitHub Actions 自动发布

## 作用与入口

工作流位于 [`.github/workflows/release.yml`](../.github/workflows/release.yml)。向 GitHub 推送 `releases/vX.Y.Z` annotated tag 后，自动编译、测试、打包、上传附件并公开正式 Release。普通分支推送、本地创建 tag 不触发发布。

正式发布仅提供 Windows x64。版本以 `src/version.h` 为唯一来源；CI 不修改版本、不提交代码、不创建 tag，也不自动提交 Notepad++ 官方插件列表 PR。

## 首次启用

1. 将工作流、辅助脚本、测试和文档提交并推送至 GitHub。发布 tag 必须指向包含这些文件的提交。
2. 在仓库 **Settings → Actions → General** 确认 Actions 已启用，允许 `actions/checkout`，且仓库或组织策略允许工作流申请 `contents: write`。
3. 使用新的版本号发布。已发布版本保留原 tag 和附件，不移动 tag、不重新上传同名包。

工作流使用 GitHub 托管的 `windows-2022` runner、PowerShell 7、Python、Git 和 GitHub CLI。现有 `setup-toolchain.ps1` 下载固定版本 llvm-mingw，不依赖开发者本机环境。发布步骤使用 GitHub 自动提供的 `GITHUB_TOKEN`，无需个人访问令牌或额外 Secret。

## 日常发布

先完成真实 Notepad++ 功能验证，再准备版本与发布说明。例如发布 `1.2.1`：

```powershell
# 更新 src/version.h，不要求本地编译
./tools/version-bump.ps1 1.2.1

# 编写 docs/releases/1.2.1.md，建议提供中英说明
# 以下假定本次功能代码已提交
git add src/version.h docs/releases/1.2.1.md
git commit -m "Prepare release 1.2.1"
git push

# 创建 annotated tag，只推送本次发布标签
git tag -a releases/v1.2.1 -m "Release 1.2.1"
git push origin releases/v1.2.1
```

打 tag 前确认工作区干净，全部发布内容均在 tag 指向的提交中。不需要手动创建 GitHub Release。

在仓库 **Actions → Release** 查看进度，成功后在 **Releases** 下载附件。也可通过 `gh run list --workflow release.yml` 查看运行状态。

## 校验与执行顺序

| 阶段 | 检查或操作 |
| --- | --- |
| 检出 | 检出触发 tag 的代码，获取完整 Git 历史及 tag；不保留 Git 推送凭据 |
| 校验 | 必须为 annotated tag，严格命名为 `releases/vX.Y.Z`，版本与源码一致，指向当前检出及触发提交，发布说明存在且非空 |
| 编译 | 下载固定版本 llvm-mingw，编译 x64 DLL，运行路径模型测试 |
| 脚本测试 | 在临时仓库中检查版本 CLI 与发布 tag 约束，不修改真实版本或 tag |
| 打包 | 核对 DLL FileVersion/ProductVersion，生成两个 ZIP 和发布材料，校验包内 DLL、PE 位数与哈希 |
| 上传 | 创建草稿 Release，以 `docs/releases/X.Y.Z.md` 为正文，上传全部附件 |
| 公开 | 仅在草稿创建与附件上传命令成功后，将 Release 改为公开正式版本 |

触发器的 `releases/v*.*.*` 是通配符，严格格式由 `tools/validate-release-tag.ps1` 检查。不接受 lightweight tag、前导零、预发布后缀或版本不一致；版本组件范围为 0–65535，与 Windows 版本资源约束一致。

同一 tag 的运行串行执行，不自动取消正在发布的任务；单次运行最多 30 分钟。默认遇错停止；GitHub CLI 失败退出码也显式转为 PowerShell 错误，避免上传失败后继续公开。

## 发布附件

| 附件 | 用途 |
| --- | --- |
| `folderpad++-X.Y.Z-x64.zip` | 二进制包，DLL 位于 ZIP 根目录，适配 Plugins Admin |
| `folderpad++-X.Y.Z-source.zip` | 对应源码、工具、测试、文档和 `.github` 工作流 |
| `SHA256SUMS.txt` | 两个 ZIP 的 SHA-256 |
| `nppPluginList-entry-x64.json` | 官方 x64 插件列表条目；下载地址按实际运行仓库和 tag 生成 |
| `release-manifest.json` | 版本、架构、DLL/ZIP 哈希、ZIP 内容及公网下载校验状态 |

准备脚本还生成 `RELEASE-NOTES.md`（用于正文）和 `NPPPLUGINLIST-PR.md`（官方列表 PR 草稿），工作流不将其作为附件上传。

清单中的 `publicDownloadVerified` 为 `false`，表示尚未执行公网下载比对，不表示包校验失败。发布后提交官方列表前，应下载冻结的 ZIP，对照 `SHA256SUMS.txt` 校验，并使用此次发布的列表条目。如在本地执行 `prepare-release.ps1 -VerifyPublished`，必须使用同一份发布 DLL 和两个 ZIP，不能用重新构建或压缩的文件替代。

## 失败与恢复

| 情况 | 处理方式 |
| --- | --- |
| 校验、测试、编译或打包失败 | 查看失败步骤。网络或 runner 临时故障可选择 **Re-run all jobs**；需要改代码或版本时，提交修复并创建新版本、新 tag |
| 创建 Release 前失败 | 没有创建 Release；临时故障解决后可重跑 |
| 上传中途失败 | 可能留下草稿和部分附件。确认尚未公开后，删除本次失败草稿再重跑；不删除 Git tag，不混用旧附件 |
| 上传完成、公开步骤失败 | 检查草稿正文、五个附件及校验和，完整后可手动公开；若选择重新构建，先删除未公开草稿再重跑 |
| 已存在 Release | 创建步骤失败，不覆盖已有 Release 或附件。成功发布后无需重跑 |
| 权限错误（例如 HTTP 403） | 检查仓库或组织 Actions 策略是否允许 `contents: write` |

公开步骤发生网络故障时，服务端可能已完成公开，以 GitHub 页面实际状态为准。恢复前必须确认是未公开草稿，避免误删正式版本。

CI 执行模型及脚本测试，不覆盖真实 Notepad++ GUI、插件管理器安装/升级等验证；这些仍在打 tag 前完成，方法见 [脚本说明](../tools/README.md) 和 [验证记录](validation.md)。GitHub 首次真实运行还将验证托管 runner、下载网络和仓库权限。

## 本地检查与参考

```powershell
# 只读检查已有 tag；当前 HEAD 必须与该 tag 一致
./tools/validate-release-tag.ps1 -Tag releases/v1.2.0

# 临时仓库中的约束测试
python tests/release_tag_tests.py
python tests/version_tests.py

# 复现构建及打包阶段
./tools/build.ps1
./tools/package.ps1
./tools/prepare-release.ps1
```

机制依据：[GitHub 工作流语法](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)、[actions/checkout](https://github.com/actions/checkout)、[gh release create](https://cli.github.com/manual/gh_release_create)、[gh release edit](https://cli.github.com/manual/gh_release_edit)。

