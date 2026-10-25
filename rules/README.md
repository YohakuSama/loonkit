# 分流规则

现役配置：**v7.0.9**。43 份远程规则固定于资源提交；目录按资源实际发布版本保留。完整资源引用、策略与 SHA256 见 [release_manifest.json](../build/release_manifest.json)。

## 规则顺序

- 明确的本地 AI 主机优先；TRAE API 的新加坡和美国端点统一归 AI 策略。
- 广告资源处理拦截与隐私端点。
- Apple、Microsoft、Paypal、Bilibili、AppleOTA 使用普通 DOMAIN / DOMAIN-SUFFIX 规则；按服务策略处理对应域名。
- 国内 AI 站点保持 `DIRECT`，海外 AI 由 ChatGPT、Gemini、Claude 或通用 AI 策略接管。
- GitHub Copilot 优先于 GitHub，YouTube 优先于 Google，Speedtest 优先于 Cloudflare。
- 其余请求按国内服务、AI、流媒体、社交和共享基础设施规则分流。
- GEOIP,CN,DIRECT,no-resolve 与 Final 处理剩余请求。

现役配置使用普通域名规则，并移除了与本地 GEOIP,CN,DIRECT,no-resolve 重复的 RegionalCN 远程订阅。

## 来源与生成

| 文件或目录 | 用途 |
| --- | --- |
| sources.json | 登记上游来源。 |
| inputs/ | 冻结的来源输入。 |
| releases/v7.0.3/ | 40 份现役 Loon 原生 `.lsr` 分类规则。 |
| releases/v7.0.5/ | 3 份移除重复归属后的现役规则。 |
| reviewed/v6.5.8/decisions.json | Beta 基础规则的审阅记录。 |
| releases/v6.5.7/、releases/v6.5.8/、releases/vNext-RC2/ | Beta 和确定性生成器仍依赖的冻结资源。 |
| beta/upstream/ | 测试渠道的累计精确域名增量。 |

历史版本的配置使用固定提交 URL；新版本通过新的资源提交更新引用。已退役候选和重复规则从工作树移除，原 Git tag/commit 保留完整历史。

[规则审阅](../docs/RULE_SAFETY.md) · [上游更新](../docs/BETA_UPSTREAM_AUTOMATION.md)
