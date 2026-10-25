# 分流规则

现役版本：**v6.5.8**。完整资源引用、策略与 SHA256 见 [release_manifest.json](../build/release_manifest.json)。

## 规则顺序

- 明确的本地 AI 主机优先。
- 广告资源处理拦截与隐私端点。
- 地区条件区分 Apple、Microsoft、Paypal、Bilibili 的国内与海外地址。
- 其余请求按国内服务、AI、流媒体、社交和共享基础设施规则分流。
- GEOIP,CN,DIRECT,no-resolve 与 Final 处理剩余请求。

地区规则先匹配服务域名，再检查 GeoIP。CN 条件和非 CN 条件成对生成，服务策略组提供代理线路。

## 来源与生成

| 文件或目录 | 用途 |
| --- | --- |
| sources.json | 登记上游来源。 |
| inputs/ | 冻结的来源输入。 |
| reviewed/v6.5.8/decisions.json | 当前版本的变更配方。 |
| releases/v6.5.8/ | 当前版本生成的规则。 |
| beta/upstream/ | 测试渠道的累计精确域名增量。 |

历史版本的配置使用固定提交 URL；新版本通过新的资源提交更新引用。

[规则审阅](../docs/RULE_SAFETY.md) · [上游更新](../docs/BETA_UPSTREAM_AUTOMATION.md)
