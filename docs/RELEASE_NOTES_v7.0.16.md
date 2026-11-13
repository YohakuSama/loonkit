# LoonKit v7.0.16

- Apple Intelligence / Siri：补全私有云计算域名，继续使用 Apple 策略组。
- 规则顺序：AppleOTA、Apple 远程订阅排在 Cloudflare 之前，并保持 AppleOTA 优先。其他 Cloudflare 业务仍归 Cloudflare。
- Stripe 支付：在现有 SharedInfrastructure 中补充 stripe.com 与 stripe.network，使用 Proxy。
- 规则质量：44 份远程订阅、既有全部策略组与本地规则保持不变；移除四条冗余 Apple 匹配，增加全量边界回归。
- Final：保留 GEOIP,CN,DIRECT,no-resolve 和 FINAL,Final。
- 更新方法：在 Loon 中更新 LoonKit 配置并刷新远程规则；修改过个人配置时请先备份。

所有正式远程规则均使用固定 40 位 Git 提交。CI 校验不代替设备实际请求日志。
