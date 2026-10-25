# v6.5.8 VPN 重启：六份复合规则隔离诊断

**现有用户实机证据**：正式 v6.5.8 的其余配置不变，注释掉这六份规则后，VPN 不再反复重启。这证明问题与这些规则的启用状态有关，但尚不能判定哪一份是唯一诱因，也可能是组合负载、某个逻辑子规则或 Loon 的解析/匹配运行时问题。

本 PR 保留不可变正式版本和 SHA256 校验；不是面向所有用户的正式发布替代品。

## 严格单变量基线

[`LoonKit.Safe.lcf`](../LoonKit.Safe.lcf) **仅从 v6.5.8 删除六条远程订阅配置**：
- `Our-RegionalCN`（2,553 条 AND + GEOIP）
- `Our-AppleOTA`（82 条 AND + NOT + GEOIP）
- `Our-Bilibili`（128 条）
- `Our-Microsoft`（645 条）
- `Our-Apple`（1,574 条）
- `Our-Paypal`（246 条）

剩余 31 个远程订阅、全部 General/DNS/TUN 设置、策略组、`[Rule]`、`GEOIP,CN,DIRECT,no-resolve`、插件和 Host 都与发布版字节级一致。不加入任何国内直连域名、Apple OTA 直连或者临时修改 GeoIP 参数。这样确保测试仅改变六份订阅的加载情况。

## 二分定位（直接导入，无需手写规则）

| 配置 | 启用的六份目标规则 | 目标规则数 |
| --- | --- | ---: |
| [Safe](../LoonKit.Safe.lcf) | 全部禁用（用户已经实测稳定） | 0 |
| [Group A](../diagnostics/v6.5.8/GroupA.lcf) | RegionalCN、AppleOTA、Bilibili | 2,763 |
| [Group B](../diagnostics/v6.5.8/GroupB.lcf) | Microsoft、Apple、Paypal | 2,465 |
| 正式 [v6.5.8](../LoonKit.lcf) | 全部启用（用户报告 VPN 重启） | 5,228 |

1. 在相同 Loon 版本、节点、网络、DNS 与插件设置下，先验证 Safe 仍稳定。
2. 依次使用 Group A 与 Group B 进行短时测试。如果某个组能稳定复现自动重启，就在**那个组**仅启用其中一份目标规则（其余五份禁用）来单独测试；如果单独都稳定，再逐对启用定位交互问题。
3. 如果 A、B 都稳定而全部启用后重启，优先检查六份同时加载的总体开销、跨组交互和 iOS Network Extension 进程的内存限制。**不要直接断言某一份规则有错。**
4. 每次记录 Loon build / iOS 版本、VPN 断开时间、Wi-Fi/蜂窝、节点、规则刷新结果、DNS 解析与系统诊断日志。若有崩溃、Jetsam 或 Extension 异常可提供脱敏记录，不要公开订阅 token。

注意：A 与 B 是从原始正式配置直接保留原规则，不改变任何规则内容。它们仍然可能触发重启；测试期间请在网络可用、数据已保存的环境进行。

## 官方分流口径与完整功能的区别

Loon 官方说明：[匹配优先级](https://nsloon.app/docs/Rule/)、[逻辑规则](https://nsloon.app/docs/Rule/logic_rule/)、[IP 与 no-resolve](https://nsloon.app/docs/Rule/ip_rule/)、[DNS](https://nsloon.app/docs/DNS/)。

- 普通 DOMAIN / DOMAIN-SUFFIX 规则与 IP 规则的匹配阶段有区别。对同一域名的 CN / 海外 CDN 做精确地区判断，无法仅靠把域名映射到 Apple/Microsoft/Paypal/Bilibili 代理组再附加一条 GEOIP 就完全复现；域名规则可能先命中代理策略。因此，地区分流既要关注 DNS 解析结果，也要考虑 Loon 的规则优先级。
- **不要盲目添加 CN 直连清单**。微信与 WeChat 不应混淆，Apple 不应整体强制直连，DNS 查询无法被堆叠 DIRECT 规则消除。必要时结合实际 DNS 的 A/AAAA、CNAME、GeoIP、使用的策略与代理节点排查。ECS 是否有效取决于解析器、上游及客户端网络。
- 六组全部关闭的 Safe 是**定位手段**，暂时丧失这六组的精细地区自动分流。这不代表已经完整解决原定的 Apple / Microsoft / PayPal 分流目标。需要先锁定崩溃源，再考虑少量经过实机验证的逻辑规则或按部署证据做最小化服务分流。
- v6.5.8 的 50 条宽泛 `USER-AGENT` 已移除，无需在此重新解决同一问题。
- DNS 泄漏防护尚未完成端到端验收：虽已设置 AliDNS DoH 与 DNS 劫持，仍需在 **Loon → DNS 服务器**关闭加密 DNS 失败时回退普通 DNS，并检验网络切换、IPv6 和客户端自带 DNS。只检查 .lcf 不足以证明无泄漏。
- 上游更新的真实写入 PR、GitHub 权限和 CI dispatch 仍需使用**真实且经过审核的新增规则**完成独立端到端测试；不能将单元测试当作写入流程已经验证。

此文档和测试配置不会替代生产发布门禁。问题在设备复现并定位后，再单独提交一个功能修复 PR，审查服务规则、DNS 路由差异和发布不可变性。
