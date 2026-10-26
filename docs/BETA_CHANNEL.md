# 测试渠道

测试渠道配置版本：**v6.5.9-beta.1**；其构建基线为历史正式版本 **v6.5.8**，与当前 `main` 上的正式配置分开维护。版本关系见 [Beta 资源清单](../build/beta_manifest.json)。

[导入测试版](https://raw.githubusercontent.com/YohakuSama/loonkit/beta/beta/LoonKit.lcf)

测试版使用独立的 beta 分支。上游更新先生成候选分支，通过校验后审阅合并；正式版单独发布。

| 项目 | 位置 |
| --- | --- |
| 配置 | beta/LoonKit.lcf |
| 构建与资源清单 | build/beta_manifest.json |
| 验收项目 | [设备测试矩阵](./BETA_DEVICE_MATRIX.md) |
| 更新机制 | [上游更新](./BETA_UPSTREAM_AUTOMATION.md) |
| 历史基线恢复 | [Beta 构建所用的固定正式配置](https://raw.githubusercontent.com/YohakuSama/loonkit/6eef8e7c218330d5f62a63d3ce155395b566d2db/LoonKit.lcf)（不是最新正式版） |

广告拦截默认启用；停用 Beta-AdBlock-Balanced 远程规则可恢复服务原有分流。

[DNS 设置](./DNS_PRIVACY.md) · [版本记录](./CHANGELOG.md)
