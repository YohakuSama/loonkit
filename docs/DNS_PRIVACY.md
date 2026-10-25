# DNS 设置

默认解析器为 AliDNS。DoH 使用域名验证 TLS 证书，Host 映射提供启动地址。

```ini
[General]
doh-server = https://dns.alidns.com/dns-query
hijack-dns = *:53

[Host]
dns.alidns.com = 223.5.5.5
```

在 Loon 的 DNS 服务器页面关闭 **「加密 DNS 失败回退到普通 DNS」**。关闭后，加密解析失败应停止解析，直到 DoH 恢复。

普通 DNS 地址保留为 AliDNS；是否启用故障回退由上述 App 开关控制。配置文件没有对应的远程开关。

## 检查方法

| 场景 | 检查内容 |
| --- | --- |
| 正常访问 | DNS 日志使用配置中的 DoH；抓包没有对应的公网明文 DNS 查询。 |
| DoH 故障 | DoH 不可达时解析失败，没有转为 UDP/TCP 53。 |
| 网络切换 | Wi-Fi 与蜂窝切换后继续使用 DoH。 |
| 节点域名 | 节点启动解析路径与全局设置一致；单独配置 server-dns 时检查该项。 |
| 应用自带 DNS | 单独核对应用发起的 DoH/DoT 请求及其路由。 |

DNS 泄漏网站显示的解析器地区不能单独说明是否使用明文传输。AliDNS 是本配置指定的解析服务。

[配置](../LoonKit.lcf) · [Loon DNS 文档](https://nsloon.app/docs/DNS/) · [App 设置](./LOON_APP_SETTINGS.md)
