# 分流规则：匹配范围与策略归属

LoonKit 根据本地规则与远程规则，将请求交给对应策略组。生效清单以 [LoonKit.lcf](../LoonKit.lcf) 和自动生成的 [release_manifest.json](../build/release_manifest.json) 为准；资源目录名称（例如 `v7.0.3`）表示规则资产的版本，并不等于正式配置版本。

## 规则如何参与选路

- **本地显式域名**：例如 `raw.githubusercontent.com` 命中 `Proxy`，TRAE 的指定海外 API 命中 `AI`；Copilot 相关请求由本地规则显式交给 AI。加密货币域名不再内嵌于本地规则。
- **远程分类订阅**：44 份固定规则按当前配置声明的顺序，将国内常用服务、AI、视频、社交、广告与共享基础设施分别指向 `DIRECT`、服务策略组、`AdBlock` 或 `Proxy`。Crypto 的独立订阅置于广告拦截之后、国内直连之前，包含 219 条 Loon 原生域名规则，不含宽泛关键词。
- **补充服务分流**：夸克（quark.cn、myquark.cn）及子域名直连，维基百科与 Wikimedia 相关域名、多邻国国际站（duolingo.com）走代理。它们分别归入原有的 DomesticSupplement 与 SharedInfrastructure 远程订阅，没有新增独立规则库或策略组，也没有模糊关键词；多邻国中国站不在国际规则范围内。
- **兜底**：`GEOIP,CN,DIRECT,no-resolve` 处理已有目标 IP 可以判断为 CN 的请求；其余落入 `FINAL,Final`。`no-resolve` 不应被解释为可以识别所有国内域名。
- **优先级注意**：更具体的服务资源与通用资源之间存在覆盖关系。当前规则对 GitHub Copilot、YouTube、Speedtest 等范围进行了有意划分；不能只看最终 `Final` 组来推断所有命中结果。

具体匹配顺序和归属应以 Loon 的请求记录为准，**页面分类不等于每个域名必然走固定出口**：策略组在 App 内仍可由用户改选。

策略组按基础选路、AI、平台服务、金融（`Crypto` / `Paypal`）、流媒体、社交及游戏排列；页面排序不改变远程规则匹配的优先级。

## 哪些选择是用户可改的

| 策略或行为 | 当前含义 |
| --- | --- |
| `Proxy`、`Auto`、`Fallback` | 决定策略最终使用的节点；筛选、测速与回退顺序见[节点选择](../docs/NODE_SELECTION.md)。 |
| Apple、Microsoft、Bilibili、Line、Speedtest | 对应策略组默认优先 `DIRECT`，用户可按需改选。 |
| **Crypto 默认使用 `Proxy`** | 经审查的 219 条固定远程域名规则（含原 29 个根域）匹配 `Crypto`，该策略组不提供 `DIRECT`。广告遥测域名仍先命中 AdBlock；纯 IP 连接与未收录域名不受 Crypto 订阅保障。 |
| **Paypal 默认使用 `Proxy`** | PayPal 所属规则命中服务策略；默认选路不等于保证所有请求都经代理。 |
| `AdBlock` | 相关订阅按拒绝策略处理；将子策略改为 `DIRECT` 不会让已命中 `REJECT` 的规则自动恢复匹配，排查时要核对实际规则和订阅。 |
| `Final` | 没有被前述规则处理的流量由此组决定。 |

## 规则资源从哪里来

| 位置 | 作用 |
| --- | --- |
| [release_manifest.json](../build/release_manifest.json) | 当前生效的远程资源 URL、顺序、目标策略、数量与校验摘要。 |
| [sources.json](./sources.json)、[inputs/](./inputs/) | 上游来源登记与冻结输入，不是直接安装入口。 |
| [releases/v7.0.13/Crypto.lsr](./releases/v7.0.13/Crypto.lsr) | Crypto 的独立远程订阅，固定到审核通过的 Git 提交；源自 blackmatrix7 的 GPL-2.0 规则，经审核去除关键词、过时或非专属平台并补充现役服务。 |
| [releases/v7.0.13/AdBlockBalanced.lsr](./releases/v7.0.13/AdBlockBalanced.lsr) | 与原 AdBlock 规则仅差 1 条：移除误拦 `coincheck.com` 主页；广告遥测子域名仍保留拦截。 |
| [releases/v7.0.16/Apple.lsr](./releases/v7.0.16/Apple.lsr) | Apple Intelligence 与 Siri 的私有云计算域名归入 Apple，AppleOTA 和 Apple 两份订阅优先于 Cloudflare。 |
| [releases/v7.0.3/](./releases/v7.0.3/)、[releases/v7.0.5/](./releases/v7.0.5/) | 其他历史远程规则快照，继续使用固定提交。 |
| [releases/v7.0.15/DomesticSupplement.lsr](./releases/v7.0.15/DomesticSupplement.lsr)、[SharedInfrastructure.lsr](./releases/v7.0.16/SharedInfrastructure.lsr) | 复用现有国内补充与通用代理分类，仅更新对应资源的固定快照；原有订阅总数不变。 |
| [reviewed/v6.5.8/decisions.json](./reviewed/v6.5.8/decisions.json) | 历史规则归属的审阅记录。 |
| [Beta 上游审核](../docs/BETA_UPSTREAM_AUTOMATION.md) | 候选来源的审阅流程，不会直接替换正式配置。 |

当前规则使用 Loon 原生的 `DOMAIN` / `DOMAIN-SUFFIX` 等匹配项，未保留以前按同一域名的 CN / 非 CN 解析目标切换策略的复合表达式；也不把共享 CDN 根域随意归给某个服务。来源处理边界见[规则审阅](../docs/RULE_SAFETY.md)。

## 出现误分流时

按 **请求记录中的命中规则 → 归属的策略组 → 策略组当前选中节点 → 实际连接结果** 顺序检查。加密货币平台请先确认请求域名确实命中 `Crypto`；第三方 CDN、未收录的 API 域名和直接使用 IP 的连接不一定命中 Crypto 订阅。能解析域名不代表正确分流，能选节点也不代表目标服务接受该出口。如果问题只发生在 DNS 解析阶段，转到[DNS 专题](../docs/DNS_PRIVACY.md)。

[返回首页](../README.md) · [规则审阅](../docs/RULE_SAFETY.md)
