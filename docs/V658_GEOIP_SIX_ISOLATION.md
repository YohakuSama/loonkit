# LoonKit v6.5.8 六份地区复合规则：实机排障记录

**本 PR 不是功能修复，所有历史正式版文件和发布哈希保持不变。** 具体规则来源见 [六份规则来源与 Loon 兼容性审计](./V658_REGIONAL_PROVENANCE_AUDIT.md)。

## 已确认的 VPN 与 DNS 结果

| 目标六份中启用的规则 | 规则数 | VPN | DNS |
| --- | ---: | --- | --- |
| 全禁用（不含六份） | 0 | 用户此前报告正常 | 待与同网络/同站点重测 |
| AppleOTA | 82 | **无重启** | 用户报告泄漏 |
| AppleOTA + Bilibili | 210 | **无重启** | 用户报告泄漏 |
| AppleOTA + Bilibili + PayPal | **456** | **无重启** | **用户报告泄漏** |
| 稳定三份 + Microsoft | 1,101 | **重启** | 未验收 |
| 稳定三份 + Apple（不加 Microsoft） | 2,030 | **重启** | 未验收 |
| 稳定三份 + RegionalCN（不加 Microsoft/Apple） | 3,009 | **重启** | 未验收 |
| Group A：RegionalCN + AppleOTA + Bilibili | 2,763 | **重启** | 曾报告泄漏 |
| Group B：Microsoft + Apple + PayPal | 2,465 | **重启** | 未验收 |
| 全六份 | 5,228 | **重启** | 未验收 |

原始 AppleOTA、Bilibili、PayPal 三份在已测条件下对 **VPN 稳定性暂时可作为基线**。注意，**DNS 测试仍未通过**，不可作为生产安全配置或所有地域分流目标已完成的证据。

三个较大的规则集 — **Microsoft（645）、Apple（1,574）、RegionalCN（2,553）** — 分别加入上述稳定基线都复现重启，但并不能证明它们单独启用也会异常。尤其不能从这些结果直接认定单一行规则语法错误、CPU/内存溢出或某一规则数量阈值。

此前仅修改语法的 OR 分组 PR #138、在内部 GeoIP 添加 no-resolve 的 PR #139 都已被用户实测为失败并关闭，不能重复作为修复提案。

## 现有的原始规则单变量诊断配置

所有文件位于 [`diagnostics/v6.5.8-geoip-six/`](../diagnostics/v6.5.8-geoip-six/)，包括：

| 文件 | 六份中启用的规则 |
| --- | --- |
| [None.lcf](../diagnostics/v6.5.8-geoip-six/None.lcf) | 全不启用（仅用于 DNS/VPN 对照） |
| [OnlyAppleOTA.lcf](../diagnostics/v6.5.8-geoip-six/OnlyAppleOTA.lcf) | AppleOTA（已测） |
| [AppleOTA_Bilibili.lcf](../diagnostics/v6.5.8-geoip-six/AppleOTA_Bilibili.lcf) | AppleOTA + Bilibili（已测） |
| [AppleOTA_Bilibili_Paypal.lcf](../diagnostics/v6.5.8-geoip-six/AppleOTA_Bilibili_Paypal.lcf) | AppleOTA + Bilibili + PayPal（已测 VPN 不重启，但 DNS 泄漏） |
| [OnlyMicrosoft.lcf](../diagnostics/v6.5.8-geoip-six/OnlyMicrosoft.lcf) | 只加 Microsoft，单独验证尚未完成 |
| [OnlyApple.lcf](../diagnostics/v6.5.8-geoip-six/OnlyApple.lcf) | 只加 Apple，单独验证尚未完成 |
| [OnlyRegionalCN.lcf](../diagnostics/v6.5.8-geoip-six/OnlyRegionalCN.lcf) | 只加 RegionalCN，单独验证尚未完成 |
| [OnlyBilibili.lcf](../diagnostics/v6.5.8-geoip-six/OnlyBilibili.lcf) | 只加 Bilibili（可选） |
| [OnlyPaypal.lcf](../diagnostics/v6.5.8-geoip-six/OnlyPaypal.lcf) | 只加 PayPal（可选） |
| [GroupA.lcf](../diagnostics/v6.5.8-geoip-six/GroupA.lcf)、[GroupB.lcf](../diagnostics/v6.5.8-geoip-six/GroupB.lcf) | 两组都已报告重启 |

本分支还保留其他历史递增试验文件以便核对，不应因存在链接而再推荐重复触发重启。

### 不变量

诊断文件只改变六份订阅中加载哪些；原有其他 **31** 个远程订阅、代理策略、节点、General、DNS/DoH/TUN、Host、Plugin 均不变，且统一保留：

```ini
GEOIP,CN,DIRECT,no-resolve
FINAL,Final
```

发布配方、发布资源、SHA256 及正式 `LoonKit.lcf` 不变。回归测试 `tests/test_v658_six_isolation.py` 防止诊断配置无意改动额外设置。

## 之后如何真正修复，而不是让用户反复碰运气

1. **暂时停止继续叠加**。先把三个大型规则集列为未通过稳定性验收。在已确认正常的 456 条稳定基线下，只有在可控、可信的单个来源范围内再做受控拆分。
2. 利用既有单份对照文件分别确认 Microsoft / Apple / RegionalCN 是否能单独触发崩溃；若仍无法定位，用原始单份文件按半区段分割，比较 Loon 规则加载成功、崩溃时间、Network Extension 日志和 Jetsam 状态。不要直接据规则条数或语法猜测根因。
3. 修复必须保留对 CN 与海外部署正确分流的目标，不因为图省事把 Apple/Microsoft/PayPal 全部强制 DIRECT。Loon 官方说明规则优先级中域名规则先于 IP 规则（https://nsloon.app/docs/Rule/）。
4. **DNS 泄漏独立解决**。Loon 官方 DNS 文档（https://nsloon.app/docs/DNS/）指出加密 DNS 失败时默认可以回退普通 DNS。记录 App 内回退开关、DNS 解析器 IP/ASN、IPv6、节点 DNS 和泄漏网站结果；在相同网络及节点下以 None 与 456 条基线比对。不以规则增减替代端到端验收。

此记录只汇总用户实际报告的现象；无法由 GitHub CI 推断真实 iOS VPN 的稳定性。