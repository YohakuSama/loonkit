# 网络辅助

[网络辅助插件](../release/Network_Diagnostics.plugin) 集成三个手动诊断入口，并提供可选的网络切换提醒。

[插件文件](../release/Network_Diagnostics.plugin) · [返回首页](../README.md)

## 节点信息

展示选定节点的公网出口 IP、地区、运营商、ASN 及第三方网络标签，有配置入口时显示入口地址。可开启直连出口对照。

## 网络检测

检查所选节点与直连的 HTTPS 连通性，显示状态和请求耗时，并查询 Loon 原生 DNS。DNS 查询需要 Loon Build 988+。网络切换提醒默认关闭。

## 解锁检测

一次按所选节点检测 DAZN、Discovery+、Paramount+、Disney+、Netflix、ChatGPT、YouTube Premium。按服务逐行显示结果。部分平台可能因安全验证或接口异常显示“检测失败”；会员权益与内容播放情况以实际账号为准。

## 更新

更新主配置后，在 Loon 中刷新网络辅助插件及远程脚本。
