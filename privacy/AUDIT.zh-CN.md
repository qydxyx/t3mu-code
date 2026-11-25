# 审计记录

审计日期：2026-11-25，北京时间（Asia/Shanghai，UTC+8）。

## 入口 → 处理

| 范围 | 实际入口 | 关闭策略 |
|---|---|---|
| usage / feedback / retry queue / shutdown | apps/server/src/telemetry/AnalyticsService.ts | 服务接口保留，record=false、flush/owner=no-op；删除收集/队列/HTTP 实现 |
| 身份 | serverRuntimeStartup.ts；client-runtime/authorization/remote.ts | 不为 analytics 读取 server owner；客户端不取/不传 owner/device analytics hash |
| server OTLP | shared/otelEnvironment.ts；server Observability.ts、serverLogger.ts | 固定源码禁用，配置解析与真实 exporter 两层防守；本地日志保留 |
| 浏览器 | web/observability/clientTracing.ts；shared/relayTracing.ts；server/http.ts | 不创建客户端 exporter，relay layer 空 tracer，服务端拒绝外发 trace |
| 主动 endpoint Test | server/observability/OtlpEndpointCheck.ts | 不进行任何 HTTP 探测；返回 Unreachable |
| Electron | desktop/app/DesktopObservability.ts | 不创建网络 exporter，原有本地诊断保持 |
| Mobile crash/startup | observe.ts；app.config.ts；mobile/package.json；RenderErrorBoundary.tsx | 无 SDK JS import，native autolink exclude，固定无效 endpoint 额外防守 |
| Mobile relay traces | diagnosticsSetting.ts；tracing.ts；shared/relayTracing.ts | 偏好不可开启、配置不可用、共享实际出口禁用 |
| 认证 SDK | Web/Electron/Mobile ClerkProvider；relay createClerkClient | telemetry=false/disabled=true，不干扰认证请求 |
| 构建采集 | task-cache/runHook.ts、telemetry.ts | 无 watcher、无磁盘队列、无独立子进程 flusher、旧队列不发送 |
| 自部署 infra | relay/task-cache worker；MobileTelemetry；Cache | 移除 Axiom telemetry layer，诊断接收不存储/转发 |
| 外部 coding agents | provider-core/server/instanceEnvironment.ts | 用户 env 合并之后强制常见 opt-out，保留 API key、PATH 等；外部 binary 不承诺完全可控 |

审查了 manifests、依赖/lock、启动服务、子进程环境、匿名反馈、队列、relay、mobile native 配置，以及源码中的 analytics/crash/OTel/HTTP 出口。关键词扫描只用来定位，不当成穷尽性证明。未通过真实 GUI/抓包证明应用完整生命周期零外发。

## 双轴代码审查

比较固定点：`git diff ef4a1643edf72ad119452c82b01c91adbf7b9e64...HEAD`。

Standards：按根 AGENTS.md、CONTRIBUTING.md、产品 analytics 与 testing 文档审查。未改 vendored .repos，未使用云代理或强制重置；本次授权后正常推送功能分支，默认分支不变；保持 Effect 接口和正常网络功能。新增 TypeScript/TSX 经 scoped lint/typecheck。复核发现移动端 trace 配置可用性仍可能显示为开启，已追加提交修正；bootstrap 测试保留对应 filesystem 诊断说明。

Spec：不仅关闭环境变量默认值，而是 collector/no-op 与出口硬门控；没有误删本地资源监控。每日获取/补丁重放在独立 worktree，未经审查的代码/依赖变化先停；冲突或测试失败不晋升候选。第三方二进制、托管服务日志与正常功能数据传输明确排除“完全可控”承诺。

当前 executor 工具没有并行子代理启动能力，因此此处是执行者按两轴进行的自行审查，不冒充独立双代理 review；父代理可对最终 patch 追加独立复核。仓库缺少 docs/agents/issue-tracker.md；未擅自创建外部 issue 或安装 tracker。

测试结果以 `VALIDATION.zh-CN.md` 为准；不提交本机日志。

## ef4a1643 最新基线人工审查

从 c925b9ab198099f67de862ed01701bd1d8809f2b 到 ef4a1643edf72ad119452c82b01c91adbf7b9e64 共六个提交、27 个文件：

- 2c95b69f25：图片段落/截图显示修复。审阅 mobile markdownDocument、shared markdownPipeline、web wordsHast 及测试；只改 AST/显示处理，不新增网络出口。
- 471088cea1：Pi session 切换后的 rewind。审阅 adapter 的 session 文件读取、分支定位、switch_session/fork RPC、错误/中断终止连接处理；这些是现有 coding provider 功能，不是遥测；无新增服务端地址。
- 5f1fcf789a：mobile 空项目 compose 直接打开选择器。审阅导航参数、路由与 native screens 变更。
- c8014ad590：项目名称为空时还原原值，只改输入处理。
- 282a1faea4：分享交接到已有草稿。审阅 IncomingShareProvider、draft flow atom 与附件 import 目标；沿用正常用户分享功能，不添加遥测 SDK/出口。
- ef4a1643ed：上游支持 DO_NOT_TRACK；保留 shared isDoNotTrackSet helper 与 desktop/WSL 转发，但 server analytics 仍是无采集/无队列 no-op，shared/真实 exporter 的源码硬禁用不会改回普通环境开关。

依赖：package/lock 的唯一版本增量是本地 vendored react-native-screens t3.62 → t3.63 及对应 peer snapshot。用 tarfile 只读逐文件比较两份归档、拒绝链接/越界路径；差异仅版本/t3-fork 元数据与三个 iOS header/screen 文件：增加 didAttachToScreen，在 attach 时提前构建 header，避免 push 动画空栏。无新增远程 SDK、依赖或安装脚本。未执行归档内容/原生构建。两份 t3-fork commit：4eb14eff8921798cf0ea1d3f3929e23020465381 → 817fdacc948c5a92458200648b43cf8bd41a1ec7。

## 本轮两轴自审

Standards：保留 Effect service 接口，未引入新的 SDK 或 React effect；Python 工具无第三方运行依赖，patch payload 与维护层独立，提交不含日志、node_modules、git 数据或凭据。额外 metadata 只允许 manifest 精确路径/内容，不能用 privacy/ 通配掩盖 SDK。

Spec：受控 update 固定真实上游/main；源码/lock/config 增量先人工审查，不执行未经审阅的新代码。工作树隔离、失败保持 last-good、重复候选不二次 apply。CI 不使用 pull_request_target，不挂载 secrets/write token，checkout 不持久化凭据，依赖安装禁 lifecycle/pnpmfile。每日流程只读，不自动 push/开 PR/merge；任意运行时代码更新仍需人工适配，这是明确边界而不是宣称全自动合并。普通 git pull 不自动重放 patch；若覆盖边界或出现新源码，CI 门禁失败。

修正：发现把旧独立 kit 原样放入 fork 会被额外文件守卫阻挡，新增精确维护层校验和四个测试；发现重复运行需拒绝已变异 last-good，补生命周期测试。没有可用独立 review 子代理，以上为自审，不冒充独立审查。建议另行配置 GitHub 分支保护，将 Privacy regression / privacy 设为 required，不能仅靠仓库文件阻止管理员绕过/修改守卫。

实际远程 CI 首次 checkout 因 .repos 的不完整嵌套 gitlink 失败；使用上游自身 CI 已用的 sparse checkout 排除 .repos，保持 persist-credentials:false。没有通过持久化 token 或修改 vendored 仓库来绕开错误。
