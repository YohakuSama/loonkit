# 上游更新

默认分支每周一 02:40 UTC 检查上游；也可手动运行 Scheduled Beta Upstream Draft。

## 更新流程

1. 验证当前 beta 配置和不可变资源。
2. 获取登记来源，与现役来源组比较，保存完整差异、原始快照和哈希。
3. 筛选数量受限、来源明确、无归属冲突的精确域名新增。
4. 先提交资源，再生成固定 SHA 的 beta 配置和草稿 PR。
5. 显式运行准确 head 的 Beta CI，随后由维护者审阅合并。

没有合格新增时保留当前版本；来源失败时停止发布。广告、地区条件、直连、AI、支付、共享设施、宽后缀、IP/ASN 及删除操作进入人工审阅。

## 发布器集成检查

基础设施更新后，verify-publisher 使用实际 Actions 凭据创建临时文档分支和草稿 PR，显式 dispatch Beta CI，核对准确提交成功，再关闭 PR、删除临时分支。运行配置保持原内容。

该检查独立于上游是否出现新增，结果保存在 publisher-integration artifact。手动运行可通过 verify_publisher 参数控制。

## 权限

来源审阅 job 只读。草稿发布与集成检查 job 使用 contents、pull-requests、actions 写权限，执行 main 上的代码。仓库需允许 Actions 创建 PR。

计划绑定 beta 提交、配置 hash 和 24 小时有效期；beta 移动后重新生成计划。正常更新不会自动合并 beta 或发布正式版。

[Actions](https://github.com/YohakuSama/loonkit/actions/workflows/beta-upstream-update.yml) · [维护流程](./MAINTAINING.md)
