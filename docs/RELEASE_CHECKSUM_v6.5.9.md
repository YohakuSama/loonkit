# LoonKit v6.5.9 发布校验

以下校验和对应本次非嵌套规则候选的 `LoonKit.lcf`：

```
c0e2bbc6f4565104a7bfa4474d2ac63df617dcc1805216b942712d361d1c23b1  LoonKit.lcf
```

正式配置五份服务订阅改为普通 DOMAIN / DOMAIN-SUFFIX，删除冗余 RegionalCN 远程订阅；其他 31 份资源及原 DNS/GeoIP/F​INAL 设置保持原样。此校验只能验证文件身份，不证明 DNS 泄漏问题已经解决或 iOS VPN 实机稳定。
