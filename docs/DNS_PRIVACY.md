# LoonKit · DNS 设置与连通性检查

LoonKit 默认使用 AliDNS，适合主要在中国大陆网络使用的场景。更换解析器时需要分别确认 **DNS 服务、DoH 请求的路由方式，以及查询失败后的回落行为**，这三项设置相互独立。

## 推荐方案

| 使用环境 | DNS 建议 | App 中的「DoH 流量模式」 |
| :--- | :--- | :--- |
| 中国大陆网络，使用默认 AliDNS | 保留现有配置，先确认解析正常 | `DIRECT` 可以保持；无须为默认方案强制改成 `RULE` |
| 使用自己的解析器，或在中国大陆可稳定连接的其他解析器 | 优先选择可信、可用的 DoH 服务；有 CDN 调度需求时，可优先考虑**明确支持 ECS** 的服务 | 能直连则可保持 `DIRECT`；需要按规则转发时选 `RULE` |
| 在中国大陆网络中使用需要代理才能访问的海外 DoH | 将 AliDNS 的 DoH 地址替换为目标解析器的实际 HTTPS 端点 | **改成 `RULE`，并确保解析器域名/IP 的规则命中可用代理** |

以上 `DIRECT` / `RULE` 指的是 **DoH 请求本身**的流量模式，不是整个 Loon 的运行模式，也不是「查询回落」开关。选择 `RULE` 只会让 DoH 请求依照实际命中的规则选路：若规则仍指向 `DIRECT`、节点不可用，或代理启动依赖该 DoH 解析节点域名，仍可能解析失败。需要时应检查该 DoH 域名的请求记录和节点域名的启动解析。

AliDNS 支持 EDNS Client Subnet（ECS），有助于满足条件时的 CDN/地区调度；但**支持 ECS 不等于每次 DoH 请求都会携带客户端网段，也不保证所有权威 DNS 都会据此返回最优地址**。ECS 可能向上游披露部分客户端网段，需与隐私偏好权衡。其他解析器是否支持 ECS、是否在中国大陆提供可用接入，请以服务商说明和实测为准。

## App 中如何更换 DoH

1. 进入 **配置 / 设置 → DNS → DNS 服务器**，查看当前 DoH 服务器与「DoH 流量模式」。
2. 默认使用 AliDNS 时，无须更换。若改用自建或第三方解析器，把 **DoH 服务器地址**替换为其官方提供的完整 HTTPS URL；仅修改「普通 DNS」或 `dns-server` **不会替换 DoH**。
3. **海外 DoH 需要代理访问时，将「DoH 流量模式」设为 `RULE`**，确认对应域名/IP 的命中策略实际走可用节点；不能仅切换选项就假定解析成功。国内或自建解析器能够直连时，通常可继续使用 `DIRECT`。
4. 「查询回落」的设置取决于隐私与可用性偏好，具体行为见下节；修改后记录当前选项，避免与 DoH 的 `RULE` 模式混淆。
5. 如果使用托管配置，还应核对配置文件 `[General]` 中的 `doh-server`。重新导入或全覆盖更新后，确认 App 实际使用的 DoH 服务器与流量模式；手动设置可能受配置更新影响。

若新 DoH 使用域名，请额外核对其启动解析是否可用；项目中 `[Host]` 对 `dns.alidns.com` 的固定地址**只用于默认 AliDNS**，不能拿来映射其他解析器。节点入口域名也可能有独立的 `server-dns`，与普通网页 DNS 分开配置和检查。

## 查询回落：关闭方式与影响

**配置 / 设置 → DNS → DNS 服务器 → 查询回落**。

Loon 官方 DNS 文档说明：加密 DNS 查询失败时，默认可以回落到普通 DNS；关闭这个选项，可以避免 **Loon 自身此类失败回落**，适合优先限制明文重试的用户。如果网络无法到达所选 DoH，关闭回落可能导致域名无法解析；需要在隐私与可用性之间自行选择。旧界面中的「加密 DNS 失败回退到普通 DNS」与此处的「查询回落」对应。

它只控制上述回落行为，不控制第三方 App 自带的 DoH/DoT、节点入口解析或可能绕过 Loon 的其他流量，不能单靠一个开关判断整个设备的 DNS 路径。

## LoonKit 默认 DNS 配置

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

`dns-server` 是普通 UDP DNS；`doh-server` 是加密 DNS 端点；`[Host]` 提供 AliDNS 主机名的启动地址；`hijack-dns = *:53` 处理匹配的 UDP/53 DNS 查询，**不等于拦截所有加密 DNS**。

## 按故障现象定位

| 现象 | 检查重点 |
| --- | --- |
| 默认 AliDNS 偶尔解析失败 | 核对 DoH 端点可达性、Loon DNS 日志和网络切换时机；暂不急于更换全套解析器。 |
| 更换海外 DoH 后无法打开网站 | 在请求记录中确认解析器请求是否按 `RULE` 命中可用代理，再区分 DoH TLS 连接失败与目标服务本身不可达。 |
| 关闭「查询回落」后只有部分网络不可用 | 在可控环境检查是否存在被阻断的 DoH 连接；恢复原网络与配置后复测，不把失败直接归因于规则。 |
| 仅 IPv6 或仅某类节点异常 | 分别检查 A/AAAA、Wi-Fi/蜂窝网络、节点 `server-dns` 与实际连接路径。 |

**验证能力边界**：DNS 日志显示解析结果，网络辅助工具显示 Loon DNS API 的测试结果；若要判断是否存在明文查询或绕行，仍需核查对应请求路径，必要时在授权的网络中抓包。单个检测网页不代表设备上的全部 DNS 请求。

参考：[Loon 官方 DNS 文档](https://nsloon.app/docs/DNS/) · [Loon 节点 DNS](https://nsloon.app/docs/Node/) · [阿里云 ECS 说明](https://www.alibabacloud.com/help/zh/dns/pvtz-intelligent-analysis-of-vpc-single-line-egress-based-on-forwarding-management)

[返回首页](../README.md) · [App 设置与托管](./LOON_APP_SETTINGS.md)
