# 第三方许可与来源

## 规则来源与许可范围

v6.5.8 的来源路径、哈希和变更范围记录于 [版本配方](../rules/reviewed/v6.5.8/decisions.json)。原始输入、来源锁和第三方许可文本保留在仓库中。

LoonKit 的原创代码、脚本和配置贡献采用 [GPL-2.0-only](../LICENSE) 许可。第三方规则、素材及品牌标识适用各自的版权与许可条件，相关来源及声明保留在仓库中。

## 规则来源

| 来源项目 | 历史来源记录 | 上游许可 | 许可与来源 |
| --- | ---: | --- | --- |
| [blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script) | 41 | GPL-2.0-only | [本地许可文本](../rules/LICENSE.GPL-2.0) · [上游 LICENSE](https://github.com/blackmatrix7/ios_rule_script/blob/master/LICENSE) |
| [v2fly/domain-list-community](https://github.com/v2fly/domain-list-community) | 35 | MIT | [本地许可及版权声明](../rules/LICENSE.MIT-V2FLY) · [上游 LICENSE](https://github.com/v2fly/domain-list-community/blob/master/LICENSE) |
| [felixonmars/dnsmasq-china-list](https://github.com/felixonmars/dnsmasq-china-list) | 1 | WTFPL-2.0 | [本地许可文本](../rules/LICENSE.WTFPL-FELIXONMARS) · [上游 LICENSE](https://github.com/felixonmars/dnsmasq-china-list/blob/master/LICENSE) |
| LoonKit 本地规则 | 10 | 自有贡献采用 GPL-2.0-only；其他内容按实际来源核对 | [来源目录](../rules/sources.json) |

上述共计 87 条历史输入来源记录，完整索引见 [license_sources.json](../build/license_sources.json)。记录数为输入来源条目数，而非独立作者数。


## v7.0.3 服务补充来源

新增的国内 AI 精准域名及 Gemini WebChannel 等规则，参考 [o-ocn/loon-rules](https://github.com/o-ocn/loon-rules) 固定提交 [`47fa36ef0fcbfb9b664bac6fa2f4e574b6107b0f`](https://github.com/o-ocn/loon-rules/tree/47fa36ef0fcbfb9b664bac6fa2f4e574b6107b0f)（GPL-2.0）。只纳入经过策略归属检查的必要规则，不整包镜像其版权规则集。修改后的域名补丁在 `rules/releases/v7.0.3/` 中保留来源信息。

[luestr/ProxyResource](https://github.com/luestr/ProxyResource)（CC BY-NC-SA 4.0，模板）和 [luestr/ShuntRules](https://github.com/luestr/ShuntRules)（分类索引）仅用于参考配置组织及分类方式，未复制其代码、模板或托管的规则正文。

LoonKit 现役规则资源的 SHA256、固定提交、对应策略组及实际规则数量，统一以 [当前发布清单](../build/release_manifest.json) 为准。其余 87 条历史来源的授权索引仍为历史构建记录。

## 许可与署名

使用、修改及分发相关内容时，以其实际适用的许可证和权利声明为准，并保留所需的版权、许可和修改记录。GPL 许可部分还需履行适用的相应许可和源码提供义务；MIT 版权及许可声明保留在仓库内的完整文本中。

[blackmatrix7 上游 README](https://github.com/blackmatrix7/ios_rule_script/blob/master/README.md) 另有转载发布及部分素材来源说明，项目保留该来源链接供使用者核对。

## 来源可追溯性

历史规则构建曾生成 **26 份远程规则、197,765 条匹配**，这些数量对应当时的构建，不是现行配置统计。现行规则数量及资源地址以[发布清单](../build/release_manifest.json)为准。历史构建未保留每条匹配到原始来源的完整对应关系；[来源索引](../build/license_sources.json)记录可追溯的输入。具体来源及授权问题仍需按资源核对。

自动化检查用于验证许可文件与来源资料的完整性，不属于独立的法律权利认定。

## 图标、商标及其他素材

第三方品牌名称、标志和应用图标用于识别相应服务，其商标和素材权利仍归各自权利人。图标信息见 [图标说明](../icons/README.md)。

发现遗漏署名、许可信息不准确或素材权利问题，请通过 [Issues](https://github.com/YohakuSama/loonkit/issues) 提供相应资源路径和参考来源。

[返回首页](../README.md) · [规则来源与资源清单](../rules/README.md)

## v6.5.5 候选的第三方依赖

发布候选只沿用已冻结 RC2 与 beta.4 规则文件，未重新引入不明来源或更换许可证。87 条历史来源记录并非逐条规则的完整溯源，不宣称版权已获得独立认证。当前已验证的许可证正文和原始上游声明继续保留于仓库；`rules/beta/` 与旧版 `rules/releases/` 均可能被仍在运行的历史提交引用。
