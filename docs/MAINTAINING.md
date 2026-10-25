# 维护与发布

正式入口为 `main/LoonKit.lcf`；个人测试入口为 `beta` 分支的 `beta/LoonKit.lcf`。
新版本统一使用通用构建引擎，无需新增版本专用脚本或 Workflow。

## 当前构建

- `build/release_spec.json`：当前版本、固定资源提交及历史配置 SHA256 台账。
- `build/release_recipe.json`：当前配置的只读基线、SHA256 和逐项变更配方。
- `scripts/release_engine.py`：版本无关的字节确定性构建与校验。
- `build/release_manifest.json`：现役规则的 URL、策略、顺序、数量与摘要。
- `scripts/verify_release.py`：当前发布的完整性检查入口。
- `rules/releases/`：正式版、Beta 及其生成输入仍依赖的完整规则。
- `.github/workflows/release.yml`：读取当前版本和准确提交，在正式 CI 通过后发布。

## 验证

```bash
python3 scripts/source_lock.py --check
python3 scripts/release_engine.py --check
python3 scripts/verify_release.py --check --remote
python3 scripts/license_audit.py --check
python3 scripts/test_suites.py current
node --test tests/diagnostics.test.cjs tests/diagnostics.retry.test.cjs
# 包含 Beta 的完整维护回归
python3 scripts/test_suites.py all
```

正式 CI 检查当前配置、来源锁、策略与许可证，并在隔离 Git 副本中连续模拟两次版本升级。
`maintenance-audit.yml` 对规则、构建及维护代码修改运行完整生产/Beta 回归，并每周检查固定远程资源、历史 Beta URL 与许可证证据。
Beta 分支继续由 `beta-ci.yml` 校验。

## 创建下一版本

在干净的 Git 工作树运行：

```bash
python3 scripts/release_engine.py --start-next v7.0.10
```

命令先完整预检，再将前一正式配置保存为 `build/baselines/generated/<旧版本>/LoonKit.lcf`，
更新版本号、历史摘要台账、README、配方和当前校验文件。现有规则 URL、DNS/TUN、插件及策略组沿用原值。

修改分流策略时，只编辑 `build/release_recipe.json` 的 `changes` 数组。
每个 `find`/`replace` 修改的旧字符串必须在当前中间结果中恰好出现一次，然后运行：

```bash
python3 scripts/release_engine.py --write
python3 scripts/release_engine.py --check
python3 scripts/verify_release.py --check --remote
```

`--write` 刷新当前配置、Manifest 中的配置 SHA256 与当前 checksum 文档；上游规则更新仍需单独审阅并冻结资源提交。
普通写入异常会回滚，多文件写入不具备断电级原子性，发布以通过 CI 的 Git commit 为准。
已存在的版本标签和 Release 不重复改写。仓库维护变更保持当前发布版本号。

## 保留范围与历史恢复

工作树只保留现役用途：当前构建基线、Beta 的基础配置和资源、可复现输入、来源锁与许可证证据。
旧候选配置、重复规则、一次性发布/迁移脚本及其专用测试已移除；通用校验器只检查当前发布。

历史 SHA256 集中保存在 `build/release_spec.json` 的 `historical_profile_sha256`。
工作树必须保留当前版本的 checksum 文档与 `release/SHA256SUMS.<版本>`；旧版本的成对校验文件可从工作树移除。
如旧文件仍存在，验证器会继续核对其版本与台账摘要，并拒绝不完整或未知版本的文件。

旧发布的完整配置、脚本、文档和规则从原 Git tag/commit 恢复。例如：

```bash
git show v7.0.8:LoonKit.lcf
```

检查旧发布流程时，应检出对应标签后使用该版本自带的验证器。
清理只删除工作树副本，既有 Git 历史、标签和固定提交 Raw URL 保留。
日期或目录名不能单独作为删除依据：`rules/inputs/`、Beta 的旧版本目录及许可证材料仍有现役引用。

设备体验由维护者自行验证，自动化检查证明离线构建与已定义的策略回归。

[更新记录](./CHANGELOG.md) · [规则审阅](./RULE_SAFETY.md) · [第三方许可](./THIRD_PARTY_NOTICES.md)
