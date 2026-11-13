# 现役远程规则边界审计

## 检查范围与方法

以 `LoonKit.lcf` 和 `build/release_manifest.json` 的 44 份固定提交远程订阅为准，按声明的顺序读取真实规则文件，检查精确域名、域名后缀、重复匹配和前置覆盖。当前正式版本是 v7.0.15。候选版本另行推演，不改动现役配置或冻结快照。

```bash
python3 scripts/policy_boundary_audit.py --json
python3 scripts/test_suites.py current
```

全量检查中有 192,292 条 DOMAIN / DOMAIN-SUFFIX 匹配规则，85 条后置匹配被**更早的其他策略**完全遮蔽。这些不等于 85 个正在错误选路的请求。另有 3,142 处「前面的较窄规则与后面的宽后缀交叠」，前面的窄规则仍先命中。两类情况必须分开处理，不能直接把数字相加，也不能按「重复」批量删除。其余 IP、GeoIP、直接使用 IP、DNS 缓存与 Loon 真机结果不属于该静态域名推演的结论。

具体的 10 组完全遮蔽关系、数量及复审备注由 [policy_boundary_v7.0.15.json](../rules/reviewed/policy_boundary_v7.0.15.json) 固定。CI 会在出现未经审核的新完全遮蔽关系时失败。

## 已审查的服务边界

- **广告先于服务**：AdBlock 更早的广告、统计和遥测域名优先。例如 Apple 的 Omtrdc、Disney 的遥测端点会先命中 AdBlock。这是既定优先级，不为清理重复而改成 Apple / Disney。
- **专用服务先于泛平台**：ChatGPT、Gemini、Claude、AI 等服务订阅优先于 Google / Microsoft 等通用平台。即使 `gemini.google.com` 属于 `google.com`，也应保持 Gemini 的服务归属。
- **共享 CDN 交叠**：YouTube 的 `gvt1.com`、`gvt2.com` 广域规则会遮蔽 Google 列表中八条更窄的 GVT 域名。保留当前经过上游整合的优先级；没有实际用途与连接证据前，不把整个 GVT 网络重分配给另一策略。新增规则应优先选准确的服务专属主机。
- **Crypto 和国内规则**：`ChinaDirect` 是远程订阅末尾。两条 MDex 与 Crypto 精确重叠，实际优先命中 Crypto。Google 对 ChinaDirect 的 45 条遮蔽也不会把 Google 请求改为 DIRECT。后续更新 ChinaDirect 冻结资源时，再去除无效的后置重复，不修改已发布的冻结资源。
- **本地特例保持稳定**：`raw.githubusercontent.com` 仍由 `[Rule]` 中既有 Proxy 特例接管。此次不添加本地域名，也不扩大本地规则。
- **兜底保持稳定**：命中明确规则时使用该规则对应的策略；否则走 `GEOIP,CN,DIRECT,no-resolve`，其余由 `FINAL,Final` 选择。Final 可以由用户选为 Proxy 或 DIRECT，不等同于所有未收录域名都强制代理。

## 本次候选修复

### Apple Intelligence / Siri

`rules/releases/v7.0.16/Apple.lsr` 增加 Apple 官方列出的三项 Private Cloud Compute 专用端点：

```text
DOMAIN,apple-relay.cloudflare.com
DOMAIN,apple-relay.fastly-edge.com
DOMAIN,cp4.cloudflare.com
```

`guzzoni.apple.com`、`*.smoot.apple.com` 和 `apple-relay.apple.com` 已由 `DOMAIN-SUFFIX,apple.com` 覆盖，无须重复添加。还移除了 4 条已被 `DOMAIN-SUFFIX,apple.com.edgekey.net` 覆盖的同策略冗余匹配，保留其完整匹配范围。

**注意发布顺序**：当前 Cloudflare 的 `DOMAIN-SUFFIX,cloudflare.com` 位于 Apple 之前。只增加上述 Apple 域名还不能让 Cloudflare 下的 Apple PCC 请求归属 Apple。下一次正式发布必须将既有 `Our-AppleOTA` 与 `Our-Apple` 两份远程订阅移到 `Our-Cloudflare` 之前，保持 `Our-AppleOTA` 优先于 `Our-Apple`；仍均 `policy=Apple`。其他 Cloudflare 服务（例如 `api.cloudflare.com`）继续 `policy=Cloudflare`。

### Stripe 付款和风控端点

正式规则的 `stripe.com`、`api.stripe.com`、`m.stripe.network` 当前未明确分流，会落到 Final。候选 `rules/releases/v7.0.16/SharedInfrastructure.lsr` 只增加 Stripe 官方自有域名：

```text
DOMAIN-SUFFIX,stripe.com
DOMAIN-SUFFIX,stripe.network
```

将这些规则保留在既有 `Our-SharedInfrastructure` 远程订阅中，继续 `policy=Proxy`。不新增 Stripe 策略组，不扩展到其他商户、共享支付网关或整个 CDN 域名。

## 发布与回归

1. 先合并候选规则资产。历史 `v7.0.3`、`v7.0.15` 文件不作修改。
2. 进行新的正式发布时，把现有 Apple 和 SharedInfrastructure 两条远程引用固定到新资产的**发布提交 SHA**。同步调整 AppleOTA / Apple 在 Cloudflare 前面的订阅顺序；不向本地 `[Rule]` 插入域名。保持远程订阅数量与策略组数量不变。
3. 使用 `scripts/release_engine.py` 的正式流程生成 `LoonKit.lcf`、manifest、资源锁、摘要，运行所有 CI 验证。绝不把已发布的 SHA 改成随 main 浮动的 URL。
4. 回归检查 Apple PCC、Siri、普通 Cloudflare、Stripe 付款、Google、YouTube、Gemini、ChatGPT、国内直连及 Final。上线后以 Loon 请求日志核对策略命中与连接结果，记录实际 DNS / IP / GeoIP 情况。

外部对照：[Apple 企业网络](https://support.apple.com/zh-cn/101555)、[Blackmatrix7 Siri](https://github.com/blackmatrix7/ios_rule_script/tree/master/rule/Loon/Siri)、[Blackmatrix7 Apple](https://github.com/blackmatrix7/ios_rule_script/tree/master/rule/Loon/Apple)、[Stripe 官方域名](https://support.stripe.com/questions/verify-you-are-on-an-official-stripe-webpage)、[Stripe.js 安全与隐私](https://support.stripe.com/questions/privacy-and-security-of-stripe-js)。
