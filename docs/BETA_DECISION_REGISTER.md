# 分流设计

| 范围 | 处理方式 |
| --- | --- |
| 国内常用服务 | 现有国内服务规则与 GEOIP 兜底。 |
| Apple / Microsoft / Paypal / Bilibili | 先检查解析 IP 的 CN 条件；CN 直连，其他结果进入服务策略。 |
| AI | 明确的 AI 主机优先于通用平台规则。 |
| 共享云和 CDN | 不将公共租户根域整体归给单个业务。 |
| 广告与隐私 | 使用独立拦截资源，保留登录、验证码、证书和通知接口。 |
| 未知服务 | Final。 |
| 上游更新 | 受限精确域名增量进入 beta 草稿；地区分流及高风险变更人工审阅。 |

现役规则不使用 USER-AGENT 或 DOMAIN-KEYWORD 猜测业务归属。GEOIP,CN,DIRECT,no-resolve 保持原样。

[规则审阅](./RULE_SAFETY.md) · [DNS](./DNS_PRIVACY.md)
