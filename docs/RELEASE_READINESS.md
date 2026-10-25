# 发布记录

## v7.0.3

- 正式配置包含 39 个策略组、43 份固定 `.lsr` 订阅、196,565 条规则；图标集中在 `icons/`。
- 43 份订阅及图标使用同一冻结资产提交：`d82214d057b27a68d6b9c07c61fb126a69adc903`。
- `build/release_manifest.json` 登记各文件策略归属、数量、来源集合和 SHA256，`release/SHA256SUMS.v7.0.3` 登记正式配置摘要。
- 归档 v7.0.0 正式配置与元数据到 `build/baselines/v7.0.0/`，DNS、TUN、现有广告拦截及诊断插件保持不变。

## v7.0.0

- 正式版与历史 v6.5.10 基线独立管理；订阅标签统一为正式标识。
- 完整性校验覆盖配置、清单、校验和、规则资源及原生规则语法。
- GitHub Release 使用主分支通过 CI 的精确提交发布。

## v6.5.10 · Bing 节点测速候选（未验收，不自动推广）

- 已更新主配置三个测速 URL 为 `http://www.bing.com`；保留互联网直连测试 URL 与 DNS、分流和插件完全不变。
- Beta 始终为内部测试资料，不在公开 README 提供安装入口。
- 发布分支必须通过新版本字节复现、历史归档、资源完整性和回归测试；未完成 Loon 真机测速、机场劫持对照及 DNS/连接稳定性验证前不应宣称已验证。


## v6.5.9 · 普通 Loon 服务规则（实机待验收）

- 用户确认命中 `AND+GEOIP` 复合规则会导致 Loon VPN 自动重启，要求合并新版本并清理冗余；已合并实现 PR #141，另按发布流程推动新版 `main/LoonKit.lcf`。
- 五份服务规则改为普通 `DOMAIN` / `DOMAIN-SUFFIX`，且删除远程 `Our-RegionalCN` 的重复 GeoIP 条件；末尾 GeoIP/CN 及 FINAL 两条原封不动。
- 旧版本 `build/baselines/v6.5.8/LoonKit.lcf` 与 v6.5.8 完整资源继续冻结；历史哈希与来源不被替换。
- **未完成设备验收**：DNS 泄漏此前已被用户报告，当前修复仅移除复合 GeoIP；同一服务域名的国内外精确自动分流不再等价保留。不能仅凭 CI 声称 VPN 和 DNS 已完全修复。


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
