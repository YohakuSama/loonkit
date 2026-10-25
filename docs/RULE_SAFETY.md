# 规则审阅

## 变更检查

| 类型 | 检查 |
| --- | --- |
| 精确域名新增 | 来源、有效归属、现有覆盖和批量数量。 |
| 后缀 | 服务所有权、共享租户、公共后缀和跨策略覆盖。 |
| IP / ASN / GeoIP | 地址范围、解析条件、地区与目标策略。 |
| 广告与统计 | 登录、支付、验证码、证书和通知依赖。 |
| 删除 | 来源可用性、替代覆盖和功能回归。 |
| 数量异常 | 完整增删差异与解析结果。 |

现役规则不使用 USER-AGENT 或 DOMAIN-KEYWORD。公共云、托管平台和 CDN 的公共租户根域不归给单个服务。

## 来源格式

DOMAIN-SET 的无前导点域名转换为 DOMAIN，带前导点域名转换为 DOMAIN-SUFFIX。V2Fly include 递归展开并保存快照；不可等价转换的正则进入排除证据。

当前正式版 v6.5.9 起，Apple、Microsoft、PayPal、Bilibili、AppleOTA 的现役订阅均使用 Loon 原生 DOMAIN / DOMAIN-SUFFIX；不生成 AND / OR / NOT 复合 GEOIP，也不声称保留同域名按 CN/非 CN IP 分流。早期 v6.5.8 嵌套规则仅为历史归档；Beta 为内部测试，不对普通用户提供安装入口。上游审阅保留来源和服务边界，不凭推测扩宽域名或共享 CDN。

## 自动化产物

- 来源状态、HTTP 元数据与原始快照。
- 完整新增和删除差异。
- 每条变更的来源 ID、风险分类和策略交叠。
- 受限 beta 更新计划与准确 head CI。

[上游更新](./BETA_UPSTREAM_AUTOMATION.md) · [分流回归](./BETA_EFFECTIVE_AUDIT.md) · [设备测试](./BETA_DEVICE_MATRIX.md)
