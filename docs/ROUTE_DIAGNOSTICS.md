# 分流排查

工具读取当前配置与资源清单，在本机推演规则匹配，并校验资源 hash。

```bash
python3 scripts/route_diagnostics.py match open.spotify.com --json
python3 scripts/route_diagnostics.py match www.apple.com --country CN --json
python3 scripts/route_diagnostics.py match www.apple.com --country US --json
python3 scripts/route_diagnostics.py coverage --json
python3 scripts/route_diagnostics.py audit --json
```

country 使用已观察的 GeoIP 国家码。地区相关域名未提供国家码时，结果包含 NEEDS_GEOIP 和国内/海外两个候选策略。IP-ASN 匹配可通过 --asn 传入已观察的 ASN。

coverage 检查登记的服务域名；audit 比较来源覆盖差异。实际请求的 DNS、节点选择和插件规则在 Loon 请求记录中核对。

## 日志汇总

```bash
python3 scripts/route_diagnostics.py logs /path/to/export.har --json
python3 scripts/route_diagnostics.py triage /path/to/export.har --json
python3 scripts/route_diagnostics.py triage /path/to/export.log --text --json
```

输出仅包含服务类别、策略、状态码段和汇总次数，不包含原始域名、IP、路径、查询参数、节点或凭据。

[网络辅助](./NETWORK_DIAGNOSTICS.md) · [DNS 设置](./DNS_PRIVACY.md)
