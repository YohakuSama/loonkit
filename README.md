<div align="center">

# LoonKit

**为 Loon 打造的完整分流配置**

精细分流 · 灵活选路 · 网络诊断

[![Production CI](https://github.com/YohakuSama/loonkit/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/YohakuSama/loonkit/actions/workflows/ci.yml)

[**获取配置**](https://raw.githubusercontent.com/YohakuSama/loonkit/main/LoonKit.lcf) · [功能概览](#功能概览) · [快速开始](#快速开始) · [问题反馈](https://github.com/YohakuSama/loonkit/issues)

</div>

LoonKit 为常用网站、AI、流媒体和社交服务提供分流、广告拦截与网络诊断。

当前版本：**v6.5.8**。

## VPN 反复断开 / 自动重连排查

如果 Loon 导入本项目配置后出现 VPN 自动关闭并重新连接，可先使用 **[Safe Routing 配置](https://raw.githubusercontent.com/YohakuSama/loonkit/main/LoonKit.Safe.lcf)** 进行稳定性对比测试（[查看文件](./LoonKit.Safe.lcf)）。此版本暂时**不加载** `Our-RegionalCN`、`Our-AppleOTA`、`Our-Bilibili`、`Our-Microsoft`、`Our-Apple`、`Our-Paypal` 六个高密度复合规则集，**不新增任何直连规则**。未被其他域名规则命中的大陆 IP 由 `GEOIP,CN,DIRECT` 处理，其余走 `FINAL`；原始 v6.5.8 正式配置不变。

**注意**：这是待实机验证的排障配置，不保证重连一定由复合规则引起。六个服务原有专属分流在该配置中暂停，部分请求将改为 GeoIP 或 Final 策略。域名规则优先级高于 IP 规则，详情与 DNS 检查方法见 [适用范围与 A/B 测试](./docs/SAFE_ROUTING.md)。

## 快速开始

**[下载 / 导入 LoonKit.lcf](https://raw.githubusercontent.com/YohakuSama/loonkit/main/LoonKit.lcf)** · [查看配置](./LoonKit.lcf)

1. 在 Loon 中导入配置。
2. 添加自己的节点或订阅，在 `Proxy` 中选择线路。
3. 刷新远程规则和插件，按需调整各服务策略。
4. 在 DNS 设置中关闭「加密 DNS 失败回退到普通 DNS」。

[导入测试版](https://raw.githubusercontent.com/YohakuSama/loonkit/beta/beta/LoonKit.lcf) · [测试渠道](https://github.com/YohakuSama/loonkit/blob/beta/docs/BETA_CHANNEL.md)

## 功能概览

| 功能 | 说明 |
| --- | --- |
| 分流 | 国内常用服务直连，AI、流媒体和社交服务独立选路。 |
| 地区判断 | Apple、Microsoft、PayPal、Bilibili 按解析 IP 区分国内和海外。 |
| 节点选择 | 支持手动选择、延迟测试和故障切换。 |
| 广告拦截 | `AdBlock` 中选择 `REJECT` 拦截、`Proxy` 放行。 |
| 网络辅助 | 查看节点出口、连接状态及流媒体和 AI 服务状态。 |
| 规则更新 | 定期检查上游，生成经过校验的测试版更新。 |

## 常用策略

| 策略组 | 用途 |
| --- | --- |
| `Proxy` | 选择常用代理线路。 |
| `Auto` | 自动选择延迟较低的节点。 |
| `Fallback` | 按顺序选择可用节点。 |
| `AdBlock` | 切换广告拦截与放行。 |
| `Final` | 处理未命中其他规则的请求。 |

[节点选择](./docs/NODE_SELECTION.md) · [DNS 设置](./docs/DNS_PRIVACY.md) · [Loon App 设置](./docs/LOON_APP_SETTINGS.md)

## 网络辅助

- **节点信息**：查看入口、代理出口 IP、地区和运营商。
- **网络检测**：检查直连、代理和 DNS。
- **解锁检测**：检测 DAZN、Discovery+、Paramount+、Disney+、Netflix、ChatGPT 和 YouTube Premium。
- **网络切换提醒**：可在插件设置中开启。

[使用说明](./docs/NETWORK_DIAGNOSTICS.md) · [分流排查](./docs/ROUTE_DIAGNOSTICS.md)

## 文档与支持

[更新记录](./docs/CHANGELOG.md) · [规则说明](./rules/README.md) · [测试渠道](./docs/BETA_CHANNEL.md) · [反馈问题](https://github.com/YohakuSama/loonkit/issues)

[维护文档](./docs/MAINTAINING.md) · [依赖清单](./docs/DEPENDENCIES.md) · [版本校验](./docs/RELEASE_CHECKSUM_v6.5.8.md) · [安全报告](./SECURITY.md)

## 开源许可

原创代码与配置采用 [GPL-2.0-only](./LICENSE)，第三方规则与素材见 [许可与来源](./docs/THIRD_PARTY_NOTICES.md)。
