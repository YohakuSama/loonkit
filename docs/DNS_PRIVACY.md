# LoonKit · DNS 设置与故障核验

**适用版本：v7.0.8。** 本页说明 LoonKit 的现有 DNS 配置、App 必须手动核对的选项，以及隐私与可用性的取舍。不修改现有 DNS、IPv6 或 TUN 的运行时配置。

## 最重要的 App 开关

**设置 → DNS → DNS 服务器 → 查询回落 → 关闭**（隐私优先时推荐）。

这项设置不能仅通过主配置中的 `dns-server`、`doh-server` 推断或替代。根据 [Loon 官方 DNS 文档](https://nsloon.app/docs/DNS/)，默认情况下加密 DNS 查询失败可回落普通 DNS；关闭后应避免这一明文回落路径，但 **DoH 不可用时可能发生解析失败**。如果当前网络阻断 DoH 且优先考虑可用性，可以自行决定是否打开回落；不要将「关闭回落」宣传成绝对无 DNS 泄漏。

过去部分 Loon 版本把这个选项描述为「加密 DNS 失败回退到普通 DNS」。**以当前 App 截图中的「查询回落」为准**，两者指的是同一类回落行为；不要因此在其他页面重复寻找旧名称。

## 当前配置（保持不变）

```ini
[General]
dns-server = 223.5.5.5,223.6.6.6
doh-server = https://dns.alidns.com/dns-query
hijack-dns = *:53
ip-mode = dual
ipv6-vif = auto

[Host]
dns.alidns.com = 223.5.5.5
```

AliDNS 是目前配置的解析服务；DoH 使用 `dns.alidns.com` 的 HTTPS 端点，`[Host]` 提供启动解析地址。`hijack-dns = *:53` 处理匹配的 UDP 53 DNS 请求，**不保证能拦截 App 内置的加密 DNS、私有解析或其他协议**。节点入口若使用独立的 `server-dns`，应额外检查解析路径。

## 真实设备检查清单

| 场景 | 建议检查 |
| :--- | :--- |
| 正常网络 | 在 Loon DNS 日志中确认 DoH 正常；若需判断明文流量，配合抓包检查。 |
| DoH 故障 | 仅在可控网络中测试故障行为，确认关闭回落后的失败方式；恢复网络后复测。 |
| Wi-Fi / 蜂窝切换 | 分别核对 DNS 记录与实际查询通道，不凭网页能否打开下结论。 |
| 订阅节点域名 | 若有独立 `server-dns`，区分节点服务器解析和普通网页解析。 |
| App 内置 DoH/DoT | 确认是否走 Loon 的 DNS 处理路径，不能把 `hijack-dns` 当作万能拦截。 |
| IPv4 / IPv6 | 分别检查 A/AAAA 与实际连接，不能用 IPv4 结果代表 IPv6。 |

诊断插件只能报告 Loon DNS API 返回的测试结果，**不能独立证明全设备无 DNS 泄漏**。

[返回首页](../README.md) · [App 设置与更新策略](./LOON_APP_SETTINGS.md) · [官方 DNS 说明](https://nsloon.app/docs/DNS/)
