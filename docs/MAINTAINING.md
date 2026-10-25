# 维护与发布（通用构建系统）

正式入口为 `main/LoonKit.lcf`；个人测试入口为 `beta` 分支的 `beta/LoonKit.lcf`。
**不需要为了新版本创建任何 `release_vXXX.py`、`prepare_release_vXXX.py` 或专用 Workflow。**

## 架构

- `build/release_spec.json`：唯一的当前正式版本号、资源 Commit 和历史校验记录。
- `build/release_recipe.json`：当前版本的只读基线位置/哈希与变更配方。
- `scripts/release_engine.py`：版本无关的字节确定性构建与校验。
- `build/release_manifest.json`：已发布配置、规则资源与插件的完整性记录。
- `scripts/verify_release.py`：通用验证入口；历史旧版验证器仅用于回归，不再为新版本复制。
- `rules/releases/`：冻结的完整规则；不移除大规则、不提供精简版本。
- `.github/workflows/release.yml`：通用发布，读取版本与 SHA，不硬编码发布版本。

## 日常验证

```bash
python3 scripts/source_lock.py --check
python3 scripts/release_engine.py --check
python3 scripts/verify_release.py --check --remote
python3 scripts/license_audit.py --check
python3 scripts/test_suites.py current
# 历史与 Beta 的全套回归可手动运行
python3 scripts/test_suites.py all
node --test tests/diagnostics.test.cjs
```

## 分层 CI

正式 CI 每次检查源码锁、当前配置完整性、当前策略及许可证，并在隔离 Git 副本连续构建两次新版本。历史审计对涉及历史资源/共享模块的 PR、定期及手动操作执行，不再把旧版本脚本与所有普通修改绑定。Beta CI 仍保留个人测试回归。首次发布新版本仍复核远端固定资源，已有 Release 不会重复下载。

## 新版本：一次命令创建基线

程序会检查 Git 工作树是否干净，并先完整预检再写入。普通文件写入异常时会回滚，但**多文件修改并非断电级原子操作**，因此始终通过经 CI 验证的 Git commit 发布。运行：

```bash
python3 scripts/release_engine.py --start-next v7.0.5
```

该命令按版本保留前一正式版基线于 `build/baselines/generated/<旧版本>/LoonKit.lcf`，
更新 `release_spec.json` 中唯一的版本号、历史 SHA256、README、配方和当前校验文件。
**不触动现有规则 URL、DNS/TUN、插件及策略组。** Git tag 保留更早版本的回滚记录。

如需修改分流策略，只编辑 `build/release_recipe.json` 的 `changes` 数组。
每个修改是包含 `find`/`replace` 字符串的对象，旧字符串必须在当前中间结果中**恰好出现一次**。
保存后运行：

```bash
python3 scripts/release_engine.py --write
python3 scripts/release_engine.py --check
python3 scripts/verify_release.py --check --remote
```

`--write` 仅刷新当前版本的配置、Manifest 中的配置 SHA256 与当前 checksum 文档；
上游规则资产变更仍必须按规则源审阅和冻结发布流程进行，不能通过替换发布版本号绕过校验。

在发布 PR 上审核准确 head 的 CI 后合并到 main。Release Workflow 只针对 main 上成功的推送 CI 发布；
已存在的版本标签/Release 不会被重复改写。对于单纯架构/文档变更，保持版本号不变。

**注意：** `--start-next` 用于尚未发布的下一版本，不是对已发布版本的原地修改。
历史基线目录、许可证证据及冻结 Raw 资源在确认依赖前不得清理。
设备体验由维护者自行验证，自动化检查只证明离线构建和已定义的策略回归。

[发布记录](./RELEASE_READINESS.md) · [规则审阅](./RULE_SAFETY.md) · [第三方许可](./THIRD_PARTY_NOTICES.md)

历史脚本整理：v7.0.3 一次性候选发布入口及 v6.5.8 旧的重复准备入口已从当前主线移除，历史 Git tag 仍完整保存原始代码；正在被历史验证器引用的脚本保留，不盲删。
