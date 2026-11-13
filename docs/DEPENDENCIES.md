# 现役依赖

当前正式版 **v7.0.14**，包含 **46 份**固定远程规则、40 个策略组及三个诊断工具。
配置与资源顺序由 [结构化模型](../build/profile.json) 定义，[资源清单](../build/release_manifest.json) 自动生成。
配置、插件、脚本和图标共 **91 个**固定资源的完整依赖图及 SHA256 见 [运行资源锁](../build/runtime.lock.json)。

| 资源 | 固定提交 |
| --- | --- |
| 42 份既有远程规则（`releases/v7.0.3/` 与 `releases/v7.0.5/`） | `673e2b470b45f291ebf15bbf9dca232d10709bad` |
| Crypto 独立远程订阅（219 条）与 AdBlock 单项修订（`releases/v7.0.13/`） | `90659c20351c37fe505d7db18896baf0aeb8f59d` |
| 夸克直连、维基百科及多邻国规则（v7.0.14） | \`beefdc33dd7f94079941eff06005a53ade9c5b1b\` |
| 常用策略图标（`icons/`） | `d82214d057b27a68d6b9c07c61fb126a69adc903` |
| Crypto 专属 BTC 图标（`icons/Crypto.png`） | `a9d4e9dc22f573d3f2a4ccd3776441d007f1e686` |
| `release/Network_Diagnostics.plugin` | `274dd172f147727445b15b9cc70a4c01881ad202` |
| 三项诊断脚本（`release/diagnostics/`） | `45dd8bff200a69740178b7a2e0e087a47c8537d8` |

诊断可编辑源码位于 `src/diagnostics/`，构建时内联公共代码，客户端加载独立脚本。
历史输入、Beta 基线和许可证证明独立保留；当前配置构建不再依赖旧正式配置快照。

[当前 SHA256](./RELEASE_CHECKSUM_v7.0.14.md) · [维护流程](./MAINTAINING.md)
