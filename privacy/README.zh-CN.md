# 硬禁遥测与受控上游更新

本 fork 已在源码中禁用已审查的 usage analytics、crash/error reporting、OTel/relay tracing、Clerk telemetry、构建事件采集/队列/子进程 flusher；普通环境变量或设置不能重新打开。入口明细见 [AUDIT](AUDIT.zh-CN.md)，实际验证见 [VALIDATION](VALIDATION.zh-CN.md)。

- 用户仓库：https://github.com/qydxyx/t3mu-code ，默认分支 main。
- 真实 fork parent/source：https://github.com/pingdotgg/t3code ，追踪 main（不是根据名字猜测）。
- 审查基线：`ef4a1643edf72ad119452c82b01c91adbf7b9e64`。
- `no-telemetry.patch` 只含禁遥测源码/契约测试/相关文档；维护脚本和 workflows 不递归打入 patch。
- `manifest.json` 固定审查基线、patch 和维护工具的 SHA256、每个 patched file 最终 SHA256；这些是回归/意外漂移守卫，不是防恶意管理员篡改的签名。

## 干净 clone 后验证（Linux，Python 3.10+、Node 26.13.1、pnpm 12.14.0）

```bash
git clone --branch privacy/no-telemetry-sync https://github.com/qydxyx/t3mu-code.git
cd t3mu-code
python3 privacy/check.py
python3 -m unittest discover -s privacy -p 'test_*.py' -v
# 先审查 manifest/lock；不能把拉到新代码等同于允许执行它的 install scripts。
npm_config_ignore_scripts=true pnpm install --frozen-lockfile --ignore-scripts --ignore-pnpmfile
python3 privacy/verify.py
```

代码合并 main 后可改为 clone 默认分支；不要对已打补丁的 fork 再运行 apply.py。
首次在**独立干净上游基线 checkout**重放可运行：

```bash
python3 /path/to/fork/privacy/apply.py /path/to/clean-upstream-checkout
```

apply 要求源树干净且已审查；重复应用、冲突、未知源码/锁文件/依赖变化均拒绝。apply 不安装依赖。

## 后续正确入口：先获取、审查、隔离重放、验证，再晋升

```bash
# 在 fork 根目录执行；不修改当前分支/工作区，不 push/merge。
python3 privacy/update.py
# 首次只验证已审查基线（离线 fetch，安装仍需要依赖缓存/网络）：
python3 privacy/update.py --baseline
# 父代理/本机工作日例程可用精确入口；只传实际 clone 与独立状态目录：
python3 privacy/daily.py --repo /path/to/t3mu-code --state /path/to/t3mu-code-privacy-state
```

update 默认状态目录为 clone 同级的 `<clone-name>-privacy-state`，可用 `--repo`、`--state` 指定。使用文件锁防并发，目标 URL/分支固定于 manifest；不直接 daily merge main，不 reset、不强推。不依赖任何 `/workspace` 路径或外置 kit。

- fetch 上游 → 将所有非普通 docs/*.md 的树内容/模式与审查基线比较。任何运行代码/依赖/lock/配置/新 SDK/新脚本变化返回 **42 REVIEW_REQUIRED**；安装和 candidate JS 测试之前停止。
- 通过审查门禁才创建独立 detached worktree，干净 apply，使用 `--frozen-lockfile --ignore-scripts --ignore-pnpmfile` 安装，运行合同测试、scoped lint、10 个相关包 typecheck。
- 全通过才原子替换 `state/current` symlink；源码/测试/安装/补丁失败不替换上次通过的源码，不静默跳过。`last-fetched.json` 记录观察到的 commit，`last-good.json` 记录已通过版本。重复候选只重验，不重复 apply/提交。
- `current` 是**已验证源码**，不是已构建/部署的客户端。切勿直接在 state 下手动改文件；也不会自动安装桌面/移动 App。
- 正常 `git pull upstream main` 或网页 Sync fork **不会自动重放外置 patch**。请勿将其当受支持更新入口；若自行 merge 上游，随后必须通过 privacy guard/CI。边界被恢复、新代码未审阅或新出口文件出现时，检查会失败，需人工处理。

## GitHub 持久机制与启用时间

- `.github/workflows/privacy.yml`：普通 push / PR / 手动触发，依赖安装前检查来源与边界，之后跑契约测试、lint、typecheck。
- `.github/workflows/privacy-sync.yml`：手动和工作日 **北京时间 09:00（UTC+8）** 获取上游、隔离重放；GitHub 可能延迟调度。遇代码变化失败并产出 `privacy-upstream-review` 文本 artifact，供人工审查。**只读权限，不自动 push、PR 或 merge，不自动执行未审阅的新代码**。
- action 引用固定 commit；checkout `persist-credentials:false`，无 secrets，`contents:read`，不用 `pull_request_target`，不复用共享依赖缓存。未配置仓库分支保护/required status（需管理员操作）；仅推功能分支不改变 main。
- **schedule 只有流程合并到默认 main 且 Actions 启用后才生效**。本交付不擅自 merge；功能分支 push 可触发回归流程，不等于 daily 已启用。
- 避免和本机例程重复执行：由父代理在确认 main 上 daily 已实际启用后停用本机例程；本次工具未创建/修改例程。
- Actions runner 不持久保存 worktree/current；每次从 GitHub 中已通过审查的 fork 与 patch 重建。上次通过版本始终留在分支历史；状态目录只对同一台本机更新器持久。不会把 runner 临时目录误称为长期部署。

## 遇 REVIEW_REQUIRED 的人工维护步骤

1. 固定 fetch 得到的 commit。审阅旧 reviewed_base 到目标 commit 的完整源码、启动/子进程/队列/出站调用、所有 manifest/lock/config 和 vendored 归档实际内容；不是搜索几个关键词后直接放行。
2. 在新分支/独立 worktree 从该 commit 重放旧 patch，人工解决冲突；保留业务代码和禁遥测契约，必要时扩充新 SDK/新出口防线。禁用实现应先补可复现测试。
3. 提交**仅 payload**的源码 commit；在维护提交中更新 reviewed_base、payload commit、patch、patched_files、kit_hashes、maintenance_files。可用 `python3 privacy/refresh.py --reviewed-base <sha> --payload-commit <sha> --review-note <已写入privacy的审查记录文件名>`，这是**人工审阅后**操作，CI/每日脚本绝不调用它。
4. 跑 Python 守卫/生命周期测试、`check.py`、`verify.py`，以及 `update.py --baseline` 从干净基线真实重放。正常 push 新分支供 review；不自动 merge。不要只更新 hash 来绕过失败。

## 保留功能与边界

保留模型 API、认证、版本/更新检查、Git、正常远程会话、用户主动分享、反馈本地报告、本地日志/资源诊断。Publish agent activity 功能仍可给 relay 发标题/状态（用户功能，不是后台 telemetry，可另行关闭）。不是“零网络”模式；官方托管 relay/模型服务端、外部 CLI/MCP/插件/二进制和系统崩溃报告不受此源码完全控制。常见 opt-out 会在子进程合并环境后强制设置，但不能保证第三方全部尊重。

原生 mobile 必须重新 prebuild/build，OTA JS 更新不能移除已内置的 native SDK。官方更新安装包可能覆盖 fork；本次保留更新检测，不宣称自动安装官方版本还能保留 fork 修改。

没有用正则扫描承诺穷尽任意未来网络出口。守卫对新源码/依赖采取停更待审；运行期网络限制如有更高要求，需单独做沙箱/防火墙和全生命周期抓包测试。`--ignore-scripts` 也不是沙箱。源码 MIT 许可允许此修改，T3 名称/商标不随源码许可授权，未擅自重新品牌发布。
