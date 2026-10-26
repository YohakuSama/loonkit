<p>
  <img src="./docs/assets/loonkit-mark.svg" width="64" height="64" alt="LoonKit 路径分流标识" />
</p>

# LoonKit

**让连接按你的规则走。**

一套面向 [Loon](https://nsloon.app/) 的分流配置与网络诊断工具箱。把服务分流、节点选择和连接排查组织在一起；保留清晰的策略边界，也保留你对每个出口的控制。

<p>
  <a href="./docs/CHANGELOG.md"><img alt="Release v7.0.9" src="https://img.shields.io/badge/release-v7.0.9-334155?style=flat" /></a>
  <a href="https://github.com/YohakuSama/loonkit/actions/workflows/ci.yml"><img alt="Build status" src="https://github.com/YohakuSama/loonkit/actions/workflows/ci.yml/badge.svg?branch=main" /></a>
  <a href="./LICENSE"><img alt="GPL-2.0-only" src="https://img.shields.io/badge/license-GPL--2.0--only-334155?style=flat" /></a>
</p>

<p>
  <a href="https://www.nsloon.com/openloon/import?sub=https%3A%2F%2Fraw.githubusercontent.com%2FYohakuSama%2Floonkit%2Fmain%2FLoonKit.lcf"><img src="./docs/assets/import-loon.svg" width="186" height="44" alt="一键导入 Loon" /></a>
</p>

[获取配置地址](https://raw.githubusercontent.com/YohakuSama/loonkit/main/LoonKit.lcf) · [快速开始](#快速开始) · [诊断工具](#诊断工具) · [关键设置](#关键设置) · [常见问题](#常见问题) · [文档](#文档)

<sub>在 iPhone / iPad 的 Safari 中打开导入链接；使用前请安装 Loon。项目不提供节点、订阅或代理账号。</sub>

---

## 一套可读、可维护的分流方案

- **服务独立选路** — AI、开发平台、流媒体与国内常用服务使用独立策略组。
- **节点由你决定** — 配合 Auto / Fallback 策略、自有订阅与广告过滤，不内置代理服务。
- **诊断选定节点** — 分别查看真实出口、连接状态、DNS 与七项服务访问情况。
- **升级可追溯** — 版本化插件、变更日志、构建检查与回滚资料相互对应。

## 快速开始

### 01 / 导入配置

**第一次部署前，先备份原有配置及节点订阅。** 按你实际使用的 Loon 界面操作：

1. 打开 Loon 底部 **「配置」→「所有配置文件」**，点击右上角 **「＋」→「从链接导入」**。
2. 粘贴上方的 [`LoonKit.lcf` 配置地址](https://raw.githubusercontent.com/YohakuSama/loonkit/main/LoonKit.lcf)；或者直接点击顶部「一键导入」唤起 Loon。
3. 打开 **「托管」**，按需设置 **「更新频率」**（例如每隔 7 天；并非必须固定值）。
4. **首次完整部署时开启「全覆盖更新」**，确认导入。然后选择并应用 `LoonKit.lcf`。
5. 再添加自己的节点订阅，在 `Proxy` 中选线路，按需刷新远程规则和插件。

> [!IMPORTANT]
> 当前主配置的 `[Proxy]` 和 `[Remote Proxy]` 是空的。**全覆盖更新可能替换既有节点、订阅与本地配置。** 如果已有个人配置，请先导出备份。只有确认接受这些覆盖后果，才执行首次全覆盖。

### 02 / 设置日常更新

**「全覆盖更新」不是日常更新的推荐常开项。**

- 在「从链接导入」界面，开启「托管」后会显示 **更新频率** 和 **全覆盖更新**。
- 首次部署完成后，日常更新建议 **关闭全覆盖更新**，以降低覆盖个人设置的风险；大版本升级前应重新备份并阅读 [更新记录](./docs/CHANGELOG.md)。
- 你提供的当前 Loon 截图显示：长按 `LoonKit.lcf` 出现 **应用、编辑、重命名、启用 iCloud、导出、删除** 等菜单，**没有「更新策略」项**。因此本页不再把「长按 → 更新策略」写成操作路径。更新托管参数时应以当前 App 的配置详情或导入选项为准。
- 远程资源的定时更新需要考虑 Loon 的运行状态；iOS 后台不保证准点完成。

[导入与更新详细说明](./docs/LOON_APP_SETTINGS.md) · [新版界面对照](./docs/SETUP_GUIDE.md)

### 03 / 关闭 DNS 查询回落（隐私优先）

进入 Loon 的 **配置 / 设置 → DNS → DNS 服务器 → 查询回落 → 关闭**。

已核对的 Loon 界面显示此开关位于「DNS 服务器」页面。关闭后能避免 **DoH 查询失败时通过普通 DNS 重试**；但如果 DoH 被当前网络阻断，域名解析可能失败。**这不等于保证全设备零 DNS 泄漏。**

当前配置使用 AliDNS DoH：`https://dns.alidns.com/dns-query`，并保留普通 DNS 地址用于对应场景。截图中的「DoH 流量模式 DIRECT」是 *DoH 请求的路由方式*，**不是「查询回落」开关**。

[DNS 原理与检查](./docs/DNS_PRIVACY.md) · [Loon 官方 DNS 文档](https://nsloon.app/docs/DNS/)

## 功能与策略

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

这里的数值仅来自你提供的示例截图，不代表所有节点的实际性能；插件的 DNS API 结果也不能证明其他 App 没有独立 DNS 请求。

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

## 关键设置

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
