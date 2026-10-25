# v6.5.8 六份复合规则兼容性优化（实验候选）

**目标**：在不删除六份订阅、不破坏 Apple/Microsoft/PayPal/Bilibili 的 CN/非 CN 分流条件、且不修改 DNS/GeoIP/Final 设置的前提下，降低数千条独立 AND + GEOIP 复合规则造成的运行负载。用户在 v6.5.8 关闭六份规则后曾实测 VPN 稳定，说明问题与这六份订阅或其共同负载有关；无法仅凭静态代码确定是哪一个具体条件使 iOS VPN Extension 重启。

## 导入测试版

候选配置为 [`LoonKit.CompositeFix.lcf`](../LoonKit.CompositeFix.lcf)。其中六份订阅都处于 `enabled=true`，标签、策略和在远程规则中的顺序完全不变，仅指向本 PR 新增的 `rules/experiments/v6.5.8-geoip-batched/*.list`。六份链接固定在 commit `ec84df35613c56d01639cd0140307148af0d1258`，便于追溯内容。其他订阅以及正式版 `LoonKit.lcf`、manifest 和已有 SHA256 不改变。

### 重写规则的方法

Loon 官方 [逻辑规则](https://nsloon.app/docs/Rule/logic_rule/) 支持 AND/OR/NOT 与嵌套条件。把不超过八条同类域名条件的

```ini
AND,((DOMAIN-SUFFIX,example.com),(NOT,((GEOIP,CN))))
AND,((DOMAIN-SUFFIX,example.net),(NOT,((GEOIP,CN))))
```

转换为：

```ini
AND,((OR,((DOMAIN-SUFFIX,example.com),(DOMAIN-SUFFIX,example.net))),(NOT,((GEOIP,CN))))
```

该转换在布尔逻辑上遵循 `(A ∧ G) ∨ (B ∧ G) = (A ∨ B) ∧ G`。每份文件原有子匹配器及顺序、GeoIP 方向 (CN 或非 CN) 均保留。为控制兼容性风险，每个 OR 限最多 8 条，仅对 `DOMAIN` / `DOMAIN-SUFFIX` 合并；`IP-CIDR`、`IP-CIDR6`、`IP-ASN` 条目保持原样。顶层复合表达式合计从 **5228** 条降至 **696** 条（338、11、24、82、210、31）。**这并不意味着 DNS 查询次数减少 86.7%，也不保证性能按同一比例提升。**

## 网络隐私及原有行为

- 主配置保留 **`GEOIP,CN,DIRECT,no-resolve` + `FINAL,Final`**，不使用导致用户在 Safe 配置中观察到 DNS 泄漏的无 `no-resolve` 变体。
- `dns-server`、`doh-server`、`hijack-dns`、`real-ip`、`ip-mode`、`ipv6-vif`、`interface-mode`、DNS 失败回退 App 设置均不调整，不新增未经验证的 DIRECT 域名或 IP。
- **逻辑规则中的 `GEOIP,CN` 仍可能要求 DNS 解析**，所以仍需做真实 DNS 泄漏测试。这项重写仅将重复 GeoIP 逻辑组合起来，并不承诺彻底消除 DNS 查询；Loon 官方 [DNS 文档](https://nsloon.app/docs/DNS/) 说明默认情况下加密 DNS 失败会回退普通 DNS，需在 App 的 DNS 页面关闭该回退。
- 地区路由语义的静态等价性依赖 Loon 对嵌套 OR/AND 的实际支持；这次测试只证明子匹配器和逻辑表达式等价，不代表已通过设备上的 Loon 解析器测试。

## 验收顺序

1. 备份目前已知不会反复重启、且 DNS 泄漏测试通过的配置，记录 Loon build、iOS 版本、网络环境和代理节点。
2. 导入 `LoonKit.CompositeFix.lcf`，刷新六份实验订阅，核对均启用且没有规则下载/解析错误；观察 VPN 是否仍会关闭后自动开启。
3. 在同一网络与相同 App 开关下，比较 DNS 泄漏测试结果，并分别检查 `apple.com`、`icloud.com`、`microsoft.com`、`paypal.com`、`bilibili.com` 等请求的解析 IP、国家、实际命中规则及所选策略。检查 CN 与非 CN 的实际连接，不能把看到代理视为泄漏。
4. 如仍重启，使用 [原始 6 份规则二分诊断](./SAFE_ROUTING.md) 或设备日志继续定位。iOS 系统分析中的 Jetsam / VPN Extension 重启记录比静态推测更可靠。
5. 等实机证明此配置能稳定运行、DNS 测试无回退泄漏且分流策略符合预期后，再依据仓库正式发布门禁做下一版本，不覆盖 v6.5.8 历史发布。

## 自动化校验

`tests/test_composite_geoip_batch.py` 检查六份文件完整覆盖原始 matcher、条件极性和顺序，限制 OR 组合的规模，核对六条远程订阅全部仍启用及原始 DNS/General/Rule/Plugin 等配置不变。真实运行时重启与 DNS 泄漏问题依赖真机验证。
