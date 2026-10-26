<p>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./docs/assets/loonkit-mark-dark.svg" />
    <img src="./docs/assets/loonkit-mark.svg" width="56" height="56" alt="LoonKit 分流路径标识" />
  </picture>
</p>

# LoonKit

**让连接按你的规则走。**

面向 [Loon](https://nsloon.app/) 的规则分流与网络诊断工具箱。独立管理服务策略、节点出口和连接状态，让每条规则都有清晰的去向。

<p>
  <a href="./docs/CHANGELOG.md"><img alt="Release v7.0.9" src="https://img.shields.io/badge/release-v7.0.9-334155?style=flat" /></a>
  <a href="https://github.com/YohakuSama/loonkit/actions/workflows/ci.yml"><img alt="Build status" src="https://github.com/YohakuSama/loonkit/actions/workflows/ci.yml/badge.svg?branch=main" /></a>
  <a href="./LICENSE"><img alt="GPL-2.0-only" src="https://img.shields.io/badge/license-GPL--2.0--only-334155?style=flat" /></a>
</p>

<p>
  <a href="https://www.nsloon.com/openloon/import?sub=https%3A%2F%2Fraw.githubusercontent.com%2FYohakuSama%2Floonkit%2Fmain%2FLoonKit.lcf"><img src="./docs/assets/import-loon.svg" width="186" height="44" alt="一键导入 Loon" /></a>
</p>

[获取配置地址](https://raw.githubusercontent.com/YohakuSama/loonkit/main/LoonKit.lcf) · [快速开始](#快速开始) · [诊断工具](#诊断工具) · [常见问题](#常见问题) · [文档](#文档)

<sub>在 iPhone / iPad 的 Safari 中打开导入链接；使用前请安装 Loon。项目不提供节点、订阅或代理账号。</sub>

---

## 核心能力

- **服务独立选路** — AI、开发平台、流媒体与国内常用服务分别使用策略组。
- **节点自主选择** — 支持 `Proxy`、`Auto`、`Fallback` 与服务级选路；不预置节点服务。
- **诊断当前节点** — 分别查看实际出口、网络状态、DNS 和七项服务的接口访问情况。
- **持续维护** — 版本化插件、更新日志、构建检查和回滚资料相互对应。

本项目是 **Loon 配置与诊断工具**，不提供节点、机场订阅、代理账号或付费平台会员权益。
## 快速开始

**首次导入前，请先备份当前配置和节点订阅。** 主配置不包含个人节点，全覆盖更新可能替换已有内容。

1. 使用 iPhone / iPad 的 Safari 点击顶部 **「一键导入 Loon」**。如果没有唤起 Loon，请在 App 中打开 **「配置 → 所有配置文件 → ＋ → 从链接导入」**，粘贴[配置地址](https://raw.githubusercontent.com/YohakuSama/loonkit/main/LoonKit.lcf)。
2. 需要远程更新时开启 **「托管」**，按需选择更新频率。**仅在已备份并确认接受覆盖后果时**，首次完整部署才开启「全覆盖更新」。
3. 完成导入后应用 `LoonKit.lcf`，添加自己的节点或订阅，在 `Proxy` 和服务策略组中设置线路，并按需刷新远程规则及插件。
4. 日常托管更新建议**关闭「全覆盖更新」**，减少覆盖个人设置的风险；升级前先阅读[更新记录](./docs/CHANGELOG.md)。

> [!IMPORTANT]
> 当前主配置的 `[Proxy]` 与 `[Remote Proxy]` 为空。**全覆盖可能替换既有节点、订阅与本地配置。尚未备份时不要直接执行。**

[逐屏导入教程](./docs/SETUP_GUIDE.md) · [托管与更新选项](./docs/LOON_APP_SETTINGS.md)
## 功能与策略

当前版本：**v7.0.9**。

| 功能 | 当前提供的能力 |
| :--- | :--- |
| **Routing** | 国内常用服务优先直连，AI、Google、GitHub、流媒体与社交应用独立策略。 |
| **Selection** | `Proxy`、`Auto`、`Fallback` 以及服务级节点选择。 |
| **Filtering** | `AdBlock` 可选 `REJECT`、`DIRECT` 或 `Proxy`。 |
| **Diagnostics** | 节点实际出口、网络与 DNS 检查、七项服务访问检测。 |
| **Release** | 固定资源提交、构建清单、回滚基线和持续集成校验。 |

## 诊断工具

LoonKit 的三项手动诊断均可从 **「策略 → 某个节点 → ···」** 菜单运行。下面是根据实际输出整理的**脱敏示例**；测试 IP 为保留示例地址，具体节点与结果随你的网络变化。

<details>
<summary><strong>节点信息</strong> — 入口与实际出口分开显示</summary>

```text
节点：示例节点
协议：Hysteria2
入口：[已隐藏]

【实际出口】
出口 IP：198.51.100.10（示例地址）
IP 版本：IPv4
位置：Japan (JP) · Tokyo
运营商：[已隐藏]
ASN：[已隐藏]
IP 网段：[已隐藏]

【网络识别】
机房 / 云：未检出
VPN / 代理：未检出
数据源：ipconfig.is
```

「未检出」只表示上游数据库没有检出对应标签，**不能据此宣称为住宅 IP 或真实家宽**。

</details>

<details>
<summary><strong>网络检测</strong> — 独立检查节点、直连与 DNS</summary>

```text
连接状态
节点：正常 · 382 ms
直连：正常 · 29 ms
DNS：正常
DNS 详情：解析成功 · DoH
结论：节点连接正常
```

这里的数值仅来自脱敏示例，不代表所有节点的实际性能；插件的 DNS API 结果也不能证明其他 App 没有独立 DNS 请求。

</details>

<details>
<summary><strong>解锁检测</strong> — 七项服务逐一给出访问状态</summary>

```text
可访问：7 / 7
DAZN              可用
Discovery+        可访问
Paramount+        可用
Disney+           可用
Netflix           片源可访问
ChatGPT           可用
YouTube Premium   可用
```

只是某次节点的接口访问示例，**不是会员权益保证**，也不代表所有节点都会 7/7 成功。

</details>

**v7.0.9 修复重点：** 某些节点第一次握手较慢，旧版网络探测约 6.5 秒就可能超时，七项服务检测也曾同时高并发启动。新版增大请求预算、限制并发，并在**原选定节点**上对短时传输错误最多重试一次。不会绕到 DIRECT 或其他节点制造「成功」结果；真实地区限制、拒绝访问和重复超时仍会如实报告。此改动经过模拟测试，**在你的高延迟节点上的实机效果还需要复测**。

[诊断插件源码](./release/v7.0.9/Network_Diagnostics.plugin) · [网络辅助说明](./docs/NETWORK_DIAGNOSTICS.md) · [v7.0.9 更新说明](./docs/RELEASE_NOTES_v7.0.9.md)

## 推荐设置

| 设置 | 建议 | 注意 |
| :--- | :--- | :--- |
| 运行模式 | **规则分流** | 全局直连会绕开预期的分流行为。 |
| `Proxy` / 筛选器 | 添加自己的节点，设置 `Auto_Filter` 和 `Fallback_Filter` | `Fallback` 选择第一个可用节点，而非第二快的节点。 |
| DNS 查询回落 | 隐私优先时**关闭** | DoH 故障可能导致解析失败；需自行权衡。 |
| 托管更新 | 首次全覆盖，后续按需关闭全覆盖 | 具体入口以当前 App 展示为准。 |
| 脚本与插件 | 运行诊断时保持启用 | 当前诊断功能使用 `[Script]`，**无需仅为此安装 MitM 证书**。 |
| TUN / QUIC / UDP | 按实际需要选择 | 不建议照搬旧教程把所有高级开关都设成开启。 |

目前节点测速统一使用 `http://www.bing.com`，独立直连测试为 `http://wifi.vivo.com.cn/generate_204`。当前主配置仍保留 `disable-stun = true`、`udp-fallback-mode = REJECT` 与双栈 IP；语音、游戏或 WebRTC 出现问题时，先核对节点 UDP 能力和 Loon 请求记录，再定向排查。

[节点筛选](./docs/NODE_SELECTION.md) · [App 推荐设置](./docs/LOON_APP_SETTINGS.md)

## 常见问题

<details>
<summary><strong>一键导入无法唤起 Loon？</strong></summary>

请使用已安装 Loon 的 iPhone / iPad，尝试在 Safari 打开本页。仍无效时，按「配置 → 所有配置文件 → ＋ → 从链接导入」手动粘贴：

```text
https://raw.githubusercontent.com/YohakuSama/loonkit/main/LoonKit.lcf
```

导入方式参考 [Loon 官方 Scheme](https://nsloon.app/docs/Scheme/)。

</details>

<details>
<summary><strong>为什么节点能用，但插件第一次显示失败？</strong></summary>

可能是代理首次连接、DNS/TLS 握手、目标平台限流或短时网络抖动造成，不能单凭一次接口失败判定节点永久不可用。v7.0.9 增加同节点有限重试；若仍异常，请收集 Loon 脚本日志、请求时间和目标服务（**不要公开节点密钥或订阅链接**），提交 Issue。

</details>

<details>
<summary><strong>首次覆盖后节点不见了？</strong></summary>

`LoonKit.lcf` 不内置任何私人节点或机场订阅。全覆盖可替换之前的本地内容，因此首次导入前应备份，完成后再添加个人订阅。

</details>

## 文档

| 上手与排查 | 维护与验证 |
| :--- | :--- |
| [真实界面导入与设置说明](./docs/SETUP_GUIDE.md) | [更新记录](./docs/CHANGELOG.md) |
| [配置托管与 App 设置](./docs/LOON_APP_SETTINGS.md) | [v7.0.9 发布说明](./docs/RELEASE_NOTES_v7.0.9.md) |
| [DNS 隐私与验证](./docs/DNS_PRIVACY.md) | [规则分类](./rules/README.md) |
| [自动选路与 Fallback](./docs/NODE_SELECTION.md) | [维护指南](./docs/MAINTAINING.md) |
| [网络检测与输出边界](./docs/NETWORK_DIAGNOSTICS.md) | [v7.0.9 SHA256](./docs/RELEASE_CHECKSUM_v7.0.9.md) |

---

<sub>Made for Loon · [Issues](https://github.com/YohakuSama/loonkit/issues) · [Security](./SECURITY.md) · [Third-party notices](./docs/THIRD_PARTY_NOTICES.md) · [GPL-2.0-only](./LICENSE)</sub>
