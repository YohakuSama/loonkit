# LoonKit v7.0.13

- **Crypto 按需远程订阅**：删除正式配置内原有的 29 条 Crypto 本地规则，改为独立 `Crypto.lsr` 订阅，共 219 条 Loon 原生 `DOMAIN` / `DOMAIN-SUFFIX` 规则。无模糊关键词，引用固定 Git 提交。
- **覆盖补全**：保留原 29 个平台根域，参照 blackmatrix7 的 GPL-2.0 规则集精简、去重并补充 Hyperliquid、Phantom、Solana、Aave、PancakeSwap、Ledger、Trezor、Solscan 等平台和相关基础设施。
- **广告与国内分流**：顺序为 AdBlock → Crypto → 常规服务和国内直连。仅从原 AdBlock 远程资源移除误拦 `coincheck.com` 主页的一条规则；其他广告、遥测继续拦截。Crypto 独立订阅优先于国内直连规则，不经由本地内嵌规则兜底。
- **稳定性**：策略组及 BTC 图标保持现有排序；DNS、TUN、诊断插件和节点设置不改。固化来源、资源锁、校验和与回归测试。
