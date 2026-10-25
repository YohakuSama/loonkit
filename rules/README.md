# 分流规则

现役版本：**v7.0.0**。完整资源引用、策略与 SHA256 见 [release_manifest.json](../build/release_manifest.json)。

## 规则顺序

- 明确的本地 AI 主机优先。
- 广告资源处理拦截与隐私端点。
- Apple、Microsoft、Paypal、Bilibili、AppleOTA 使用普通 DOMAIN / DOMAIN-SUFFIX 规则；按服务策略处理对应域名。
- 其余请求按国内服务、AI、流媒体、社交和共享基础设施规则分流。
- GEOIP,CN,DIRECT,no-resolve 与 Final 处理剩余请求。

现役配置使用普通域名规则，并移除了与本地 GEOIP,CN,DIRECT,no-resolve 重复的 RegionalCN 远程订阅。

## 来源与生成

| 文件或目录 | 用途 |
| --- | --- |
| sources.json | 登记上游来源。 |
| inputs/ | 冻结的来源输入。 |
| reviewed/v6.5.8/decisions.json | 当前版本的变更配方。 |
| releases/v6.5.9/ | 固定版本的五份普通域名规则。 |
| releases/v6.5.8/ | 历史冻结规则，供审计与回滚。 |
| beta/upstream/ | 测试渠道的累计精确域名增量。 |

历史版本的配置使用固定提交 URL；新版本通过新的资源提交更新引用。

[规则审阅](../docs/RULE_SAFETY.md) · [上游更新](../docs/BETA_UPSTREAM_AUTOMATION.md)
