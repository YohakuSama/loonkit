# 六份 GEOIP 复合规则导致 VPN 重启：单变量定位（v6.5.8）

## 最新实机反馈（2026-10-25）

- 用户最新明确反馈：**Group A（RegionalCN + AppleOTA + Bilibili）与 Group B（Microsoft + Apple + PayPal）均触发 VPN 自动关闭/重启**。此前一度反馈 Group A 没有重启，后来明确更正为两组都有该问题。DNS 泄漏也曾在 Group A 测试中观察到，但不得由此推断是某一份订阅导致。
- 用户已经测试 **OnlyAppleOTA（82 条）**、**AppleOTA + Bilibili（210 条）**、**AppleOTA + Bilibili + PayPal（456 条）** 三档：在已测条件下均没有 VPN 重启，**但三档都报告 DNS 泄漏**。这些结果不能证明 DNS 已修复，不能用添加更多远程服务规则来掩盖泄漏。
- 新增递增测试 **AppleOTA_Bilibili_Paypal_Microsoft**（456 + 645 = **1,101** 条）和 **AppleOTA_Bilibili_Paypal_Microsoft_Apple**（1,101 + 1,574 = **2,675** 条）。必须先测试 Microsoft 版；若触发重启，则暂停增加 Apple，并单独验证 Microsoft 或组合问题。最后一份 RegionalCN（2,553 条）加回即恢复 5,228 条的原始正式 v6.5.8（此前已知会重启），**无需再次冒险直接导入全六份**。
- 三份已实测失败的规则变体：正式 v6.5.8（六份全开）、OR 分组 PR #138、内层 no-resolve PR #139。继续改写语法缺乏可用证据，优先做累加隔离。

### DNS 泄漏应另行对照

仓库核对确认原始 v6.5.8、Group A、Group B、OnlyAppleOTA 和新递增配置的 `[General]`、`[Host]`、`[Rule]` 完全一致。仍保留：

```ini
GEOIP,CN,DIRECT,no-resolve
FINAL,Final
```

因此不能仅凭本次分组的 DNS 泄漏测试就确定源头，需记录实际 DNS 解析器 IP/ASN、网络传输、IPv6、App 内加密 DNS 失败回退开关。Loon DNS 文档：https://nsloon.app/docs/DNS/ 。

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
| [AppleOTA_Bilibili.lcf](../diagnostics/v6.5.8-geoip-six/AppleOTA_Bilibili.lcf) | AppleOTA、Bilibili（210 条） | 33 |
| [AppleOTA_Bilibili_Paypal.lcf](../diagnostics/v6.5.8-geoip-six/AppleOTA_Bilibili_Paypal.lcf) | AppleOTA、Bilibili、PayPal（456 条） | 34 |
| [AppleOTA_Bilibili_Paypal_Microsoft.lcf](../diagnostics/v6.5.8-geoip-six/AppleOTA_Bilibili_Paypal_Microsoft.lcf) | 再加 Microsoft（1,101 条） | 35 |
| [AppleOTA_Bilibili_Paypal_Microsoft_Apple.lcf](../diagnostics/v6.5.8-geoip-six/AppleOTA_Bilibili_Paypal_Microsoft_Apple.lcf) | 再加 Apple（2,675 条） | 36 |
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

## 当前最少的有效实机测试顺序

1. 三份小规模原始规则组合（82/210/456 条）**已实测 VPN 稳定，但都有 DNS 泄漏**。现在从 456 条配置递增，先导入 `AppleOTA_Bilibili_Paypal_Microsoft.lcf`（1,101 条），刷新订阅并确认目标四份启用。
2. **只有 Microsoft 递增版不重启时**，才使用 `AppleOTA_Bilibili_Paypal_Microsoft_Apple.lcf`（2,675 条）。如果某一级出现 VPN 自动重启，应停止添加，不要继续升到下一档；定位本次新增规则集与前面组合之间的关系。
3. **RegionalCN（2,553 条）尚未加入这些递增测试**。加入它后会回到已知重启的正式 v6.5.8 全六份状态；如果前五份均稳定，应优先独立测试 `OnlyRegionalCN.lcf`，再考虑与其他规则组合的最小触发集，不要直接尝试全六份。
4. **DNS 泄漏是单独未通过的验收项目**。Loon 官方说明同时配置普通 DNS 和 DoH 时优先使用加密 DNS，但默认 DoH 失败允许回退普通 DNS。须在 Loon App 的 DNS 服务器设置中检查并关闭“加密 DNS 失败时回退普通 DNS”（按需先备份设置），比较 `None.lcf` 与三份已测方案在同一网络/节点/站点显示的实际 DNS 解析器 IP、流量来源和 IPv6。静态配置相同不证明真实 DNS 路径安全；本轮增加规则**不会修复 DNS 泄漏**。<https://nsloon.app/docs/DNS/>

**每次测试记录**：是否正常导入、六份中实际启用哪几份、规则刷新是否出错、最短复现间隔、iOS 诊断分析中的 Network Extension 退出或 Jetsam 记录，并对比 DNS 测试结果。注意不要公开付费节点、订阅 Token 和设备标识。

## 为什么此 PR 还不能算完成地区分流修复

Loon 对域名规则的匹配优先于 IP 规则；对于同一服务既有 CN 又有海外部署的域名，要根据实际 IP 归属决定路由，不能简单把全部 Apple/Microsoft/PayPal 域名静态设为 DIRECT。反过来，五千多条 GEOIP 复合规则的稳定性也不能通过官方普通域名性能数字推断。用户希望同时实现国内直连、海外正确选路、VPN 稳定和 DNS 不泄漏；直到找出触发原因并在设备上复测，这些目标仍不可宣称全部完成。

**本 PR 仅为定位工具，不修改正式 v6.5.8 发布文件，不应合并成正式修复。** 静态回归测试检查每份诊断配置严格只改变目标订阅是否加载。
