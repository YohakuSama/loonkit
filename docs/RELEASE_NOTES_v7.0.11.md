# LoonKit v7.0.11

- 新增独立的 `Crypto` 策略组，默认选用 `Proxy`，提供 `Auto`、`Fallback` 和手动节点筛选，不提供 `DIRECT` 选项。
- 为 Binance、OKX、Bybit、Coinbase、Kraken、Gate、Bitget、KuCoin、Crypto.com、MEXC、HTX 等平台和部分钱包/行情服务添加 29 条明确的本地域名后缀规则；本地优先匹配，避免落入旧 ChinaDirect 或 `GEOIP,CN,DIRECT`。
- 网络辅助插件声明 macOS 支持，三个 Generic Script 使用已有跨平台 Loon API；不改动诊断脚本、MitM、DNS、TUN 或 43 份固定规则订阅。
- 增加 Crypto 精确命中、模拟 CN 地址、相似域名不误匹配，以及插件平台声明的离线回归。

**验收边界：** GitHub CI、资源完整性与静态规则模拟不等于 macOS 实机兼容验收。请在 Loon for Mac 上核对三个诊断入口和实际节点，同时检查加密货币站点的请求记录与实际出口。未登记的第三方 API/CDN 域名及直接连接 IP 不受这 29 条域名规则保障。
