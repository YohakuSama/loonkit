# LoonKit v7.0.0

- 正式版入口与规则订阅标签统一为 v7.0.0；清理正式配置中的 Beta 标签。
- 继续使用 Loon 原生 `DOMAIN` / `DOMAIN-SUFFIX` 服务规则，不使用曾引发异常的复合 GEOIP 分流。
- 保持节点测速、DNS、TUN、路由优先级、36 个远程规则源、196486 条匹配器及网络插件运行时行为不变。
- 完整保留 v6.5.10 固定配置、发布元数据和 SHA-256 历史记录以供回滚。
- 为正式版补齐自动化校验、Tag 与 GitHub Release 发布流程。

配置：`LoonKit.lcf`；规则与资源详细信息：`build/release_manifest.json`。
