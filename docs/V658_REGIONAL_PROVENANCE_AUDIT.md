# v6.5.8 地区逻辑规则来源、Loon 兼容性及实机结论

## 结论

这六份 **不是 Loon 官方分流表**，而是 LoonKit 将原始合并规则和维护者审核配方转成 `AND,(DOMAIN/GEOIP)` 或 `AND,(DOMAIN/NOT(GEOIP))` 的地区规则。官方 Loon 确实支持逻辑语法，不表示数千条复合列表已由官方做性能、稳定性或 DNS 隐私背书。

用户已在 iOS 的 Loon 实际测试：

| 在另外 31 份远程订阅始终不变的基础上，六份中的加载组合 | 目标复合规则数 | VPN |
| --- | ---: | --- |
| AppleOTA | 82 | 正常 |
| AppleOTA + Bilibili | 210 | 正常 |
| AppleOTA + Bilibili + PayPal | **456** | **正常** |
| 稳定三份 + Microsoft | 1,101 | **重启** |
| 稳定三份 + Apple（不含 Microsoft） | 2,030 | **重启** |
| 稳定三份 + RegionalCN（不含 Microsoft 和 Apple） | 3,009 | **重启** |
| 六份全开 | 5,228 | **重启** |

注意：正常只指“在已测条件下未发生 VPN 重启”，**用户在前三组都报告 DNS 泄漏**；不能把这三份写成 DNS 安全或已经解决分流功能。

## 当前正式 v6.5.8 是如何构建的

仓库 `scripts/release_v658.py` 从 `rules/reviewed/v6.5.8/decisions.json` 读取各资源的冻结路径和 SHA256，调用 `scripts/regional_rules.py::wrap()`：

```ini
# 用于 DIRECT 的 CN 分支
AND,((DOMAIN-SUFFIX,example.com),(GEOIP,CN))

# 用于 Apple / Microsoft / PayPal / Bilibili 等组的非 CN 分支
AND,((DOMAIN-SUFFIX,example.com),(NOT,((GEOIP,CN))))
```

对于 `regional=true` 的服务，生成器将服务域名同时送入 `RegionalCN` 的 CN 匹配候选，并在服务自身列表只保留“非 CN”条件。RegionalCN 汇总来自这些服务的 CN 匹配器，归约重复/被上级后缀覆盖的规则，还追加少数共享 CDN 后缀；不是独立地理数据库。固定提交 URL 的原始发布规则见 `rules/releases/v6.5.8/`，不能为了修复而覆盖历史发布。

## 历史来源目录 `rules/sources.json` 的登记

| 当前订阅 | v6.5.8 的上一层冻结输入 | 记录的历史上游或本地来源（按目录，不保证逐行归属） |
| --- | --- | --- |
| AppleOTA（82） | `rules/releases/vNext-RC2/AppleOTA.list` | blackmatrix7 的 `SystemOTA`；v2fly 的 `apple-update` |
| Bilibili（128） | `rules/releases/vNext-RC2/Bilibili.list` | blackmatrix7 的 `BiliBili`；v2fly 的 `bilibili`、`bilibili-cdn`、`bilibili-game` |
| PayPal（246） | `rules/releases/vNext-RC2/Paypal.list` | blackmatrix7 的 `PayPal`；v2fly 的 `paypal` |
| Microsoft（645） | `rules/releases/v6.5.7/Microsoft.list` | blackmatrix7 的 `Microsoft`；`rules/custom/Microsoft.list` 本地规则 |
| Apple（1,574） | `rules/releases/v6.5.7/Apple.list` | blackmatrix7 的 `Apple`、`Apple_Domain`；felixonmars 的 `apple.china.conf` |
| RegionalCN（2,553） | v6.5.8 生成器对前述服务的 CN 侧组合进行聚合 | **无单独对应上游**；主要是多来源规则的二次合成，并增加 `shared_cn_roots` |

上游项目地址：
- [blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script)
- [v2fly/domain-list-community](https://github.com/v2fly/domain-list-community)
- [felixonmars/dnsmasq-china-list](https://github.com/felixonmars/dnsmasq-china-list)

**来源证据的限制**：`scripts/source_lock.py` 和 `build/sources.lock.json` 将这些历史来源标为 `HISTORICAL_PROVENANCE_UNRECOVERABLE`，冻结的合并快照标为 `FROZEN_MERGED_SNAPSHOT`。这证明输入快照的字节身份，不证明每一条域名的上游来源。因此不能把某个具体 IP/域名都归属到 blackmatrix7、v2fly 或 felixonmars，也不能声称本项目列表由 Loon 官方提供。

## 语法支持 ≠ 运行时可靠

官方参考：[逻辑规则](https://nsloon.app/docs/Rule/logic_rule/)、[规则优先级](https://nsloon.app/docs/Rule/)、[订阅规则](https://nsloon.app/docs/Rule/sub_rule/)、[IP 和 no-resolve](https://nsloon.app/docs/Rule/ip_rule/)、[DNS](https://nsloon.app/docs/DNS/)。

- Loon 3.1.7 起支持 AND/OR/NOT，官方给过域名 + GEOIP 组合的语法示例；远程订阅中每行也必须使用 Loon 支持的规则语法。**但官方的普通 DOMAIN / IP 规则性能基准不能直接证明 2,553 条复合逻辑稳定**。
- Loon 匹配域名规则早于 IP 规则；服务组策略也会影响最终请求路径。使用 GEOIP 条件不表示 DNS 一定可信、无 DNS 泄漏，或所有未解析域名都有正确地区信息。
- 之前两版将顶层 AND 分组/在内层 GEOIP 添加 no-resolve 的实验仍让 VPN 重启，已关闭对应 PR。不能以这些办法冒充已验证修复。
- 接下来应**冻结已测 VPN 稳定的三份组合**作为比较基线，对 Microsoft、Apple、RegionalCN 三份分别进行小批次/原始子规则范围的隔离。是否它们单独也会重启、是否存在 Loon 构建版本的处理问题，目前尚无结论。不要盲目新增 DIRECT 域名规则。

## DNS 泄漏独立处理

v6.5.8 设置普通 `dns-server = 223.5.5.5,223.6.6.6`、加密 `doh-server = https://dns.alidns.com/dns-query` 和 `hijack-dns = *:53`，末尾保留 `GEOIP,CN,DIRECT,no-resolve`、`FINAL,Final`。官方 DNS 文档指出加密 DNS 失败时 App 默认可以退回普通 DNS，需要通过 App 开关核对；节点 DNS、IPv6、应用内 DNS、泄漏测试网站显示的解析器也应核查。**即使三份组合 VPN 正常，也尚未通过 DNS 泄漏验收**。不能用增加/减少服务规则作为 DNS 安全结论。

此报告记录来源与排障事实，并不改动正式发布配置或宣称最终稳定性修复。
