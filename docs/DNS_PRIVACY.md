# DNS 设置与故障核验

默认解析器为 AliDNS。DoH 使用 `dns.alidns.com` 的 HTTPS 域名进行 TLS 验证，`[Host]` 提供启动解析地址。此处不变更已有 DNS、IPv6 或 TUN 的实际配置。

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

## 必须在 Loon App 内核对

在 Loon「DNS 服务器」中关闭**「加密 DNS 失败回退到普通 DNS」**。这个开关不能仅凭配置文件设置，也不能由仓库 CI 推断当前手机的开关状态。普通 DNS 地址保留用于现有配置兼容；关闭回退之后，加密 DNS 故障应呈现解析失败，而不是静默向普通 DNS 发送明文请求。

## 真机验证

| 场景 | 期望与检查方法 |
| --- | --- |
| 正常解析 | 从 Loon DNS 日志确认 DoH 生效；必要时抓包核实没有意外的公网明文 53 端口查询 |
| 仅 DoH 不可达 | 临时制造受控故障，确认不会回退到 UDP/TCP 53；恢复网络后确认自动恢复解析 |
| Wi-Fi / 蜂窝切换 | 分别检查 DNS 日志，不能仅依靠网页可访问判定无泄漏 |
| 节点域名 | 若使用单独的 `server-dns`，核查节点入口域名的实际解析路径 |
| 应用自带 DoH/DoT | 分别核对应用 DNS 流量及路由；`hijack-dns = *:53` 不等于能拦截所有加密 DNS |
| IPv4 / IPv6 | 双栈分别检验 AAAA/A 返回和实际访问，不能将一个地址族的结果外推给另一个 |

插件的「网络检测」能检查 Loon DNS API 的解析状态，**不能独立证明全设备无 DNS 泄漏**。IP/DNS 泄漏测试网站显示的解析器国家也不能证明是否通过明文传输。

[配置](../LoonKit.lcf) · [Loon DNS 文档](https://nsloon.app/docs/DNS/) · [App 设置](./LOON_APP_SETTINGS.md)
