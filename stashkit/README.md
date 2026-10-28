# StashKit

基于 [LoonKit](../README.md) **v7.0.10** 生产分流的 Stash 原生 YAML 适配版。当前是与 LoonKit 并行的独立配置目录；不会修改原来的 LoonKit.lcf。

> **状态**：已完成静态规则转换和自动化校验体系；导入到真实 Stash 客户端及网络连接测试仍需要设备验收。请先确认 CI 通过后再用于常用设备。

## 导入配置

**Stash 完整配置（主分支发布后生效）：**

`https://raw.githubusercontent.com/YohakuSama/loonkit/main/stashkit/StashKit.yaml`

在 Stash 的配置文件管理中通过 URL 下载，或下载 [StashKit.yaml](./StashKit.yaml) 再导入。

- **必须自行添加节点或兼容 Clash/Stash 的远程节点订阅**。本项目不含个人订阅 URL、凭据或真实节点。
- 可使用 [节点订阅覆写示例](./overrides/provider.stoverride.example)（复制为 .stoverride，替换 URL 后再导入、启用）。覆写里的 `proxy-providers` 会与主配置合并，`include-all` 会使节点加入 ALL、Auto、Fallback。订阅必须是包含 `proxies:` 的合法代理集；不保证所有机场原生订阅可直接使用，必要时应先转换成 Stash 支持的格式。
- 在 Stash 策略页手动核对 **Proxy、ALL、Auto、Fallback** 和需要特定地区的 AI/流媒体服务。不要只凭测速判定地区解锁。

**默认不含节点**：Auto / Fallback / ALL 显式使用 REJECT 作为空节点保护，避免在未配置节点时自动成为 DIRECT。加入订阅后，应在 Stash 策略页确认有可用节点，并测试失败切换逻辑。

## 与 LoonKit 的对应关系

- **40 个策略组**：LoonKit 的 39 组完整迁移，另将 `ALL_Filter` 映射为 Stash 的 `ALL` 手动节点池。Proxy / Auto / Fallback / AdBlock / Final 和 34 个服务组保留原有首选项。
- **43 个生产远程规则来源 → 54 个 Stash rule-providers**，合计 **196,561** 条匹配器。规则来源、分类、顺序按 LoonKit 的 [release_manifest.json](../build/release_manifest.json) 冻结。
- **规则转换**：`DOMAIN` → 精确域名；`DOMAIN-SUFFIX` → `+.后缀`（Stash domain text）；`IP-CIDR` / `IP-CIDR6` → Stash ipcidr text；`IP-ASN,...,no-resolve` → 原生 classical text。IP 子规则的 `no-resolve` 在主配置 `RULE-SET` 中保留。
- **性能**：广告拦截 76,895 条、ChinaDirect 114,705 条均拆为低内存的 domain/ipcidr 类型。绝不把两大规则集直接作为大型 classical 规则加载。
- **内置规则**：LoonKit 的 GitHub Raw、Gemini / Copilot / TRAE 显式路由，以及 GeoIP CN / Final 兜底保留。
- **DNS**：按 LoonKit 国内使用场景采用 AliDNS DoH + Fake-IP；Stash DNS 查询默认直连，Fake-IP 不代表全部 DNS 走代理，也不能保证绝对无泄漏。
- **未迁移**：Loon 的 Network_Diagnostics.plugin / 专属脚本和 Loon 特有网络设置不是 Stash 原生 YAML 组件，未假装兼容。

## 规则集与引用可靠性

本目录下的 `rules/` 存放 **Stash 原生 text 规则文件**，`StashKit.yaml` 引用同一个仓库 main 分支的 Raw 文件，不直接把不支持的 `.lsr` 当 domain provider 用。

每份源资产从冻结的 LoonKit 生产文件转换，保留无重复、顺序和目标策略。**主分支 URL 只有在本目录合并到 main 后才可使用**；PR/开发分支不能作为长期订阅地址。

| 类型 | 数量 | 用途 |
| --- | ---: | --- |
| `domain + text` | 43 | 大部分服务 / 国内直连 / 广告 |
| `ipcidr + text` | 7 | 含 IPv4/IPv6 的服务 |
| `classical + text` | 4 | 原生 ASN 小集合，保留 no-resolve |
| **总计** | **54** | 规则条目数合计 196,561 |

Stash 原生格式说明：[规则集合](https://stash.wiki/rules/rule-set)、[策略组](https://stash.wiki/proxy-protocols/proxy-groups)、[远程代理集](https://stash.wiki/proxy-protocols/proxy-providers)。

## DNS 与节点故障排查

1. 首先确认服务对应策略组实际选择了节点，避免误选 DIRECT。
2. 访问不了海外服务时，查看 Stash 请求记录，核对命中规则和 DNS 结果；针对 AI、流媒体还须验证节点地域、出口与解锁。
3. 出现 DNS 泄漏担忧时，注意默认 `dns.nameserver` 的 DoH 请求仍可能直连。Fake-IP 仅避免一部分本地提前解析，不能检测应用自带 DoH/DoT、VPN 绕过等情况。
4. iOS 设备容量和内存不同；虽然规则已转为低内存格式，不能仅凭静态校验保证内存、速度或所有网站都正常。

## 校验与维护

- CI：[`stashkit-ci.yml`](../.github/workflows/stashkit-ci.yml)
- 本地（Python 3.10+）：`python -m pip install PyYAML && python stashkit/scripts/verify.py`
- 重建资源：`python stashkit/scripts/build_rules.py`（从当前生产 manifest 和源规则生成文件，然后更新主配置，运行校验并逐项设备验收）。
- 校验范围：源文件 SHA-256、43 组规则条数和重复项、全量规则逐条对应、YAML 键重复、54 规则文件 URL/类型、域名及 IP 语法、全部策略组的引用、策略匹配顺序、no-resolve。
- **设备验收**：Stash 配置导入、54 个资源更新状态、DNS、节点测速、广告拦截、AI 服务访问和流媒体地区策略必须在 iOS/macOS 实测。未完成时不标注“已实际验证”。

## 许可

遵循 LoonKit 根目录 [GPL-2.0-only](../LICENSE) 及 [第三方声明](../docs/THIRD_PARTY_NOTICES.md)；规则仍保留原始来源和维护边界。请勿提交含账号、密钥、私人订阅地址的覆写文件。
