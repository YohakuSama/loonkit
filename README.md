# LoonKit

**为 Loon 准备的规则分流配置。**

根据不同服务选择连接线路：国内常用服务优先直连，AI、开发平台、流媒体与社交应用可以分别指定策略。配置还包含节点选择、广告过滤与网络排查工具。

[**在 Loon 中导入配置 →**](https://www.nsloon.com/openloon/import?sub=https%3A%2F%2Fraw.githubusercontent.com%2FYohakuSama%2Floonkit%2Fmain%2FLoonKit.lcf) · [获取配置地址](https://raw.githubusercontent.com/YohakuSama/loonkit/main/LoonKit.lcf)

在已安装 Loon 的 iPhone / iPad 上使用 Safari 打开导入链接。**节点、订阅与代理账号需自行准备，本项目不提供。**

当前版本：**v7.0.9** · [更新记录](./docs/CHANGELOG.md) · [构建状态](https://github.com/YohakuSama/loonkit/actions/workflows/ci.yml) · [GPL-2.0-only](./LICENSE)

---

## 快速开始

1. **备份现有配置。** 如果已经在使用 Loon，请先导出配置文件并保存节点订阅。
2. **导入配置。** 点击上方的导入链接；若未唤起 Loon，在 App 内进入 **配置 → 所有配置文件 → ＋ → 从链接导入**，粘贴[配置地址](https://raw.githubusercontent.com/YohakuSama/loonkit/main/LoonKit.lcf)。
3. **添加节点并选路。** 应用 `LoonKit.lcf` 后，导入自己的节点或订阅，在 `Proxy` 及对应服务策略组中选择线路。
4. **按需开启托管。** 可设置更新频率。首次完整部署前确认覆盖范围；日常更新建议关闭「全覆盖更新」。

> [!IMPORTANT]
> `LoonKit.lcf` 的 `[Proxy]` 与 `[Remote Proxy]` 默认不包含个人节点。**「全覆盖更新」可能替换已有的节点、订阅及本地设置。** 只有完成备份并理解覆盖后果，才使用这一选项。

[图文操作路径](./docs/SETUP_GUIDE.md) · [托管与更新说明](./docs/LOON_APP_SETTINGS.md)

## 功能

- **规则分流** — 按服务类别组织策略，国内常用服务优先直连，其他服务可按需指定线路。
- **节点选择** — 在 `Proxy` 中手动选路，也可使用 `Auto` 自动测速、`Fallback` 选择可用线路。
- **广告管理** — `AdBlock` 策略支持 `REJECT`、`DIRECT` 或代理，按需要调整。
- **网络辅助** — 查看选定节点的出口信息、连接状态与 DNS 结果，辅助定位网络问题。

调整线路时，优先修改对应的服务策略组；遇到问题时，再结合节点信息与请求记录定位。

## 日常使用

**调整线路**：在 Loon 的策略页选择服务策略组，改选 `DIRECT`、`Proxy`、`Auto` 或 `Fallback`。`Fallback` 按可用性和候选顺序选择节点，不等同于延迟排名第二的节点。

**排查连接**：在 **策略 → 选定节点 → ···** 中运行所需的诊断工具。出口信息与连接结果只反映当前测试条件，不应被当作永久性能或可用性保证。[网络辅助说明](./docs/NETWORK_DIAGNOSTICS.md) · [插件源码](./release/v7.0.9/Network_Diagnostics.plugin)

**检查 DNS**：隐私优先时可在 Loon 的 **DNS → DNS 服务器** 中关闭「查询回落」，但加密 DNS 不可用时可能导致解析失败。该设置不能单独保证设备不存在 DNS 泄漏。[DNS 设置与核验](./docs/DNS_PRIVACY.md)

<details>
<summary>其他配置与兼容性说明</summary>

- 节点测速默认使用 `http://www.bing.com`；实际测速结果受网络状态和节点影响。
- 自动选路与故障切换的候选范围可分别调整，见[节点选择说明](./docs/NODE_SELECTION.md)。
- 网络辅助使用脚本功能，不需要仅为此安装 MitM 证书。
- TUN、UDP、QUIC 与 IPv6 设置应结合实际设备和节点协议检查，不建议照搬他人的开关组合。

</details>

## 常见问题

<details>
<summary>点击导入链接后没有打开 Loon</summary>

先确认已安装 Loon，并尝试在 iPhone / iPad 的 Safari 中打开。也可以在 Loon 的「从链接导入」界面手动填写[配置地址](https://raw.githubusercontent.com/YohakuSama/loonkit/main/LoonKit.lcf)。参见 [Loon 官方 URL Scheme](https://nsloon.app/docs/Scheme/)。

</details>

<details>
<summary>导入后没有可用节点</summary>

配置不内置节点或订阅。请添加自己的节点，并检查 `Proxy` 与其他策略组的线路选择。若使用了全覆盖更新，还应检查个人配置是否被替换。

</details>

<details>
<summary>节点可以连接，但某次诊断失败</summary>

初次握手、DNS/TLS 建连、临时网络波动等都可能影响结果。建议在同一节点复测，并核对 Loon 的请求记录与脚本日志。提交 [Issue](https://github.com/YohakuSama/loonkit/issues) 时，请移除节点密钥、订阅地址等敏感信息。

</details>

## 文档

- **安装与设置**：[导入指南](./docs/SETUP_GUIDE.md) · [托管与 App 设置](./docs/LOON_APP_SETTINGS.md) · [DNS 设置](./docs/DNS_PRIVACY.md)
- **选路与排查**：[节点选择](./docs/NODE_SELECTION.md) · [网络辅助](./docs/NETWORK_DIAGNOSTICS.md) · [规则分类](./rules/README.md)
- **版本与维护**：[更新记录](./docs/CHANGELOG.md) · [发布说明](./docs/RELEASE_NOTES_v7.0.9.md) · [校验信息](./docs/RELEASE_CHECKSUM_v7.0.9.md) · [维护指南](./docs/MAINTAINING.md)
- **项目说明**：[安全政策](./SECURITY.md) · [第三方许可](./docs/THIRD_PARTY_NOTICES.md) · [开源许可证](./LICENSE)
