# 现役依赖

当前正式版 **v7.0.10**，包含 **43 份**固定远程规则、39 个策略组及三个诊断工具。
配置与资源顺序由 [结构化模型](../build/profile.json) 定义，[资源清单](../build/release_manifest.json) 自动生成。
配置、插件、脚本和图标共 **87 个**固定资源的完整依赖图及 SHA256 见 [运行资源锁](../build/runtime.lock.json)。

| 资源 | 固定提交 |
| --- | --- |
| 43 份远程规则（`releases/v7.0.3/` 与 `releases/v7.0.5/`） | `673e2b470b45f291ebf15bbf9dca232d10709bad` |
| 配套图标（`icons/`） | `d82214d057b27a68d6b9c07c61fb126a69adc903` |
| `release/Network_Diagnostics.plugin` | `f79361451216850fecf9f9914720fb4f1c36861f` |
| 三项诊断脚本（`release/diagnostics/`） | `45dd8bff200a69740178b7a2e0e087a47c8537d8` |

诊断可编辑源码位于 `src/diagnostics/`，构建时内联公共代码，客户端加载独立脚本。
历史输入、Beta 基线和许可证证明独立保留；当前配置构建不再依赖旧正式配置快照。

[当前 SHA256](./RELEASE_CHECKSUM_v7.0.10.md) · [维护流程](./MAINTAINING.md)
