# 维护与发布

正式入口为 main 分支的 `LoonKit.lcf`；个人测试入口为 beta 分支的 `beta/LoonKit.lcf`。

## 配置与资源

- `build/profile.json`：正式配置的唯一结构化源，包含策略组、规则顺序、固定资源 URL 与服务登记。
- `build/release_spec.json`：当前版本和历史配置摘要台账。
- `scripts/profile_model.py`：模型验证与确定性渲染。
- `scripts/release_engine.py`：由模型生成配置、资源清单及当前 checksum。
- `build/release_manifest.json`：自动生成的现役规则顺序、归属、数量及摘要。
- `build/runtime.lock.json`：配置 → 插件 → 脚本及规则、图标的完整固定依赖图。
- `build/sources.lock.json`：独立保留的历史编译输入证明。

修改配置时编辑模型，资源必须先发布到固定 Git commit。生成器在写入前检查未定义策略、重复名称、循环引用、FINAL 与宽泛规则顺序：

```bash
python3 scripts/release_engine.py --write
# 仅在审阅资源变更后显式更新依赖证据
python3 scripts/runtime_assets.py --write
python3 scripts/verify_release.py --check --remote
```

生成的 manifest 无需手工维护。只读检查不会更新配置、清单或资源锁。

## 诊断源码与构建

可编辑源码位于 `src/diagnostics/`：

- `common.js` 统一节点上下文、策略组解析及请求处理。
- `node.js`、`network.js`、`media.js` 分别处理三项诊断。
- `Network_Diagnostics.plugin` 定义面向用户的名称、说明与手动入口。

`scripts/build_diagnostics.py` 将公共代码内联到三个独立脚本；客户端无需额外加载公共模块。输出固定使用 `release/diagnostics/` 和 `release/Network_Diagnostics.plugin`，日常维护无需新增日期目录。

更新诊断按依赖顺序进行：

1. 修改源码，运行 `python3 scripts/build_diagnostics.py --write --scripts-only`，提交源码和脚本输出。
2. 将该脚本提交填入 `build/diagnostics.json` 的 `script_commit`，运行 `python3 scripts/build_diagnostics.py --write`，再提交插件。
3. 将插件提交 URL 填入配置模型，重新生成配置并审阅更新资源锁。
4. 运行完整校验与诊断回归。

两次资源提交用于避免配置或插件引用其尚未存在的自身提交。所有正式资源均固定到 40 位 commit，禁止使用 main、分支名或浮动标签。

## 验证

```bash
python3 scripts/source_lock.py --check
python3 scripts/build_diagnostics.py --check
python3 scripts/verify_release.py --check --remote
python3 scripts/license_audit.py --check
python3 scripts/test_suites.py current
node --test tests/diagnostics*.test.cjs
# 包含 Beta 的完整维护回归
python3 scripts/test_suites.py all
```

诊断测试从正式配置和资源锁解析实际插件、脚本及摘要，不写死版本目录。CI 还在隔离 Git 副本中连续模拟两次升级。设备体验仍由维护者在 Loon 实机验证；自动化结果仅代表相应的离线或远程资源检查。

## 创建下一版本

在干净 Git 工作树运行：

```bash
python3 scripts/release_engine.py --start-next v7.0.11
```

命令预检当前发布，记录前一版本摘要，并生成下一版配置、清单、checksum 与发布说明。配置模型和资源引用继续使用原值，不生成旧配置基线或新维护脚本。随后补充发布说明并执行上述验证。

普通写入异常会回滚；多文件更新不具备断电级原子性，以通过 CI 的 Git commit 为发布单位。已有版本标签和 Release 不重复改写。

## 历史兼容

旧正式版本通过 Git tag/commit 恢复，例如 `git show v7.0.9:LoonKit.lcf`。历史客户端的固定 Raw URL 保留在原提交中。

工作树仍保留 Beta、历史编译输入、许可证证明及独立规则回归实际使用的基线；已替代的正式配置补丁、生成基线和旧诊断副本已移除。历史输入证明与当前运行资源锁各自记录明确范围。

[更新记录](./CHANGELOG.md) · [规则审阅](./RULE_SAFETY.md) · [第三方许可](./THIRD_PARTY_NOTICES.md)
