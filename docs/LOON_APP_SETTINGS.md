# Loon App 设置

| 设置 | 建议 |
| --- | --- |
| 工作模式 | 规则分流 |
| DNS 明文回退 | 在「DNS 服务器」页面关闭「加密 DNS 失败回退到普通 DNS」 |
| 远程规则与插件 | 启用，导入主配置后刷新 |
| 脚本 | 使用网络辅助时开启 |
| Wi-Fi 共享 | 按需开启，配置默认 `allow-wifi-access = false` |
| MitM | 仅在其他确有需要的插件中启用；网络辅助不依赖 MitM |

本配置不内置代理节点。导入个人订阅后，在 `Proxy` 和各服务组中选择线路，并分别调整 `Auto_Filter` 与 `Fallback_Filter` 的候选节点。测速使用 **Bing**，不要将独立的直连互联网 204 检测地址误当成节点测速目标。

**当前服务组默认：** Apple、Microsoft、Bilibili、Line、Speedtest 首选 `DIRECT`，可手动改选代理。Paypal 默认使用 `Proxy`，不是默认直连。最终是否走直连仍取决于本地/远程规则优先级和 GeoIP。

## 兼容性排查

`ip-mode = dual`、`ipv6-vif = auto` 保留 IPv6 能力。当前 `disable-stun = true` 和 `udp-fallback-mode = REJECT` 意味着 STUN 受限、节点不支持 UDP 时不会无条件回退直连。遇到 WebRTC、语音通话或特定游戏问题时，先在 Loon 请求记录中明确失败类型、目标策略和节点 UDP 支持，再决定是否单独调整；**不要为了一个应用的异常全局取消保护**。

[节点池配置](./NODE_SELECTION.md) · [DNS 验证](./DNS_PRIVACY.md) · [网络辅助](./NETWORK_DIAGNOSTICS.md)
