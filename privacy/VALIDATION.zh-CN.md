# 验证记录

2026-11-25，北京时间（Asia/Shanghai，UTC+8）。审查基线 `ef4a1643edf72ad119452c82b01c91adbf7b9e64`，payload commit `1f9d9c8d4d112d7626bd89d97f6c18bedfacc83a`。

## 实际通过

- Box 上使用官方 Node **26.13.1** Linux x64，下载后与官方 SHASUMS256 校验；pnpm **12.14.0**。没有更改用户电脑。
- 当前 payload 与独立干净上游 worktree 均通过：**16 个测试文件 / 203 个测试**，包含 11 个无遥测契约文件，以及最新上游 Pi rollback、shared/mobile/web markdown、desktop WSL 回归。
- 修改的 TypeScript/TSX scoped lint 通过。
- **10 个包** `effect-tsgo tsrs --noEmit` 通过：shared、provider-core、client-runtime、server、web、desktop、mobile、relay、task-cache、provider-pi。输出包含仓库既有 Effect schema brand suggestions，退出码为 0；不将它们隐藏为“没有任何诊断”。
- Python **19 个**守卫/维护层/更新器生命周期测试通过：普通 docs 放行、运行时代码/新 SDK/依赖/lock/隐藏配置/可执行或 symlink Markdown 阻断、维护层精确匹配、拒绝额外 SDK、重复候选不二次 apply、不晋升失败候选、拒绝变异 last-good。
- 真实 `update.py --baseline` 从干净 ef4a 基线创建独立 worktree，干净 apply、禁 lifecycle 安装、完整上述检查后才晋升 current。并非复用手改的旧 c925 结果。
- 真实负例：把 server AnalyticsService 临时换回未补丁上游实现，`privacy/check.py` 非零并指出 Patched boundary changed；新增未知 collector 出口文件也非零。负例文件已还原/移除；现有边界再次通过。
- 官方 actionlint **1.7.12** 两份 workflow 校验通过（下载包 SHA256 校验），Python 编译、`git diff --check`（排除 patch 数据文件固有的上下文空白；patch 由真实 apply 校验）通过；actions/checkout、setup-node、upload-artifact 固定 commit。

## 干净 clone 与交付时上游继续前进

本地通过普通 `git clone --no-local` 得到独立完整 clone（不依赖旧 kit 目录），preflight 与全部 19 个 Python 测试通过。实际默认 updater 从真实上游 fetch 后观察到 `91f0b32e2db2cb8abca5fdd33c33609a0f57b15e`：比本次人工审查的 ef4a 又多三个提交（device 错误 Unicode、Pi 后台 subagent、删除 thread history），涉及 19 个运行/测试文件。门禁真实返回 **42**，在创建候选/安装新依赖/执行新代码之前停止，并成功生成只读 review report。

本次交付已人工审阅并覆盖用户指定的 ef4a 增量，不冒称后续 91f0 的业务/数据库改动也已审查通过；那一批由后续维护按 AUDIT 流程处理。上游持续变化是设计中必须 fail-closed 的场景，不自动放宽 allowlist、不为追上移动目标无限扩展此次修改。

## 安装安全与未运行项

本轮 ef4a 的依赖安装明确使用 `--frozen-lockfile --ignore-scripts --ignore-pnpmfile` 和 npm_config_ignore_scripts=true；先人工审阅完整源码与 lock/本地 native tgz 增量。早先 c925 探索阶段曾因 pnpm exec 自动触发生命周期/prepare，这不是本轮安全重放命令，不能把整个历史描述成从未执行过脚本。

未运行完整 monorepo 全套 checks、浏览器端 e2e、桌面打包、iOS/Android 原生构建、生产部署、完整生命周期抓包或外部二进制行为审计。未配置 GitHub 分支保护；管理员仍可修改/绕过守卫。Actions 的实际远程运行状态以 GitHub 为准，不能把本机 actionlint 通过当作远程 CI 已绿；schedule 必须合并默认分支后才启用。
