# 六份 GEOIP 复合规则导致 VPN 重启：单变量定位（v6.5.8）

## 最新实机反馈（2026-10-25）

- 用户最新明确反馈：**Group A（RegionalCN + AppleOTA + Bilibili）与 Group B（Microsoft + Apple + PayPal）均触发 VPN 自动关闭/重启**。此前一度反馈 Group A 没有重启，后来明确更正为两组都有该问题。DNS 泄漏也曾在 Group A 测试中观察到，但不得由此推断是某一份订阅导致。
- **OnlyAppleOTA**（六份可疑中仅加载 AppleOTA 的 82 条原始复合规则）：实机报告 **没有 VPN 重启**。这仅证明该单份规则在本次测试条件下不触发故障，不代表 DNS 已通过。
- 新增两份按规则条数递增的候选：**AppleOTA_Bilibili**（82 + 128 = 210 条），**AppleOTA_Bilibili_Paypal**（82 + 128 + 246 = 456 条）。按顺序测试，前一份若重启，先停止，避免继续增加混杂变量。两份配置始终保留原始 DNS/TUN、GeoIP/no-resolve 和所有 31 份非目标规则。
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

1. 已确认 **OnlyAppleOTA 单独启用时 VPN 没有重启**。先导入 **AppleOTA_Bilibili**（新增 Bilibili 的 128 条），刷新远程订阅，验证实际上只加载六份目标规则中的两份。
2. 若第一份在同样使用场景下未重启，再导入 **AppleOTA_Bilibili_Paypal**（再加 PayPal 的 246 条）。若第一份已经重启，就停止递增，接下来单独测试 OnlyBilibili，而非继续增加更多规则。
3. 若两份都稳定，才根据增加数量最少的顺序考虑 Microsoft（645 条）、Apple（1,574 条）和 RegionalCN（2,553 条）；但 Group A 与 Group B 均重启的结果意味着之后还需排查组合交互。
4. DNS 泄漏单独记录，不随意去掉 `GEOIP,CN,DIRECT,no-resolve`。对照六份全关闭的 [None.lcf](../diagnostics/v6.5.8-geoip-six/None.lcf)，避免把 VPN 稳定与 DNS 不泄漏混为一谈。

**每次测试记录**：是否正常导入、六份中实际启用哪几份、规则刷新是否出错、最短复现间隔、iOS 诊断分析中的 Network Extension 退出或 Jetsam 记录，并对比 DNS 测试结果。注意不要公开付费节点、订阅 Token 和设备标识。

## 为什么此 PR 还不能算完成地区分流修复

Loon 对域名规则的匹配优先于 IP 规则；对于同一服务既有 CN 又有海外部署的域名，要根据实际 IP 归属决定路由，不能简单把全部 Apple/Microsoft/PayPal 域名静态设为 DIRECT。反过来，五千多条 GEOIP 复合规则的稳定性也不能通过官方普通域名性能数字推断。用户希望同时实现国内直连、海外正确选路、VPN 稳定和 DNS 不泄漏；直到找出触发原因并在设备上复测，这些目标仍不可宣称全部完成。

**本 PR 仅为定位工具，不修改正式 v6.5.8 发布文件，不应合并成正式修复。** 静态回归测试检查每份诊断配置严格只改变目标订阅是否加载。
