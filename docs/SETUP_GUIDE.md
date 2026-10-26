# 初次导入：从空配置到可以使用

本页只处理**首次安装与验收**。托管更新的具体选项见[配置托管](./LOON_APP_SETTINGS.md)，DNS 参数见[DNS 专题](./DNS_PRIVACY.md)，不在这里重复展开。操作路径依据 2026-10-26 核对的 Loon 界面；不同 App 版本可能调整名称。

## 1. 先保存现有设置

已有 Loon 配置的用户，先导出当前配置，并单独保存节点订阅、证书或其他不能轻易恢复的本地设置。首次使用也应确认自己拥有可用节点：**LoonKit 不提供节点和订阅**。

## 2. 导入并应用配置

1. 在 iPhone / iPad 的 Safari 打开 [LoonKit 一键导入](https://www.nsloon.com/openloon/import?sub=https%3A%2F%2Fraw.githubusercontent.com%2FYohakuSama%2Floonkit%2Fmain%2FLoonKit.lcf)。未唤起 App 时，进入 **配置 → 所有配置文件 → 右上角 ＋ → 从链接导入**。
2. 手动导入请填入 [正式配置地址](https://raw.githubusercontent.com/YohakuSama/loonkit/main/LoonKit.lcf)，核对文件名后**应用**该配置。
3. 是否开启「托管」由使用需求决定；**不要为了导入成功就开启「全覆盖更新」**。它可能替换已有节点、订阅及本地设置。各开关的作用和后续维护方法请看[配置托管](./LOON_APP_SETTINGS.md)。

## 3. 添加节点并完成选路

1. 添加自己的节点或远程订阅，确认 Loon 的节点列表不为空。
2. 打开策略页，在 `Proxy` 组手动选一个可连接的节点，再按需求选择 AI、开发平台、视频等服务组的策略。
3. 需要自动选择或备用线路，再按[节点筛选与测速](./NODE_SELECTION.md)分别管理 `Auto_Filter` 和 `Fallback_Filter`；首次部署无须同时调整全部分组。

## 4. 首次验收

| 检查 | 预期与排查入口 |
| --- | --- |
| 常用国内网站 | 确认基本访问正常；异常时先检查当前模式与命中的策略。 |
| 需要代理的服务 | 检查该服务组是否已选择有效节点，不用节点测速结果替代实际访问。 |
| DNS 解析 | 默认 AliDNS 可以先保留；需关注「查询回落」或改用海外 DoH 时，按[DNS 设置与故障定位](./DNS_PRIVACY.md)操作。 |
| 网络辅助 | 在单个节点菜单手动运行需要的检测；结果解释见[诊断结果说明](./NETWORK_DIAGNOSTICS.md)。 |

如出现“导入成功但没有网络”，依次检查：**配置是否已应用 → 节点/订阅是否存在 → 服务策略命中 → DNS 请求记录**。不要通过反复全覆盖导入来排查网络故障。

[返回 README](../README.md) · [托管和覆盖更新](./LOON_APP_SETTINGS.md) · [Loon 官方说明](https://nsloon.app/docs/)
