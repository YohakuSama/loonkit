# 分流规则：匹配范围与策略归属

这里说明 **LoonKit 会把哪些请求交给哪个策略组**，不负责教用户导入配置、选节点或操作 DNS。实际生效清单以 [LoonKit.lcf](../LoonKit.lcf) 和自动生成的 [release_manifest.json](../build/release_manifest.json) 为准；规则资源目录名（例如 `v7.0.3`）是固定资源的历史版本，**不等于当前配置版本**。

## 规则如何参与选路

- **本地显式域名**：例如 `raw.githubusercontent.com` 命中 `Proxy`，TRAE 的指定海外 API 命中 `AI`；Copilot 相关请求由本地规则显式交给 AI。
- **远程分类订阅**：43 份固定规则按当前配置声明的顺序，将国内常用服务、AI、视频、社交、广告与共享基础设施分别指向 `DIRECT`、服务策略组、`AdBlock` 或 `Proxy`。
- **兜底**：`GEOIP,CN,DIRECT,no-resolve` 处理已有目标 IP 可以判断为 CN 的请求；其余落入 `FINAL,Final`。`no-resolve` 不应被解释为可以识别所有国内域名。
- **优先级注意**：更具体的服务资源与通用资源之间存在覆盖关系。当前规则对 GitHub Copilot、YouTube、Speedtest 等范围进行了有意划分；不能只看最终 `Final` 组来推断所有命中结果。

具体匹配顺序和归属应以 Loon 的请求记录为准，**页面分类不等于每个域名必然走固定出口**：策略组在 App 内仍可由用户改选。

## 哪些选择是用户可改的

| 策略或行为 | 当前含义 |
| --- | --- |
| `Proxy`、`Auto`、`Fallback` | 决定策略最终使用的节点；筛选、测速与回退顺序见[节点选择](../docs/NODE_SELECTION.md)。 |
| Apple、Microsoft、Bilibili、Line、Speedtest | 对应策略组默认优先 `DIRECT`，用户可按需改选。 |
| **Paypal 默认使用 `Proxy`** | PayPal 所属规则命中服务策略；默认选路不等于保证所有请求都经代理。 |
| `AdBlock` | 相关订阅按拒绝策略处理；将子策略改为 `DIRECT` 不会让已命中 `REJECT` 的规则自动恢复匹配，排查时要核对实际规则和订阅。 |
| `Final` | 没有被前述规则处理的流量由此组决定。 |

## 规则资源从哪里来

| 位置 | 作用 |
| --- | --- |
| [release_manifest.json](../build/release_manifest.json) | 当前生效的远程资源 URL、顺序、目标策略、数量与校验摘要。 |
| [sources.json](./sources.json)、[inputs/](./inputs/) | 上游来源登记与冻结输入，不是直接安装入口。 |
| [releases/v7.0.3/](./releases/v7.0.3/)、[releases/v7.0.5/](./releases/v7.0.5/) | 现役规则所引用的固定资产；路径内版本反映资源生成批次。 |
| [reviewed/v6.5.8/decisions.json](./reviewed/v6.5.8/decisions.json) | 历史规则归属的审阅记录。 |
| [Beta 上游审核](../docs/BETA_UPSTREAM_AUTOMATION.md) | 候选来源的审阅流程，不会直接替换正式配置。 |

当前规则使用 Loon 原生的 `DOMAIN` / `DOMAIN-SUFFIX` 等匹配项，未保留以前按同一域名的 CN / 非 CN 解析目标切换策略的复合表达式；也不把共享 CDN 根域随意归给某个服务。来源处理边界见[规则审阅](../docs/RULE_SAFETY.md)。

## 出现误分流时

按 **请求记录中的命中规则 → 归属的策略组 → 策略组当前选中节点 → 实际连接结果** 顺序检查。能解析域名不代表正确分流，能选节点也不代表目标服务接受该出口。如果问题只发生在 DNS 解析阶段，转到[DNS 专题](../docs/DNS_PRIVACY.md)。

[返回首页](../README.md) · [规则审阅](../docs/RULE_SAFETY.md)
