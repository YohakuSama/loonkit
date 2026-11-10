# LoonKit v7.0.11

- 新增独立的 `Crypto` 策略组，默认选用 `Proxy`，提供 `Auto`、`Fallback` 和手动节点筛选，不提供 `DIRECT` 选项。
- 为 Binance、OKX、Bybit、Coinbase、Kraken、Gate、Bitget、KuCoin、Crypto.com、MEXC、HTX 等平台和部分钱包/行情服务添加 29 条明确的本地域名后缀规则；本地优先匹配，避免落入旧 ChinaDirect 或 `GEOIP,CN,DIRECT`。
- 网络辅助插件声明 macOS 支持，三个 Generic Script 使用已有跨平台 Loon API；不改动诊断脚本、MitM、DNS、TUN 或 43 份固定规则订阅。
- 增加 Crypto 精确命中、模拟 CN 地址、相似域名不误匹配，以及插件平台声明的离线回归。

**实机测试：** 维护者已确认完成实机验证。加密货币域名仍以配置中明确登记的 29 条规则为准。
