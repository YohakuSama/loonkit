# LoonKit v7.0.3

本次更新聚焦按服务细分的 Loon 分流规则与策略组统一管理。

## 新增策略

GitHub、ChatGPT、Gemini、Claude、Speedtest、Cloudflare 六个独立服务策略组，总数增至 39 个；沿用现有 Proxy、Auto、Fallback 和其他策略组，不增加地区节点组。

## 分流规则

- 43 份 Loon 原生 `.lsr` 远程规则，固定到不可变 Git 提交。
- ChatGPT、Gemini、Claude 独立选路；其余 AI 包括 Copilot、GitHub Models、Grok、Perplexity、Cohere 等继续使用 `AI`。
- 国内 AI 服务明确直连，并处理 GitHub Copilot、Google/YouTube、Gemini/Google、Cloudflare/Speedtest 的匹配边界。
- 海外电商域名从 `ChinaDirect` 中移除，由统一代理承接。
- 保持原有广告拦截资源、DNS、TUN、插件与 `GEOIP,CN,DIRECT,no-resolve`。

## 图标与完整性

所有策略图标集中至 `icons/`，保留 40 张 512×512 PNG 及相应来源记录。正式配置与资源 SHA256、历史回滚配置均已纳入发布校验。

## 安装

使用 [正式配置](https://raw.githubusercontent.com/YohakuSama/loonkit/main/LoonKit.lcf)，或从本 GitHub Release 下载 `LoonKit.lcf`。

[更新记录](./CHANGELOG.md) · [第三方来源](./THIRD_PARTY_NOTICES.md) · [完整校验](./RELEASE_CHECKSUM_v7.0.3.md)
