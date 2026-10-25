# 发布记录

## v6.5.8

- 正式发布：[PR #132](https://github.com/YohakuSama/loonkit/pull/132)，运行时提交 `3366ee77d3e1ee44788e60ba1381e976406f4596`。
- 测试渠道：[PR #131](https://github.com/YohakuSama/loonkit/pull/131)，版本 v6.5.9-beta.1。
- [正式 CI](https://github.com/YohakuSama/loonkit/actions/runs/40157438384) 与 [Beta CI](https://github.com/YohakuSama/loonkit/actions/runs/40157430514) 通过。
- 正式入口实际下载 SHA256：`3995be763a1ee52f70fca9b86a303c2842c559fae8c45cefa72f286c6a741715`。
- 本地与 CI 覆盖 120 项 Python、12 项 Node 测试、远程资源和历史版本校验。
- 上游权限兼容更新：[正式 PR #135](https://github.com/YohakuSama/loonkit/pull/135) 与 [测试 PR #134](https://github.com/YohakuSama/loonkit/pull/134)，两渠道 CI 通过。
- [上游运行](https://github.com/YohakuSama/loonkit/actions/runs/40159737181)完成来源审阅，本轮没有合格新增。
- 同次运行成功创建临时候选分支、运行[对应提交的 Beta CI](https://github.com/YohakuSama/loonkit/actions/runs/40159746722)并清理分支。当前仓库采用候选分支与人工 PR 模式。
- 回滚：[v6.5.7 固定配置](https://raw.githubusercontent.com/YohakuSama/loonkit/a67828e6efbe6c4f6e19be4d78abfe28b1cb2953/LoonKit.lcf)。

[版本校验](./RELEASE_CHECKSUM_v6.5.8.md) · [维护流程](./MAINTAINING.md) · [上游更新](./BETA_UPSTREAM_AUTOMATION.md)
