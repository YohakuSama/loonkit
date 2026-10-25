# 正式版规则优化与所有权审计（v7.0.4）

此报告依据 `scripts/optimize_runtime_rules.py --audit` 对当前 Manifest 列出的 **43 份冻结资源**实际运行，
结果见 [审计 PR #156](https://github.com/YohakuSama/loonkit/pull/156) 的 Historical Integrity CI。
本报告是静态离线判断，不代表设备运行耗时或用户实际访问频率。

## 规则规模与性能敏感类型

| 类型 | 数量 |
| --- | ---: |
| DOMAIN | 23,606 |
| DOMAIN-SUFFIX | 168,455 |
| IP-CIDR | 2,928 |
| IP-CIDR6 | 1,567 |
| IP-ASN | 9 |
| DOMAIN-KEYWORD / USER-AGENT / URL-REGEX | 0 |
| **合计** | **196,565** |

两份大型资源 `ChinaDirect.lsr` 与 `AdBlockBalanced.lsr` 占规则字节数的约 97.2%，但
`DOMAIN-SUFFIX` / 精确域名不需要因为规则数多就盲目转换为 `DOMAIN-KEYWORD`；
Loon 对大量域名和 IP 规则采用专门的匹配策略。所有已记录的 CIDR 匹配带 `no-resolve`。

## 无行为变化的可删除冗余

同一订阅覆盖关系和跨订阅的「较早规则、同策略」覆盖关系共找到 **4 条**，
全部位于 `Our-Apple`，合计 **169 字节**。优化后 196,561 条，共 5,627,136 字节，
与原始 196,565 条、5,627,305 字节相比，节省约 0.003%。
这点收益不足以单独发布一个新正式版本、重定向 43 份 Raw 资源或增加设备回归成本。
因此 **保持现有冻结资源字节不变**，把安全压缩工具保留给未来规则有实质变化时一并使用。

## 跨策略完全相同的谓词（只记录，不自动更改策略）

| 谓词 | 当前先出现的策略 | 后出现的策略 | 处理 |
| --- | --- | --- | --- |
| `DOMAIN-SUFFIX,fast.com` | Speedtest | Netflix | 保持既有策略顺序；属于测速与视频服务共享域 |
| `DOMAIN-SUFFIX,trae.ai` | AI | TikTok | 保持 AI 先匹配；来源重叠需在更新时再次审查 |
| `DOMAIN-SUFFIX,minimax.io` | AI | DIRECT | 当前有效策略是 AI；不可仅因为国内企业就推断 DIRECT |
| `DOMAIN-SUFFIX,z.ai` | AI | DIRECT | 当前有效策略是 AI；不要自动调整为直连 |

此表只是**当前按配置优先级预测的结果**，不是对业务归属的永久认可。
与这些域相关的策略变更属于有行为变化的规则变更，必须明确审查。
其他不同类型谓词的交叉覆盖不应由本报告误判为「无冲突」。

## 后续每次更新规则的做法

1. 保留已有的源锁、许可证审计和 Git commit 固定 Raw 资源。
2. 对更新后的候选完整规则运行 `python3 scripts/optimize_runtime_rules.py --audit`，
   比较规则类型、DNS 风险、所有权冲突以及可无损消除的谓词。
3. 仅在收益足够且有完整基线对比时，用 `--write-dir` 在**独立候选目录**生成优化结果；
   原始冻结文件与正式配置绝不原地覆盖。
4. 更改优先级、增加更宽后缀、合并不同策略或删除未使用域名均视为行为变更，
   需单独验证，不纳入自动等价去重。

当前不新增 Lite 规则集，不触碰 Beta 个人测试配置，也不创建 v7.0.5。
