# 节点选择与自动故障切换

通过 `Proxy`、`Auto` 和 `Fallback` 选择线路，使用筛选器调整候选节点。自动测速只衡量目标地址的可达性与延迟，不保证指定地区或服务解锁。

## 策略组逻辑

| 策略组 | 选择方式 | 适合的场景 |
| --- | --- | --- |
| `Proxy` | 手动选择单节点、`Auto` 或 `Fallback` | 按服务或使用习惯固定线路 |
| `Auto` | `url-test`，定期在候选节点中选延迟最低者 | 日常自动选路 |
| `Fallback` | `fallback`，按候选列表顺序取首个可用节点 | 主线路与备用线路有明确优先级 |

## 多订阅节点池

三个筛选器默认包含全部节点：

- `ALL_Filter`：完整节点列表，用于手动选择。
- `Auto_Filter`：`Auto` 自动测速候选列表。
- `Fallback_Filter`：`Fallback` 有序主备候选列表。

在 Loon「配置 → 筛选节点」中，通过 `NodeSelect`、`NameKeyword` 或 `NameRegex` 调整列表。`Auto_Filter` 可保留常用线路，`Fallback_Filter` 按主备优先级排列。

## 测速参数

| 参数 | 配置 | 作用 |
| --- | --- | --- |
| `proxy-test-url` | `http://www.bing.com` | Loon 原生节点列表测速 |
| 自动策略 `url` | 同上 | 统一 Auto 与 Fallback 的探测目标 |
| `Auto interval` | 600 秒 | 适用于少量和较多节点的定期优选 |
| `Auto tolerance` | 60 毫秒 | 减少微小抖动导致的频繁切换 |
| `Fallback interval` | 900 秒 | 定期检查备用节点可用性 |
| `Fallback max-timeout` | 2200 毫秒 | 对抖动保留余量，同时减少高延迟节点被判为可用 |
| `test-timeout` | 5 秒 | 原生测速超时上限 |

节点较多时，收窄自动策略的候选列表可减少每轮探测数量。`Auto_Filter` 建议仅包含常用且能访问目标服务的节点；`Fallback_Filter` 建议按主备优先级排序。地区受限服务不应仅依靠测速判断可用性。

参考：[Loon 节点筛选](https://nsloon.app/docs/Node/nodefilter/) · [Loon 策略组](https://nsloon.app/docs/Policy/policygroup/) · [维护指南](./MAINTAINING.md)
