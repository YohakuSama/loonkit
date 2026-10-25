# 分流回归

```bash
python3 scripts/beta_effective_audit.py --output /tmp/loonkit-routes.json
python3 scripts/route_diagnostics.py match www.apple.com --country CN --json
python3 scripts/route_diagnostics.py match www.apple.com --country US --json
```

回归覆盖实际配置引用的规则、广告资源开关、服务归属及地区条件。country 参数使用已观察的 GeoIP 国家码；未提供时，地区相关结果标记为 NEEDS_GEOIP。

[排查工具](./ROUTE_DIAGNOSTICS.md) · [设备测试](./BETA_DEVICE_MATRIX.md)
