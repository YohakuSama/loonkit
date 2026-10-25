# LoonKit v6.5.9：原生分流规则替代 GeoIP 嵌套规则

## 背景与修复

用户在 iOS Loon 中确认：实际请求命中旧版六份 `AND,(...,(GEOIP,CN))` 或 `AND,(...,(NOT,((GEOIP,CN))))` 时，VPN 反复重启。减少复合规则数量、修改内部 `no-resolve` 均未消除故障。

应用户要求，PR #141 的非嵌套实验通过静态 CI 后进入仓库，并由 v6.5.9 正式发布实施替换：

- **正式配置入口：** [`LoonKit.lcf`](../LoonKit.lcf)；现在属于 v6.5.9。
- **五份现役资源：** [`rules/releases/v6.5.9/`](../rules/releases/v6.5.9/)（AppleOTA、Bilibili、Microsoft、Apple、Paypal），全部使用 `DOMAIN` / `DOMAIN-SUFFIX`，无 `AND`/`OR`/`NOT` 复合逻辑。
- **冗余清理：** 旧版独立远程 `Our-RegionalCN` 的 2553 条复合规则全部停止加载（订阅条目删除）；原正式版配置末尾 `GEOIP,CN,DIRECT,no-resolve` 已提供 CN GeoIP 回退；`FINAL,Final` 仍然保留。
- 其他 31 份订阅、DNS/DoH/TUN、Host、Proxy Group、节点和插件完全不变。
- 原来的实验配置 `LoonKit.NativeRulesTrial.lcf` 与 `rules/experiments/v6.5.8-native-no-composite/` 不再保留在工作分支/正式发布树内，避免两个配置并存造成误导。它们可以在历史固定 Git 提交中追溯；**v6.5.8 的完整正式发布文件与规则不删**，仍可历史回滚。

现役配置拥有 36 份远程订阅、196486 条普通/其它匹配（其中五份是 2654 条普通域名规则）。所有正式资源 URL 固定于提交，不从浮动 main 直接加载。

## 意图与可观测限制

此改动只是从**规则运行时稳定性风险**角度替换语法：

- **过去**：Apple、Microsoft、PayPal、Bilibili/OTA 的同一域名根据 CN/非 CN 目标 IP 条件自动选 DIRECT 或专用策略，实际命中会触发用户报告的 VPN 重启。
- **现在**：普通 DOMAIN/DOMAIN-SUFFIX 先捕获服务域名，再交给该服务组。国内服务即使 IP 位于 CN，也可能进入代理组；**地区精确切分不再等价**。
- 不能用无条件的 DIRECT 域名来偷换“国内 IP 直连、海外 IP 代理”的原有设计；如果要求对同一域名严格根据实际解析 IP 分流，需要另行获得 Loon 的稳定支持或上游修复。
- 用户还报告此前“VPN 不重启”配置存在 **DNS 泄漏**，本版 DNS 参数原样保留，因此 **没有解决 DNS 泄漏**。
- 仅有静态 CI 的成功证据，**真实匹配服务请求时是否不再重启，必须在用户设备上测量**。

建议在 Loon 中刷新远程规则后实际访问 Microsoft、Apple、Bilibili、PayPal 的规则命中域名，查看实际请求日志，记录 VPN 是否重启；同时测量 DNS 解析器、UDP 53、IPv6、App 内加密 DNS 失败回退选项及对应服务组策略。若异常仍然出现，应将最小真实命中记录及脱敏的 Network Extension 日志用于向 Loon 官方反馈。

## 保障与溯源

- `scripts/release_v659.py` 根据冻结 v6.5.8 构建**严格复现 v6.5.9 配置**，校验规则内容、固定提交、字节哈希、36 份资源以及未改动的非资源配置。
- `scripts/release_v658.py` 保留历史验证模式，读取 `build/baselines/v6.5.8/`；历史发行校验不因修复被覆盖。
- `tests/test_native_only_loom_trial.py` 对现役无嵌套规则、冗余移除与 DNS/GeoIP 末尾不变做回归检查。
- 旧来源及丢失的逐行来源限制见 [来源审计](https://github.com/YohakuSama/loonkit/blob/diagnostics/geoip-six-isolation-20261025/docs/V658_REGIONAL_PROVENANCE_AUDIT.md)。

正式版不构成 Loon 官方产品的规则兼容性或性能保证。
