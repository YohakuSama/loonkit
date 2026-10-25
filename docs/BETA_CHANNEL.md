# 测试渠道

当前测试版：**v6.5.9-beta.1**，基于正式版 **v6.5.8**。

[导入测试版](https://raw.githubusercontent.com/YohakuSama/loonkit/beta/beta/LoonKit.lcf)

测试版使用独立的 beta 分支。上游更新先生成草稿 PR，通过校验和审阅后合并；正式版单独发布。

| 项目 | 位置 |
| --- | --- |
| 配置 | beta/LoonKit.lcf |
| 构建与资源清单 | build/beta_manifest.json |
| 验收项目 | [设备测试矩阵](./BETA_DEVICE_MATRIX.md) |
| 更新机制 | [上游更新](./BETA_UPSTREAM_AUTOMATION.md) |
| 回滚 | [固定正式配置](https://raw.githubusercontent.com/YohakuSama/loonkit/3366ee77d3e1ee44788e60ba1381e976406f4596/LoonKit.lcf) |

广告拦截默认启用；停用 Beta-AdBlock-Balanced 远程规则可恢复服务原有分流。

[DNS 设置](./DNS_PRIVACY.md) · [版本记录](./CHANGELOG.md)
