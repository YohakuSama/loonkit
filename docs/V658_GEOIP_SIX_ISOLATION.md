# 六份 GEOIP 复合规则导致 VPN 重启：单变量定位（v6.5.8）

## 最新实机反馈（2026-10-25）

**Group A（RegionalCN + AppleOTA + Bilibili）已测试：VPN 没有自动重启，但 DNS 泄漏检测未通过。** Group B（Microsoft + Apple + PayPal）尚未测试。该结果只能说明 Group A 在已测网络和时段下未复现重启，**不能判断 Group A 的三个服务规则在 DNS 方面可用**，也不能宣称故障只存在于 Group B。

检查过原始 v6.5.8 与 Group A、Group B：三者 `[General]` 中的 `dns-server = 223.5.5.5,223.6.6.6`、`doh-server = https://dns.alidns.com/dns-query`、`hijack-dns = *:53`、`ip-mode = dual` 以及 `[Rule]` 的 `GEOIP,CN,DIRECT,no-resolve` / `FINAL,Final` 完全相同。**DNS 泄漏不一定是上述三份新启用规则造成**。尤其官方文档称：同时配置普通 DNS 和 DoH，优先加密解析，但加密 DNS 失败时，App 默认可回退普通 DNS。需要核对 App 内「加密 DNS 失败回退普通 DNS」开关（https://nsloon.app/docs/DNS/）。同时检查节点专用 DNS、系统应用自带 DNS、IPv6、DNS 测试站点解析器列表，不能只凭显示了 AliDNS/所在地就认定普通 UDP DNS 泄漏。

为区别“六份复合规则影响”与“所有诊断配置共有的 DNS 问题”，新增 [None.lcf](../diagnostics/v6.5.8-geoip-six/None.lcf)：仅禁用六份，**保留原版的 no-resolve 及其他所有 DNS 设置**。在相同 App 开关、网络/节点和泄漏测试站点上，分别比较 None、Group A 和 Group B 的**DNS 解析器 IP/ASN、传输是否为 UDP 53、实际请求命中规则**。若 None 也泄漏，则不能将泄漏归因于 Group A；若 None 不泄漏而 Group A 泄漏，才继续使用单份隔离配置筛查 RegionalCN、AppleOTA、Bilibili。

**建议测试顺序**：先完成尚未测试的 **Group B（记录 VPN 和 DNS 两项）**；之后测试 None 作为泄漏的严格基线。如果 Group B 不重启，则调查两组叠加；如果重启，就分别检查 Group B 三个单份规则。测试时无需修改 `GEOIP,CN,DIRECT,no-resolve`，也不要为通过 DNS 检测而盲目添加 DIRECT。

## 已确认的实机结果

| 用户已测试的配置 | 结果 |
| --- | --- |
| v6.5.8 全部六份复合订阅 | VPN 持续断开/重连 |
| 六份全注释 | VPN 正常 |
| PR #138：OR 分组优化、5228 → 696 顶层复合规则 | VPN 仍重启；该 PR 已关闭 |
| PR #139：为全部 5228 条复合条件内部的 GEOIP 加 no-resolve | VPN 仍重启；该 PR 已关闭 |

**目前没有证据证明是某一份列表、某一种逻辑语法、某一条具体规则或总内存用量导致异常。** 上述三种全开配置均出现重启，只能确认问题与六份规则同时存在有关。不要再把压缩规则数、无条件强制 DIRECT 或追加 no-resolve 当作已经验证的解决方法。

官方 [规则匹配顺序](https://nsloon.app/docs/Rule/)、[逻辑规则语法](https://nsloon.app/docs/Rule/logic_rule/) 和 [IP/no-resolve](https://nsloon.app/docs/Rule/ip_rule/) 均不能取代 Loon/iOS VPN Extension 的真机诊断记录。

## 本 PR 提供的严格对照

**所有配置均复制原始正式 v6.5.8 文件，不引用任何前两次失败实验资源。** 只改变六份正式、不可变订阅中哪些条目被导入；所有原始订阅 URL、匹配器和策略均未编辑。其他 31 份订阅完全保留。

| 配置文件 | 六份可疑订阅中仍启用 | 远程订阅总数 |
| --- | --- | ---: |
| [None.lcf](../diagnostics/v6.5.8-geoip-six/None.lcf) | 无（严格 DNS/VPN 对照基线） | 31 |
| [GroupA.lcf](../diagnostics/v6.5.8-geoip-six/GroupA.lcf) | RegionalCN、AppleOTA、Bilibili | 34 |
| [GroupB.lcf](../diagnostics/v6.5.8-geoip-six/GroupB.lcf) | Microsoft、Apple、Paypal | 34 |
| [OnlyRegionalCN.lcf](../diagnostics/v6.5.8-geoip-six/OnlyRegionalCN.lcf) | RegionalCN | 32 |
| [OnlyAppleOTA.lcf](../diagnostics/v6.5.8-geoip-six/OnlyAppleOTA.lcf) | AppleOTA | 32 |
| [OnlyBilibili.lcf](../diagnostics/v6.5.8-geoip-six/OnlyBilibili.lcf) | Bilibili | 32 |
| [OnlyMicrosoft.lcf](../diagnostics/v6.5.8-geoip-six/OnlyMicrosoft.lcf) | Microsoft | 32 |
| [OnlyApple.lcf](../diagnostics/v6.5.8-geoip-six/OnlyApple.lcf) | Apple | 32 |
| [OnlyPaypal.lcf](../diagnostics/v6.5.8-geoip-six/OnlyPaypal.lcf) | Paypal | 32 |

始终保持：

```ini
GEOIP,CN,DIRECT,no-resolve
FINAL,Final
```

以及完整 `[General]` 的 DNS、DoH、`hijack-dns`、`ip-mode`、IPv6，`[Host]`、`[Proxy Group]`、`[Plugin]`、其余远程资源不变。没有新增 CN DIRECT 域名或静态 IP 表，也没有修改 Apple/Microsoft/PayPal 默认策略。

## 最少的有效实机测试顺序

1. **Group A 已测：VPN 稳定，DNS 检测未通过。现在先测试 Group B，并记录 VPN 与 DNS 两项；再测试 None 对照泄漏来源。** 导入时确认**原有配置被替换**，不是在当前配置上追加订阅；执行刷新远程规则，分别确认总数 34、六份可疑中各有三份。保持相同网络、节点、Loon/iOS 版本及 App 内 DNS 回退开关。
2. **若只有 Group A 触发重启**，测试 OnlyRegionalCN、OnlyAppleOTA、OnlyBilibili。**若只有 Group B 触发**，测试 OnlyMicrosoft、OnlyApple、OnlyPaypal。若两组都触发，则两个组都需要各自定位。
3. **若 Group A 和 Group B 单独都稳定，六份同时启用却重启**，更像跨组交互或资源累积问题；不能认定单个列表出错。继续对单份规则量/多份叠加进行受控测试，配合 VPN Extension 的 Jetsam/崩溃日志。
4. **若一组触发，但该组三份单独都不触发**，优先做两两组合排查，而不是从任意一份里删规则。在确定触发组合后，对相关列表再按规则行范围二分。

**每次测试记录**：是否正常导入、六份中实际启用哪几份、规则刷新是否出错、最短复现间隔、iOS 诊断分析中的 Network Extension 退出或 Jetsam 记录，并对比 DNS 测试结果。注意不要公开付费节点、订阅 Token 和设备标识。

## 为什么此 PR 还不能算完成地区分流修复

Loon 对域名规则的匹配优先于 IP 规则；对于同一服务既有 CN 又有海外部署的域名，要根据实际 IP 归属决定路由，不能简单把全部 Apple/Microsoft/PayPal 域名静态设为 DIRECT。反过来，五千多条 GEOIP 复合规则的稳定性也不能通过官方普通域名性能数字推断。用户希望同时实现国内直连、海外正确选路、VPN 稳定和 DNS 不泄漏；直到找出触发原因并在设备上复测，这些目标仍不可宣称全部完成。

**本 PR 仅为定位工具，不修改正式 v6.5.8 发布文件，不应合并成正式修复。** 静态回归测试检查每份诊断配置严格只改变目标订阅是否加载。
