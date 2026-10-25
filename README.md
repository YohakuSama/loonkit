<p align="center"><sub>LOON CONFIGURATION  /  ROUTING TOOLKIT</sub></p>

<h1 align="center">LoonKit</h1>

<p align="center">
  <strong>更清晰的分流，更自由的选路。</strong><br />
  一套为 Loon 整理的分流配置、策略组与网络诊断工具。
</p>

<p align="center">
  <a href="./docs/CHANGELOG.md"><img alt="Version v7.0.8" src="https://img.shields.io/badge/version-v7.0.8-52525b?style=flat-square" /></a>
  <a href="https://github.com/YohakuSama/loonkit/actions/workflows/ci.yml"><img alt="Production CI" src="https://github.com/YohakuSama/loonkit/actions/workflows/ci.yml/badge.svg?branch=main" /></a>
  <a href="./LICENSE"><img alt="GPL-2.0-only" src="https://img.shields.io/badge/license-GPL--2.0--only-52525b?style=flat-square" /></a>
</p>

<p align="center">
  <a href="https://www.nsloon.com/openloon/import?sub=https%3A%2F%2Fraw.githubusercontent.com%2FYohakuSama%2Floonkit%2Fmain%2FLoonKit.lcf"><img src="./docs/assets/import-loon.svg" height="48" alt="一键导入 Loon" /></a>
  &nbsp;
  <a href="https://raw.githubusercontent.com/YohakuSama/loonkit/main/LoonKit.lcf"><img src="./docs/assets/download-config.svg" height="48" alt="获取 LoonKit 配置文件" /></a>
</p>

<p align="center">
  <sub>在 iPhone / iPad 的 Safari 中打开本页，点击「一键导入 Loon」即可尝试唤起 App。</sub>
</p>

<p align="center">
  <a href="#快速开始">快速开始</a> &nbsp;·&nbsp;
  <a href="#功能概览">功能概览</a> &nbsp;·&nbsp;
  <a href="#策略与分流">策略与分流</a> &nbsp;·&nbsp;
  <a href="#使用文档">使用文档</a> &nbsp;·&nbsp;
  <a href="https://github.com/YohakuSama/loonkit/issues">反馈问题</a>
</p>

---

LoonKit 将常用网站、AI 服务、流媒体与社交平台的分流规则集中到一套配置中，同时提供节点选择、广告管理与网络诊断能力。**规则、策略和节点相互独立**：你可以沿用自己的节点订阅，再为不同服务选择合适的线路。

## 快速开始

**01 · 导入配置**  
点击顶部的 **「一键导入 Loon」**，按照 Loon 的提示导入远程配置。

**02 · 添加自己的节点**  
在 Loon 中添加已有节点或节点订阅，然后进入 `Proxy` 选择线路。默认配置**不附带任何节点或代理订阅**。

**03 · 刷新并调整**  
刷新远程规则与插件，按需调整 `Auto`、`Fallback` 和各服务策略组。

> [!NOTE]
> 建议导入前备份原有配置。LoonKit 是配置项目，不提供节点、代理服务或账号；导入后仍需自行添加可用线路。

<details>
<summary>无法一键打开 Loon？查看手动导入方式</summary>

在 Loon 中打开 **配置 → + → 从 URL 下载**，粘贴以下正式版地址：

```text
https://raw.githubusercontent.com/YohakuSama/loonkit/main/LoonKit.lcf
```

也可以通过顶部「获取配置」按钮下载 `.lcf` 文件后从本地导入。如果 GitHub 内置浏览器无法唤起 App，请改用 Safari 打开。

</details>

## 功能概览

| 能力 | 说明 |
| :--- | :--- |
| **精细分流** | 国内常用服务优先直连；AI、开发、流媒体及社交平台分别设置线路。 |
| **灵活选路** | 39 个服务与通用策略组，支持手动选择、延迟测试和故障切换。 |
| **广告管理** | `AdBlock` 可选择拦截、直连放行或代理放行。 |
| **网络诊断** | 查看代理出口、网络与 DNS 连通性，以及部分服务的访问状态。 |
| **规则维护** | 43 份远程 `.lsr` 规则，配套更新记录、校验和维护文档。 |

## 策略与分流

LoonKit 不替你决定所有流量都走哪条线路，而是将常用服务留给你单独控制。

| 策略组 | 用途 |
| :--- | :--- |
| `Proxy` | 主力代理线路，支持手动选择。 |
| `Auto` | 根据测速结果自动选择可用节点。 |
| `Fallback` | 按顺序在可用节点之间故障切换。 |
| `AdBlock` | 在 `REJECT`、`DIRECT` 和 `Proxy` 之间切换。 |
| `Final` | 处理未命中其他规则的连接。 |

**可独立选路的服务**

`ChatGPT` · `Gemini` · `Claude` · `GitHub` · `Google` · `YouTube` · `Netflix` · `Disney` · `Telegram` · `Spotify` · `Cloudflare` 等。

`Apple`、`Microsoft`、`Bilibili`、`Line`、`Speedtest` 的策略组默认优先直连，必要时可以改选代理。`Auto` 和 `Fallback` 初始覆盖全部节点，建议按个人订阅分别设置候选池。

节点测速使用 `http://www.bing.com`；独立的直连互联网检测使用 204 地址。详细说明见 [节点选择](./docs/NODE_SELECTION.md) 与 [DNS 设置](./docs/DNS_PRIVACY.md)。

## 网络辅助

主配置包含 [Network Diagnostics](./release/Network_Diagnostics.plugin) 插件，集中提供：

- **节点信息**：查看实际代理出口 IP、地区、ASN、运营商等信息，并与可获取的入口信息分开展示。
- **网络检查**：验证所选节点的 HTTPS 连通性、直连网络及 Loon DNS。
- **服务检测**：检查 DAZN、Discovery+、Paramount+、Disney+、Netflix、ChatGPT、YouTube Premium 的接口或区域访问状态。

> 服务检测不代表会员权益保证。IP 归属地和网络类型来自第三方识别，仅供排查参考。

[网络辅助说明](./docs/NETWORK_DIAGNOSTICS.md) · [分流排查](./docs/ROUTE_DIAGNOSTICS.md)

## 使用文档

| 使用指南 | 项目资料 |
| :--- | :--- |
| [节点与策略组](./docs/NODE_SELECTION.md) | [更新记录](./docs/CHANGELOG.md) |
| [DNS 与隐私](./docs/DNS_PRIVACY.md) | [规则说明](./rules/README.md) |
| [Loon App 设置](./docs/LOON_APP_SETTINGS.md) | [维护说明](./docs/MAINTAINING.md) |
| [网络辅助](./docs/NETWORK_DIAGNOSTICS.md) | [依赖与来源](./docs/DEPENDENCIES.md) |
| [分流故障排查](./docs/ROUTE_DIAGNOSTICS.md) | [v7.0.8 校验](./docs/RELEASE_CHECKSUM_v7.0.8.md) |

<details>
<summary>常见问题</summary>

**导入后看不到节点？**  
主配置的 `[Proxy]`、`[Remote Proxy]` 不预置节点。添加自己的节点订阅后，再配置 `Proxy`、`Auto` 和 `Fallback`。

**规则或诊断插件未更新？**  
检查是否能访问 GitHub 原始文件地址，然后在 Loon 中刷新远程规则及插件。

**某个应用走错线路？**  
先检查对应策略组，再通过 Loon 的近期请求记录确认实际命中规则；参考 [分流排查](./docs/ROUTE_DIAGNOSTICS.md)。

</details>

---

**反馈与许可**

遇到问题可以提交 [Issue](https://github.com/YohakuSama/loonkit/issues)，请不要公开私人订阅链接或节点密钥。

原创代码与配置采用 [GPL-2.0-only](./LICENSE)；第三方规则和素材的许可见 [来源说明](./docs/THIRD_PARTY_NOTICES.md)。安全问题参见 [SECURITY.md](./SECURITY.md)。
