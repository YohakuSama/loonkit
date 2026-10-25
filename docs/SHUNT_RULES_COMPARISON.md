# 分流规则统一与 ShuntRules 对照

## 基准

LoonKit 正式版 v7.0.0 启用 36 份远程规则，合计 196486 条匹配器，来自五组历史发布路径。ShuntRules 的公开 README 列出 668 个按服务命名的 Loon 链接，并说明其合并策略：将同一服务的普通、域名及需要解析的拆分规则整合为单份 .lsr。**这不是跨策略全局去重的证明。**

参考：
- https://github.com/luestr/ShuntRules
- https://github.com/blackmatrix7/ios_rule_script
- https://nsloon.app/docs/Rule/
- https://nsloon.app/docs/Rule/domain_rule/
- https://nsloon.app/docs/Rule/ip_rule/
- https://nsloon.app/docs/Rule/sub_rule/

ShuntRules 仓库仅提供目录和链接，实际 .lsr 由 rule.kelee.one 托管；没有获得规则字节及生成器前，不得宣称两库已经完成逐条差异比较或全局去重验证。LoonKit 在 Blackmatrix7 基础上还混入 V2Fly 与自定义归属，因此不应直接整体替换 ShuntRules 输出。

## 本分支的统一快照

所有 36 个正式版订阅的原始 Git blob 复制到 `rules/releases/v7.0.1/`，不重写、拆分或移动现有正式文件。候选配置为 `build/candidates/v7.0.1/LoonKit.lcf`，全部 36 条订阅固定引用同一资源提交。原来的 tag、策略、订阅顺序、规则字节、GEOIP/CN 与 FINAL 均保持一致；广告和 DNS/TUN 等配置未被调整。

运行 `python3 scripts/routing_candidate_audit.py --check` 检查固定资源、内容哈希、Loon 原生规则类型、订阅顺序，以及跨策略域名覆盖统计。域名覆盖不能简单按文本去重：不同策略的专用域名可能位于共享上级域名之内。

## 已确认的跨策略覆盖

| 分流组 | 具体覆盖示例 | 归属准则 |
| --- | --- | --- |
| AI / Google | `aistudio.google.com` 属于 `google.com` 后缀 | AI 专用域名先于通用 Google |
| AI / Microsoft | `copilot.microsoft.com` 属于 `microsoft.com` 后缀 | Copilot 由 AI 处理 |
| YouTube / Google | `youtube.googleapis.com` 属于 `googleapis.com` 后缀 | YouTube 业务独立 |
| WhatsApp / Facebook | `graph.facebook.com` 位于 Facebook 后缀下 | 审核实际用途和用户策略选择 |
| SteamCN / Steam | `steamchina.com` 与国际 Steam/CDN 规则相交 | 国内下载服务优先 DIRECT |
| AppleOTA / Apple | `gdmf.g.aaplimg.com` 落入 Apple 的 `aaplimg.com` 后缀 | 相同 Apple 策略下可考虑去重 |

## 与 ShuntRules 分类的差异

当前 LoonKit 的核心 AI 统一落在 AI 策略；ShuntRules 有 OpenAI、Claude、Anthropic、Gemini 等独立分类。Apple 还有 AppleID、AppleMusic、AppleNews 等业务细分；微软生态可拆 OneDrive、MicrosoftEdge；视频有 YouTubeMusic、BiliBiliIntl；其他候选包括 GitHub、SteamCN、ChinaMedia、ChinaMaxNoMedia。

建议先补充 GitHub、OneDrive 与必要的 AI 子服务归属审计。是否新设策略组，应以用户实际需要、DNS 命中和现有选择器为依据。Apple 子业务、YouTubeMusic、国内媒体差异可按需细分，但**不得盲目同时订阅父集与全部子集**。ChinaDirect 已包含大型 ChinaMaxNoMedia 来源，GEOIP,CN,DIRECT,no-resolve 也是现有兜底，不能直接追加 ChinaMax/China/ChinaMedia 并认为增强。

## 分阶段处理原则

1. 统一发布资产目录、单一提交固定引用与构建清单。
2. 以严格策略优先级和业务所有权审查跨策略匹配，分清相同策略冗余与不同策略必要例外。
3. 仅对明确同策略且不会改变有效命中的规则去重；跨策略重叠需业务事实支持。
4. 对上游候选先确认来源、许可、Loon 语法和现有覆盖，再列入新业务组。
5. 生成前后进行逐条路由效果差异审计，保持历史回滚快照；正式版入口独立于候选。

不编造复合 GEOIP 写法、不按想象增加地区判定。任何后续规则变化仅采用 Loon 官方支持的语法，且不得把域名和 IP 匹配优先级简单视为等价。
