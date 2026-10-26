# 测试版验收

验收数据保存在 BETA_ACCEPTANCE_TEMPLATE.json 的本地副本中，包含准确配置 hash、CI、设备场景与观察时间。

```bash
python3 scripts/beta_promotion_gate.py --help
```

旧版专用提升脚本与当前正式版构建流程分开维护。Beta 候选需提供设备记录、准确的配置摘要及相应 CI 结果，经人工审阅后再通过独立 PR 合并。正式版本号与历史配置摘要由 [release_spec.json](../build/release_spec.json) 记录；版本构建和验证命令见 [维护指南](./MAINTAINING.md)。

[测试矩阵](./BETA_DEVICE_MATRIX.md) · [维护流程](./MAINTAINING.md)
