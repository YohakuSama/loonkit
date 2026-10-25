# 节点选择与自动故障切换

LoonKit 保留 **Bing** 作为节点测速地址。公共配置不包含用户的机场节点，不按国家、倍率或名称擅自排除线路。

## 三个节点池

| 筛选器 | 初始范围 | 使用方式 |
| --- | --- | --- |
| `ALL_Filter` | 全部节点 | 手动选路，保留完整候选 |
| `Auto_Filter` | 全部节点 | `Auto` 定期测速，在候选中选择延迟最低的可用节点 |
| `Fallback_Filter` | 全部节点 | `Fallback` 从候选列表中选择**第一个可用节点**，不是第二快的节点 |

初始三个筛选器均为 `NameRegex, FilterKey = ".*"`。这是兼容所有个人订阅的安全默认值，**不代表已经为每个用户优化候选列表**。Loon 的节点测速结果也不能直接证明流媒体、AI 或游戏服务可用。

## 导入节点后建议设置

1. 在 Loon「配置 → 筛选节点」找到 `Auto_Filter`，通过 `NodeSelect` 手动选取常用、稳定、能访问 Bing 的线路；节点非常多时，不必全部纳入每轮自动测速。
2. 单独编辑 `Fallback_Filter`：按实际主线路、备用线路的优先级整理候选节点。**在 Loon 中核对最终显示顺序**，因为 Fallback 使用第一个可用节点。
3. 保留 `ALL_Filter` 的全量列表，以便其他服务组手动选择任何节点。
4. 检查 `Auto`、`Fallback` 均有有效候选；尤其在节点改名、订阅更新、暂停或删除后重新核对。候选为空可能使策略不可用。
5. 在 Loon 中对首选节点做连接测试，再模拟首选节点不可用，核实 Fallback 是否选择预期的备用节点。海外服务需要额外使用对应的节点解锁检测，不要用 Bing 测速结果代替。

`NodeSelect`、`NameKeyword` 和 `NameRegex` 均为 Loon 官方支持的筛选方式；不依赖特定机场的节点命名规则。策略的优先级来自实际候选顺序，无法通过公共模板预先推断。

## 当前测速参数（保持不变）

| 配置项 | 当前值 | 用途 |
| --- | --- | --- |
| 全局 `proxy-test-url` | `http://www.bing.com` | 节点列表测速 |
| `Auto url` | `http://www.bing.com` | 自动选低延迟节点 |
| `Auto interval` | 600 秒 | 自动测速周期 |
| `Auto tolerance` | 60 毫秒 | 减少小幅抖动引起的反复切换 |
| `Fallback url` | `http://www.bing.com` | 判断候选节点可达性 |
| `Fallback interval` | 900 秒 | 故障切换检测周期 |
| `Fallback max-timeout` | 2200 毫秒 | 超时节点视为不可用 |
| `test-timeout` | 5 秒 | 原生测速超时 |
| `internet-test-url` | `http://wifi.vivo.com.cn/generate_204` | 直连互联网检测，**不用于上述节点测速** |

Bing 可能受到本地网络重定向、运营商劫持或地区策略影响；若某条线路 Bing 延迟很低但目标应用仍无法访问，检查该应用的单独策略与节点，而不是自动改为直连。

参考：[Loon 节点筛选](https://nsloon.app/docs/Node/nodefilter/) · [Loon 策略组](https://nsloon.app/docs/Policy/policygroup/) · [DNS 设置](./DNS_PRIVACY.md)
