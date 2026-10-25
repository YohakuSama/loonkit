# 设备测试矩阵

| 场景 | 预期 |
| --- | --- |
| 导入与刷新 | 配置、远程规则、图标和插件加载正常。 |
| 地区分流 | Apple、Microsoft、Paypal、Bilibili 的 CN 结果直连，非 CN 结果进入对应策略组。 |
| 登录与支付 | 验证码、双重验证、支付和通知正常。 |
| 播放与下载 | 流媒体、音乐、Steam 登录和下载正常。 |
| 广告开关 | 拦截生效；关闭广告资源后恢复服务分流。 |
| DNS 故障 | 关闭明文回退后，DoH 故障不会触发普通 DNS 查询。 |
| 网络切换 | Wi-Fi、蜂窝和 IPv4/IPv6 切换后路由与 DNS 正常。 |
| 节点故障 | 按所选策略切换，不通过 UDP fallback 直连。 |

记录配置 hash、Loon Build、时间和实际结果。使用 docs/BETA_ACCEPTANCE_TEMPLATE.json 保存验收数据。

[DNS 设置](./DNS_PRIVACY.md) · [测试渠道](./BETA_CHANNEL.md)
