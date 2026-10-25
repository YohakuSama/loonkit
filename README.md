<div align="center">

# LoonKit

**为 Loon 打造的完整分流配置**

原生规则分流 · 灵活选路 · 网络诊断

[![Production CI](https://github.com/YohakuSama/loonkit/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/YohakuSama/loonkit/actions/workflows/ci.yml)

[**获取配置**](https://raw.githubusercontent.com/YohakuSama/loonkit/main/LoonKit.lcf) · [功能概览](#功能概览) · [快速开始](#快速开始) · [问题反馈](https://github.com/YohakuSama/loonkit/issues)

</div>

LoonKit 为常用网站、AI、流媒体和社交服务提供分流、广告拦截与网络诊断。

当前版本：**v7.0.0**。

## 快速开始

**[下载 / 导入 LoonKit.lcf](https://raw.githubusercontent.com/YohakuSama/loonkit/main/LoonKit.lcf)** · [查看配置](./LoonKit.lcf)

1. 在 Loon 中导入配置。
2. 添加自己的节点或订阅，在 `Proxy` 中选择线路。
3. 刷新远程规则和插件，按需调整各服务策略。

节点测速使用 `http://www.bing.com`；互联网连接检测与网络诊断保持原有设置。

## 功能概览

| 功能 | 说明 |
| --- | --- |
| 分流 | 国内常用服务直连，AI、流媒体和社交服务独立选路。 |
| 分流策略 | Apple、Microsoft、PayPal、Bilibili 使用普通 Loon 域名规则； |
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

[更新记录](./docs/CHANGELOG.md) · [规则说明](./rules/README.md) · [反馈问题](https://github.com/YohakuSama/loonkit/issues)

[维护文档](./docs/MAINTAINING.md) · [依赖清单](./docs/DEPENDENCIES.md) · [版本校验](./docs/RELEASE_CHECKSUM_v7.0.0.md) · [安全报告](./SECURITY.md)

## 开源许可

原创代码与配置采用 [GPL-2.0-only](./LICENSE)，第三方规则与素材见 [许可与来源](./docs/THIRD_PARTY_NOTICES.md)。
