# LoonKit · App 设置与更新指南

> 对应正式版 **v7.0.8**。本文是 LoonKit 的推荐操作，不代表 Loon 对所有配置的通用要求。UI 文案随 Loon 版本可能微调；先备份原配置与节点信息。

## 1. 第一次导入：选「全覆盖更新」

1. 用 [一键导入](https://www.nsloon.com/openloon/import?sub=https%3A%2F%2Fraw.githubusercontent.com%2FYohakuSama%2Floonkit%2Fmain%2FLoonKit.lcf) 唤起 Loon，或进入「配置 → 配置文件」通过 URL 导入 `https://raw.githubusercontent.com/YohakuSama/loonkit/main/LoonKit.lcf`。
2. **首次部署 LoonKit 时，在导入 / 更新设置里开启「全覆盖更新」**，按完整基线安装策略组、规则与插件。
3. 确认当前启用 `LoonKit.lcf`，再添加个人节点或节点订阅；依次刷新远程规则、插件等外部资源。

**为什么先备份？** 当前配置的 `[Proxy]`、`[Remote Proxy]` 为空；全覆盖导入可能替换原配置、已有节点订阅和部分本地选项。对于已经高度自定义的 Loon，建议先导出备份并理解覆盖后果，而不是在现有个人配置上直接尝试。

## 2. 日常更新：关闭「全覆盖更新」

导入完成并添加个人订阅后：

1. 打开 Loon「**配置 → 配置文件**」。
2. **长按 `LoonKit.lcf` → 更新策略**。
3. 按个人需求设置**更新频率**，**关闭「全覆盖更新」**并保存。
4. 今后在 `LoonKit.lcf` 条目更新配置；主配置有变更时，检查并刷新远程规则与插件。

日常关闭全覆盖可减少覆盖本地调整的风险，但不保证保留每一项编辑。**若版本更新修改了策略结构或其他基础字段，先备份并阅读发行说明，必要时再全覆盖导入。** 定时资源更新的执行时间受 App 运行状态影响，不保证 iOS 后台准点执行。

## 3. DNS 查询回落：明确位置与取舍

**设置 → DNS → DNS 服务器 → 查询回落 → 关闭**（隐私优先建议）。

这项 App 开关不是 `LoonKit.lcf` 内可替代设置的字段。LoonKit 使用：

```ini
dns-server = 223.5.5.5,223.6.6.6
doh-server = https://dns.alidns.com/dns-query
hijack-dns = *:53
```

根据 [Loon 官方 DNS 文档](https://nsloon.app/docs/DNS/)，加密 DNS 失败时通常会回落普通 DNS。关闭后可阻止这一路径将请求退回普通 DNS，**但也意味着 DoH 不可用时可能无法解析**。是否开启应在隐私与可用性间自行选择；同时应注意，`hijack-dns = *:53` 针对指定的 UDP DNS 目标，不意味着所有 App 的 DoH/DoT 都被拦截。

逐项验证的方法见 [DNS 与隐私](./DNS_PRIVACY.md)。

## 4. 其他建议

| 设置 | 推荐值与理由 |
| :--- | :--- |
| 流量模式 | **规则分流**，确保服务策略组参与匹配。 |
| `Proxy` | 导入节点后选择主要可用线路；项目不提供节点。 |
| `Auto_Filter` | 手动控制自动测速候选，不必让所有节点参与每轮测速。 |
| `Fallback_Filter` | 按主备优先顺序排列，Fallback 取第一个可用候选，并非第二快。 |
| 节点测速 | 配置使用 `http://www.bing.com`；独立直连检测为 `http://wifi.vivo.com.cn/generate_204`。 |
| 域名拦截 | 当前是 `domain-reject-mode = DNS`、`dns-reject-mode = LOOPBACKIP`，无需重复写配置。 |
| TUN Only | 如果需要更完整的 DNS 阶段拦截，可依据网络环境评估；不是必须对所有设备强制切换的万能方案。 |
| MitM | **网络诊断插件不依赖 MitM**。其他插件若明确需要，再按要求配置证书、主机名与权限。 |
| Wi-Fi 共享 | 当前 `allow-wifi-access = false`，保持关闭，除非确实需要局域网设备接入。 |

**服务组默认：** `Apple`、`Microsoft`、`Bilibili`、`Line`、`Speedtest` 优先 `DIRECT`；`Paypal` 优先 `Proxy`。策略组选项与最终命中规则应分别核对。

**兼容性：** `ip-mode = dual`、`ipv6-vif = auto` 保留双栈能力；`disable-stun = true`、`udp-fallback-mode = REJECT` 保护特定场景，但可能影响 WebRTC、语音和 UDP 游戏。先核对请求记录与节点 UDP 能力，不建议为排查某一个应用而全局取消保护。

## 5. 参考

- [Loon 官方 Scheme / 配置导入](https://nsloon.app/docs/Scheme/)
- [Loon 官方 DNS 行为](https://nsloon.app/docs/DNS/)
- [Loon 官方通用配置参数](https://nsloon.app/docs/General/)
- [Loon 配置导入参考](https://wiki.repcz.link/loon/profile/)
- [Loon 资源自动更新参考](https://wiki.repcz.link/loon/more-set/)

[返回项目首页](../README.md) · [节点筛选](./NODE_SELECTION.md) · [DNS 验证](./DNS_PRIVACY.md) · [诊断插件](./NETWORK_DIAGNOSTICS.md)
