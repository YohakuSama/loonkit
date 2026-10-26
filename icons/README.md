# LoonKit 图标

策略组及网络诊断使用的 PNG 图标统一存放在 `icons/`，尺寸均为 **512×512**。

应用图标的原始素材及统一规范见 [App Store 来源清单](./appstore_sources.json)；可重新生成的脚本为 [build_appstore_icons.py](../scripts/build_appstore_icons.py)。已有图标可编辑 SVG 源文件保存在 [source](./source/)，不参与运行时资源引用。

正式配置通过固定提交的 `icons/*.png` 地址加载图标；资源实际引用以 [LoonKit.lcf](../LoonKit.lcf) 和 [运行资源锁](../build/runtime.lock.json) 为准。旧版本的图标引用保留在相应 Git 提交中。

应用图标和商标归相应权利人所有；素材只用于识别相应策略，不代表平台认可或赞助。
