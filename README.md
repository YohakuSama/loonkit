<p align="center">
  <picture>
    <source media="(max-width: 600px) and (prefers-color-scheme: dark)" srcset="./docs/assets/readme-hero-mobile-dark.svg" />
    <source media="(max-width: 600px)" srcset="./docs/assets/readme-hero-mobile-light.svg" />
    <source media="(prefers-color-scheme: dark)" srcset="./docs/assets/readme-hero-wide-dark.svg" />
    <img src="./docs/assets/readme-hero-wide-light.svg" alt="LoonKit：为 Loon 提供规则分流、节点选路与网络辅助的配置" width="960" />
  </picture>
</p>

<p align="center">
  <strong>让不同服务，走各自合适的线路。</strong>
</p>

<p align="center">
  适用于 Loon 的规则分流配置与网络辅助工具。<br />
  国内常用服务优先直连，AI、开发平台和流媒体等服务可独立选路。
</p>

<p align="center">
  <a href="https://www.nsloon.com/openloon/import?sub=https%3A%2F%2Fraw.githubusercontent.com%2FYohakuSama%2Floonkit%2Fmain%2FLoonKit.lcf">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="./docs/assets/readme-cta-dark.svg" />
      <img src="./docs/assets/readme-cta-light.svg" alt="一键导入 Loon" width="214" height="48" />
    </picture>
  </a>
</p>

<p align="center">
  <sub>请在已安装 Loon 的 iPhone / iPad 上通过 Safari 导入 · 节点与订阅需自行准备</sub>
</p>

<p align="center">
  <a href="https://raw.githubusercontent.com/YohakuSama/loonkit/main/LoonKit.lcf">获取配置地址</a> ·
  <a href="#快速开始">快速开始</a> ·
  <a href="./docs/SETUP_GUIDE.md">完整指南</a>
</p>

当前版本：**v7.0.10** · [更新记录](./docs/CHANGELOG.md) · [Production CI](https://github.com/YohakuSama/loonkit/actions/workflows/ci.yml) · [GPL-2.0-only](./LICENSE)

---

## 功能概览

**服务分流** — 根据服务类别分别设定策略。国内常用服务优先直连，AI、开发平台、流媒体与社交服务按需选择线路。

**节点选路** — 通过 `Proxy` 手动选路、`Auto` 根据测速选择节点，或由 `Fallback` 在候选线路中选择可用节点；广告管理由 `AdBlock` 策略控制。

**网络辅助** — 在选定节点上查看出口信息、连接状态和 DNS 结果，辅助定位问题。诊断结果反映测试时的网络状况，不代表持续可用。

## 快速开始

1. **备份**：首次导入前，先导出现有配置并保存节点订阅。
2. **导入**：在 iPhone / iPad 的 Safari 中点击顶部「一键导入 Loon」；若未唤起 App，可在 **配置 → 所有配置文件 → ＋ → 从链接导入** 中粘贴[配置地址](https://raw.githubusercontent.com/YohakuSama/loonkit/main/LoonKit.lcf)。
3. **配置线路**：应用 `LoonKit.lcf`，再添加自己的节点或订阅，在 `Proxy` 与各服务策略组中选路。
4. **更新**：需要托管更新时可开启「托管」并设置频率；日常更新建议关闭「全覆盖更新」。

> [!IMPORTANT]
> 主配置的 `[Proxy]` 和 `[Remote Proxy]` 默认不包含个人节点。**「全覆盖更新」可能替换现有节点、订阅及本地设置。** 只有完成备份、确认接受覆盖后果时，才在首次完整部署中使用。

[详细导入步骤](./docs/SETUP_GUIDE.md) · [托管与更新选项](./docs/LOON_APP_SETTINGS.md)

## 使用与排查

- **切换线路**：在 Loon 的策略页选择服务策略组，改选 `DIRECT`、`Proxy`、`Auto` 或 `Fallback`。其中 `Fallback` 选择第一个可用节点，而不是延迟第二低的节点。
- **检查出口**：在 **策略 → 选定节点 → ···** 中运行所需的网络辅助工具，区分节点入口、实际出口与连接状态。[网络辅助说明](./docs/NETWORK_DIAGNOSTICS.md)
- **DNS 默认方案**：默认使用 AliDNS，适合主要在中国大陆网络使用；也可换成自建或国内可稳定访问、按需支持 ECS 的解析器。若更换为需要代理访问的**海外 DoH**，进入 **配置 / 设置 → DNS → DNS 服务器**，替换 DoH URL，将 **「DoH 流量模式」设为 `RULE`**，并确认解析器请求实际命中可用代理。
- **DNS 查询回落（隐私优先建议关闭）**：进入 **配置 / 设置 → DNS → DNS 服务器 → 查询回落 → 关闭**。关闭后，Loon 的加密 DNS 查询失败时不会自动回落至普通 DNS，可减少这类明文 DNS 重试；但如果 DoH 不可用，可能出现域名解析失败。优先考虑可用性的用户可根据网络情况决定是否开启。这是**独立于「DoH 流量模式」的 App 开关**，也不能据此判断设备的全部 DNS 路径。[DNS 设置与核验](./docs/DNS_PRIVACY.md)

<details>
<summary><strong>进阶设置与兼容性</strong></summary>

- 节点测速默认使用 `http://www.bing.com`，实际结果受网络与节点影响。
- 自动选路和备用线路的候选筛选可分别设置，见[节点选择说明](./docs/NODE_SELECTION.md)。
- 网络辅助使用脚本功能，无需仅为此安装 MitM 证书。
- TUN、UDP、QUIC、IPv6 应根据实际网络及节点协议调整；遇到问题时先核对 Loon 请求记录。

</details>

## 常见问题

<details>
<summary><strong>点击导入后没有打开 Loon？</strong></summary>

请确认设备已安装 Loon，并用 Safari 打开页面。也可以在「配置 → 所有配置文件 → ＋ → 从链接导入」中手动粘贴[配置地址](https://raw.githubusercontent.com/YohakuSama/loonkit/main/LoonKit.lcf)。参见 [Loon 官方 URL Scheme](https://nsloon.app/docs/Scheme/)。

</details>

<details>
<summary><strong>导入后没有可用节点？</strong></summary>

LoonKit 不内置个人节点。请添加自己的节点订阅，并检查 `Proxy` 及服务策略组的线路选择。若启用了全覆盖更新，还应确认原有设置是否被替换。

</details>

<details>
<summary><strong>节点能连接，但诊断偶尔失败？</strong></summary>

首次握手、DNS/TLS 连接、临时网络波动等因素都可能影响结果。建议在同一节点复测，并结合请求记录与脚本日志排查。如需提交 [Issue](https://github.com/YohakuSama/loonkit/issues)，请先移除节点密钥和私人订阅链接。

</details>

## 文档导航

**使用指南** · [导入与设置](./docs/SETUP_GUIDE.md) · [配置托管](./docs/LOON_APP_SETTINGS.md) · [节点选择](./docs/NODE_SELECTION.md) · [DNS 设置](./docs/DNS_PRIVACY.md)

**规则与诊断** · [规则分类](./rules/README.md) · [网络辅助](./docs/NETWORK_DIAGNOSTICS.md) · [插件源码](./release/Network_Diagnostics.plugin)

**项目维护** · [更新日志](./docs/CHANGELOG.md) · [发布说明](./docs/RELEASE_NOTES_v7.0.10.md) · [版本校验](./docs/RELEASE_CHECKSUM_v7.0.10.md) · [维护指南](./docs/MAINTAINING.md)

<sub>[Issues](https://github.com/YohakuSama/loonkit/issues) · [Security](./SECURITY.md) · [Third-party notices](./docs/THIRD_PARTY_NOTICES.md) · [GPL-2.0-only](./LICENSE)</sub>
