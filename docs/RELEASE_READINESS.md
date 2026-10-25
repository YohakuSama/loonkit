# 发布记录

## v6.5.8

- 正式发布：[PR #132](https://github.com/YohakuSama/loonkit/pull/132)，运行时提交 `3366ee77d3e1ee44788e60ba1381e976406f4596`。
- 测试渠道：[PR #131](https://github.com/YohakuSama/loonkit/pull/131)，版本 v6.5.9-beta.1。
- [正式 CI](https://github.com/YohakuSama/loonkit/actions/runs/40157438384) 与 [Beta CI](https://github.com/YohakuSama/loonkit/actions/runs/40157430514) 通过。
- 正式入口实际下载 SHA256：`3995be763a1ee52f70fca9b86a303c2842c559fae8c45cefa72f286c6a741715`。
- 本地与 CI 覆盖 117 项 Python、12 项 Node 测试、远程资源和历史版本校验。
- [上游运行](https://github.com/YohakuSama/loonkit/actions/runs/40157438559)的来源审阅阶段成功：87 条来源、33 组，本轮没有合格新增。
- 发布器集成检查在创建 PR 时收到 403；仓库的 Actions 创建与批准 PR 开关当前关闭，等待开启后重试。
- 回滚：[v6.5.7 固定配置](https://raw.githubusercontent.com/YohakuSama/loonkit/a67828e6efbe6c4f6e19be4d78abfe28b1cb2953/LoonKit.lcf)。

[版本校验](./RELEASE_CHECKSUM_v6.5.8.md) · [维护流程](./MAINTAINING.md) · [上游更新](./BETA_UPSTREAM_AUTOMATION.md)
