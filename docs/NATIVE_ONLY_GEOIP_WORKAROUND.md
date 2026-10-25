# 2026-10-25 · 六份 GEOIP 复合列表的 Loon 原生规则替代实验

**用户真机最新观察**：在 v6.5.8 中，请求**实际命中**原先六份列表中的 `AND + GEOIP` / `AND + NOT(GEOIP)` 逻辑规则时，VPN 会断开并反复重启。小规则组合仅在没有触发相关匹配时看似稳定。之前按规则数量或 OR 合并、给 GEOIP 加 no-resolve 的优化在实机均未解决重启。**该观察是因果线索，尚无 iOS Network Extension 退出日志来证明内部根因。**

## 目的

本实验不再尝试让同类复合表达式更短，也不只是关闭订阅，而是让**六份远程订阅全部启用，却没有一条可能命中的 AND/OR/NOT 逻辑表达式**。候选 [`LoonKit.NativeRulesTrial.lcf`](../LoonKit.NativeRulesTrial.lcf) 仅将正式 v6.5.8 的六份订阅 URL 改指向固定提交的实验列表。其余 31 份订阅、Proxy Group、DNS/DoH/TUN、插件、Host、General、`GEOIP,CN,DIRECT,no-resolve` 和 `FINAL,Final` 完全不改。发布版 `LoonKit.lcf` 及不可变 `rules/releases/v6.5.8/` 仍不动。

## 原始到替代的变化

| 订阅 | 原始 GEOIP 复合规则 | 实验普通规则 | 策略 |
| --- | ---: | ---: | --- |
| Our-RegionalCN | 2,553 | 1 | `GEOIP,CN,no-resolve`（remote policy=DIRECT，与现有本地 GeoIP fallback 重复） |
| Our-AppleOTA | 82 | 82 | 保留 `DOMAIN` / `DOMAIN-SUFFIX`，原 Apple 策略 |
| Our-Bilibili | 128 | 120 | 保留域名，跳过原来附带非 CN 判断的 8 条 IP 规则 |
| Our-Microsoft | 645 | 645 | 保留域名，原 Microsoft 策略 |
| Our-Apple | 1,574 | 1,561 | 保留域名，跳过原来附带非 CN 判断的 13 条 IP 规则 |
| Our-Paypal | 246 | 246 | 保留域名，原 PayPal 策略 |

其他五份列表都没有更改原有 `DOMAIN` / `DOMAIN-SUFFIX` 原子条件及其顺序，只是**移除整个 GEOIP 条件**。两个 IP 例外集没有安全的“非 CN”纯 IP 等价条件，因此不直接改为全部代理；RegionalCN 的 2,553 个 CN 服务域名也**没有**被转换成无依据的 DIRECT 规则，以免违背官方建议。其策略通过原有 IP GeoIP fallback 尽可能处理。

### 必须正视的功能退化（不宣称等价）

**普通服务域名规则先于 GEOIP/CN**。对于 Apple/Microsoft/PayPal/Bilibili/AppleOTA 等服务，原来可能根据解析 IP 在 CN 走 DIRECT、在海外走相应服务策略；**现在相同域名即使解析到 CN，也可能先命中服务规则而进入代理策略组**。反过来，来自 RegionalCN 中非服务列表的 CDN，可能落到其它 31 份订阅或 FINAL 而非旧 CN 特定 DIRECT 规则。它不是原先自动精确地域分流的等价实现。

因此：**这只是验证 VPN 是否可安全命中普通域名规则的替代路线，不能作为最终完整地区分流修复立即发布。** 若真实运行稳定，再针对有证据的跨地区节点（域名、DNS CNAME/A/AAAA、策略匹配）逐个收敛名单，无法仅靠标准域名规则+GeoIP fallback 在 Loon 当前匹配优先级下保持同一域名的完整地区自动策略选择。若业务绝对要求该性质，需要向 Loon 官方提供最小复现，等待运行时修复或受支持的新路由能力。

## DNS 与隐私保留

主配置原样保留：
```ini
GEOIP,CN,DIRECT,no-resolve
FINAL,Final
```

没有新增任何 DIRECT 域名规则，未改变 `dns-server = 223.5.5.5,223.6.6.6`、`doh-server = https://dns.alidns.com/dns-query`、`hijack-dns = *:53`、IPv6 或 DNS 回退设置。**用户之前已在“VPN 不重启”的组合里报告 DNS 泄漏，所以此版本绝不能声称 DNS 已修复**。参照 [Loon 官方 DNS](https://nsloon.app/docs/DNS/)，加密 DNS 失败时默认可回退普通 DNS，应在 Loon App DNS 服务器设置中核对并关闭回退；测试实际解析器和应用/系统 DNS 请求，以及 Wi-Fi、蜂窝、IPv6 状态。

## 验收（必须主动触发一条匹配）

1. 在同设备、同 Loon/iOS build、同 Wi-Fi/蜂窝和同节点下备份已有配置，导入 [`LoonKit.NativeRulesTrial.lcf`](../LoonKit.NativeRulesTrial.lcf)，刷新远程规则，确认六份实验列表均成功加载、没有解析错误。名称、policy、顺序与正式配置一致。
2. **不能只观察空闲 VPN**。依次实际访问匹配 AppleOTA、Bilibili、PayPal、Microsoft、Apple 的常用域名。在 Loon 请求日志中确认真实规则命中已切换为普通 `DOMAIN` 或 `DOMAIN-SUFFIX`，同时记录 VPN 是否重启。如实际请求没有命中，则本次测试不能证实复合规则已被正确替换。
3. 分别检查解析到 CN 与非 CN 的目标地址，记录真实命中策略与 IP 地理归属，明确哪些服务被“过度代理”。不能用 VPN 稳定替代地区自动分流验收。
4. 同时进行 DNS 泄漏网站/抓包测试（解析器 IP、UDP 53、IPv6、节点专用 DNS），并对照原先的六项全禁用基线。两个问题独立验收。
5. 如果原生规则命中仍触发 VPN 重启，立即停止这一方向，采集脱敏的 iOS Network Extension 退出/Jetsam 日志及 Loon 规则匹配记录，提交给 Loon 官方。不要再未经验证地增加 DIRECT 域名或 GEOIP 逻辑嵌套。

## 官方参考与来源限制

Loon 官方：[匹配优先级](https://nsloon.app/docs/Rule/) · [普通域名规则](https://nsloon.app/docs/Rule/domain_rule/) · [订阅规则](https://nsloon.app/docs/Rule/sub_rule/) · [IP/GEOIP](https://nsloon.app/docs/Rule/ip_rule/) · [逻辑规则](https://nsloon.app/docs/Rule/logic_rule/)。

这六份由 LoonKit 基于冻结上游合并输入自行生成，**不是 Loon 官方发布**。历史原始上游到逐行域名的来源映射并不完整。详见 [来源审计](https://github.com/YohakuSama/loonkit/blob/diagnostics/geoip-six-isolation-20261025/docs/V658_REGIONAL_PROVENANCE_AUDIT.md)。

静态测试仅验证格式、所有六份仍启用、没有 ANY AND/OR/NOT、正式配置其它内容不变；不代替真实设备稳定性、地区精度和 DNS 安全验收。
