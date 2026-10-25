# 六份 GEOIP 复合规则导致 VPN 重启：单变量定位（v6.5.8）

## 2026-10-25 最新实机结论：Microsoft 加入后复现重启

| 六份可疑订阅的加载组合 | 复合规则数 | VPN | DNS 泄漏 |
| --- | ---: | --- | --- |
| AppleOTA | 82 | 用户测试正常 | 用户报告泄漏 |
| AppleOTA + Bilibili | 210 | 用户测试正常 | 用户报告泄漏 |
| AppleOTA + Bilibili + PayPal | 456 | **用户测试正常** | 用户报告泄漏 |
| **上述三项 + Microsoft** | **1,101** | **用户确认发生 VPN 重启** | 暂不判断 |
| 上述三项 + Apple（明确不加 Microsoft） | **2,030** | **待测试** | 待测试 |
| 上述四项 + RegionalCN（仍不加 Microsoft） | **4,583** | **待测试** | 待测试 |

**Microsoft 被列为优先排查的复合规则集。** 原始发布资源是 `rules/releases/v6.5.8/Microsoft.list`，含 **645 条** AND/NOT/GEOIP 复合规则。严格意义上，当前只证明在原先 456 条稳定组合上**增加 Microsoft 就复现重启**，尚未证明 Microsoft 规则单独运行必定异常。独立验证文件仍有 `diagnostics/v6.5.8-geoip-six/OnlyMicrosoft.lcf`；稍后可据此判断是单份故障还是组合问题。

为避免重复复现已知问题，新增两份**排除 Microsoft** 的累加对照文件：
- `AppleOTA_Bilibili_Paypal_Apple.lcf`：维持已稳定的三份，加入 Apple 的 1,574 条规则，仍禁用 Microsoft 和 RegionalCN。
- `AppleOTA_Bilibili_Paypal_Apple_RegionalCN.lcf`：在上一版基础上加入 RegionalCN 的 2,553 条规则；Microsoft 始终禁用。

**测试顺序**：先 Apple 版；只有 Apple 版 VPN 不重启时再测试 RegionalCN 版。如果第一份发生重启，停止加量，优先单独测试 `OnlyApple.lcf`。如果第一份稳定、第二份重启，则优先单独测试 `OnlyRegionalCN.lcf`。这不等价于完成故障修复，亦不保证 DNS 安全。

所有上述配置仅改变原始六项订阅的启用范围；保持原版其他 31 份订阅、原有 `GEOIP,CN,DIRECT,no-resolve`、`FINAL,Final`、DoH/TUN、规则标签及策略、Host 与插件不变。**DNS 泄漏是独立未通过项，不靠继续添加服务域名规则解决**。可用同条件 `None.lcf` 测量泄漏基线，并核对 Loon App 内加密 DNS 失败回退开关与 DNS 测试报告的解析器 IP。


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
| [AppleOTA_Bilibili_Paypal_Apple.lcf](../diagnostics/v6.5.8-geoip-six/AppleOTA_Bilibili_Paypal_Apple.lcf) | AppleOTA、Bilibili、PayPal、Apple（2,030 条；禁用 Microsoft） | 35 |
| [AppleOTA_Bilibili_Paypal_Apple_RegionalCN.lcf](../diagnostics/v6.5.8-geoip-six/AppleOTA_Bilibili_Paypal_Apple_RegionalCN.lcf) | 除 Microsoft 外其他五项（4,583 条） | 36 |
| [OnlyApple.lcf](../diagnostics/v6.5.8-geoip-six/OnlyApple.lcf) | Apple | 32 |
| [OnlyPaypal.lcf](../diagnostics/v6.5.8-geoip-six/OnlyPaypal.lcf) | Paypal | 32 |

始终保持：

```ini
GEOIP,CN,DIRECT,no-resolve
FINAL,Final
```

以及完整 `[General]` 的 DNS、DoH、`hijack-dns`、`ip-mode`、IPv6，`[Host]`、`[Proxy Group]`、`[Plugin]`、其余远程资源不变。没有新增 CN DIRECT 域名或静态 IP 表，也没有修改 Apple/Microsoft/PayPal 默认策略。

## 当前最少的有效实机测试顺序

1. 在 456 条稳定组合加入 Microsoft（总计 1,101 条）后**已实测 VPN 重启**。因此暂时不再添加 Microsoft，先导入 [AppleOTA_Bilibili_Paypal_Apple.lcf](../diagnostics/v6.5.8-geoip-six/AppleOTA_Bilibili_Paypal_Apple.lcf) 测试新增 Apple 后的 VPN 稳定性。
2. **只有 Apple 版不重启时**，再导入 [AppleOTA_Bilibili_Paypal_Apple_RegionalCN.lcf](../diagnostics/v6.5.8-geoip-six/AppleOTA_Bilibili_Paypal_Apple_RegionalCN.lcf) 测试 RegionalCN。若任一步重启，停止加量并单独测试新增的规则集。
3. 如两份不含 Microsoft 的配置都稳定，再通过 [OnlyMicrosoft.lcf](../diagnostics/v6.5.8-geoip-six/OnlyMicrosoft.lcf) 或 Microsoft 的规则行二分确定它单独还是与其他订阅组合时触发，不直接修改 immutable v6.5.8 原文件。
4. **DNS 泄漏另行对照**，不要误把 VPN 不重启解释为 DNS 安全。静态 DNS 参数在这些配置中完全一致；检查 Loon 加密 DNS 失败回退开关、实际解析器 IP、IPv6、节点解析及对照 [None.lcf](../diagnostics/v6.5.8-geoip-six/None.lcf) 的结果。不能依靠给域名加 DIRECT 来消除 DNS 查询。

**每次测试记录**：是否正常导入、六份中实际启用哪几份、规则刷新是否出错、最短复现间隔、iOS 诊断分析中的 Network Extension 退出或 Jetsam 记录，并对比 DNS 测试结果。注意不要公开付费节点、订阅 Token 和设备标识。

## 为什么此 PR 还不能算完成地区分流修复

Loon 对域名规则的匹配优先于 IP 规则；对于同一服务既有 CN 又有海外部署的域名，要根据实际 IP 归属决定路由，不能简单把全部 Apple/Microsoft/PayPal 域名静态设为 DIRECT。反过来，五千多条 GEOIP 复合规则的稳定性也不能通过官方普通域名性能数字推断。用户希望同时实现国内直连、海外正确选路、VPN 稳定和 DNS 不泄漏；直到找出触发原因并在设备上复测，这些目标仍不可宣称全部完成。

**本 PR 仅为定位工具，不修改正式 v6.5.8 发布文件，不应合并成正式修复。** 静态回归测试检查每份诊断配置严格只改变目标订阅是否加载。
