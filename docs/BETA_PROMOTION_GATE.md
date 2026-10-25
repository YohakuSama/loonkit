# 测试版验收

验收数据保存在 BETA_ACCEPTANCE_TEMPLATE.json 的本地副本中，包含准确配置 hash、CI、设备场景与观察时间。

```bash
python3 scripts/beta_promotion_gate.py --help
python3 scripts/release_promotion_gate.py --help
```

通过验收的候选由独立发布 PR 提升。当前发布版本的构建决定和校验范围记录在 build/release_spec.json 的 release_gate_file 中。

[测试矩阵](./BETA_DEVICE_MATRIX.md) · [维护流程](./MAINTAINING.md)
