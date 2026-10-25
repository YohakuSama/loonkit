# LoonKit 稳定性排障配置（v6.5.8 Safe Routing）

如安装正式配置后 Loon VPN 出现自动断开、自动重连，可暂时导入 [LoonKit.Safe.lcf](../LoonKit.Safe.lcf) 进行 A/B 排查。本配置为**待实机验证的应急方案**，不能保证排除所有 iOS Network Extension 或节点异常。

- 正式发布文件 `LoonKit.lcf`、冻结规则、release manifest 与发布 SHA256 **均保持不变**，以免破坏已发布 v6.5.8 的可追溯性和 CI 校验。
- 独立配置保留 37 个远程规则资源、现有节点策略、DNS、TUN、插件、GEOIP CN no-resolve 及 Final；仅替换以下六项引用为普通匹配器，不加载原有 `AND/NOT + GEOIP` 资源：`Our-RegionalCN`、`Our-AppleOTA`、`Our-Bilibili`、`Our-Microsoft`、`Our-Apple`、`Our-Paypal`。
- 上述六份改为 2,880 条普通规则（包含 205 条静态国内例外）。其中 RegionalCN 由明确的 `.cn` 服务域名和精选哔哩哔哩大陆域名组成；AppleOTA 改为直连；海外服务域名按对应 `Apple/Microsoft/Paypal/Bilibili` 策略组处理。其余规则与策略保持原顺序。
- **地区路由有意降级**：原版利用运行时解析结果判断相同域名的境内/境外 IP；稳定性配置按明确域名静态分类，无法对相同域名在不同地区的 CDN 做完全等价分流。尤其在中国大陆以外网络，所列大陆 Bilibili 域名仍将直连，Apple OTA 域名全部直连。根据实际需要调整对应策略或临时切回原配置。

## 排查步骤

1. 记录 Loon App 版本、iOS 版本、使用的网络（Wi-Fi/蜂窝）及断线间隔，并确认节点配置有效。
2. 备份当前配置，将 `LoonKit.Safe.lcf` 导入 Loon，保留相同的节点/订阅。刷新远程规则。
3. 在相同网络与节点下分别使用原版和 Safe Routing，观察是否出现 VPN 开关自动关闭后重连；同时检查 Loon 请求记录和系统分析日志（如果存在 `JetsamEvent`、崩溃或 Network Extension 终止记录，可提供脱敏内容）。
4. 如 Safe Routing 仍重连，进一步测试停用网络诊断插件、分组自动测速、非目标远程规则，并排查节点/DNS/系统 VPN 冲突；不应据此断言复合规则是唯一根因。

## 维护约束

- 安全配置中六个 `rules/hotfix/v6.5.8-safe/*.list` 使用同一个**固定 commit SHA**，避免远端规则在不经审查时漂移。
- `tests/test_safe_routing.py` 校验：六组均为普通匹配器、五组保留全部原始服务匹配范围、地区直连只保留可静态确认的例外、远程资源顺序及非目标配置不变。
- 在完成实机 A/B 测试与发布门禁升级之前，**不要用 Safe Routing 覆盖**已锁定的 `LoonKit.lcf`。
