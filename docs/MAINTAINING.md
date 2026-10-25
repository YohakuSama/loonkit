# 维护与发布

正式入口为 main/LoonKit.lcf，测试入口为 beta 分支的 beta/LoonKit.lcf。现役构建参数位于 build/release_spec.json，资源和校验值位于 build/release_manifest.json。

## 校验

```bash
python3 scripts/source_lock.py --check
python3 scripts/verify_release.py --check --remote
python3 scripts/beta_channel.py --remote
python3 scripts/license_audit.py --check
python3 scripts/license_evidence.py --check
python3 -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/diagnostics.test.cjs
```

## 规则变更

1. 更新 rules/reviewed/ 下的版本配方，并补充行为回归。
2. 先提交规则资源，再用该提交 SHA 生成配置和 manifest。
3. 同步版本号、checksum、依赖、更新记录及下一轮 beta 基线。
4. 创建发布 PR，检查准确 head 的 CI，再合并发布。
5. 下载正式入口复核 hash，更新发布记录，将维护改动同步到 beta。

历史基线用于确定性构建和回滚。清理工作树前运行 beta_cleanup.py 与 --verify-archives，保留当前配置及校验器依赖。

[发布记录](./RELEASE_READINESS.md) · [规则审阅](./RULE_SAFETY.md) · [第三方许可](./THIRD_PARTY_NOTICES.md)
