---
name: bewlycat-safari
description: 将 Chrome 商店新版 BewlyCat 用 Apple 官方工具转换、修复并升级为本机 Safari 扩展；复用登录态、评论主题及宽屏抽屉修复，保留已选的隐藏弹幕发送栏功能。用户要求转换、更新或修复 BewlyCat Safari 版本时使用。
---

# BewlyCat Safari 转换与升级

交付可运行、可回退的 Safari 应用及可维护工程。官方转换器主要生成 Safari 宿主工程，不能保证浏览器 API、登录态和 Shadow DOM 样式行为完全一致。复用已验证方案，但不要承诺未知新版无需适配。

## 工作流程

1. 先定位现有安装、工程、版本和 bundle ID。读取 [安装与复现说明](README.md)，并检查实际安装位置。保持现有注册应用路径和 bundle ID，保留旧应用用于回退。只升级用户指定的 BewlyCat。
2. 从 [Chrome 商店](https://chromewebstore.google.com/detail/oopkfefbgecikmfbbapnlpjidoomhjpl) 对应的 Google 官方更新服务获取原包，记录来源、实际 manifest 版本、时间和 SHA-256。保留原包与未修改资源；所有修复在副本中进行。可用 `scripts/extract_crx.py INPUT OUTPUT_DIR` 解包 CRX2/CRX3/ZIP；它会检查 ZIP 完整性和路径，拒绝覆盖，**不验证 CRX 签名**。
3. 检查本机 Xcode。通过命令级 `DEVELOPER_DIR` 使用完整 Xcode，不必改变全局 xcode-select。查看当前 `xcrun safari-web-extension-packager --help`；旧版本工具名为 `safari-web-extension-converter`。用官方工具生成 macOS 工程，保存转换警告并逐项判断，不因警告直接删除 `world` 或 `type`。
4. 适配前读取 [兼容修复手册](references/compatibility.md)。涉及宽屏或升级这份用户定制版时，再读 [宽屏定制与回归](references/widescreen.md)。先检查上游是否已修复、结构是否变化，再决定迁移哪些补丁。**不要把 1.8.0 的压缩变量名或文本替换强套到新版。** `scripts/patch_known_baseline.py` 仅对已知原始文件哈希执行当前兼容补丁，隐藏发送栏通过独立选项启用；未知版本拒绝写入。这时继续依据手册进行语义适配，而非把拒绝视为任务终点。
5. 构建前核对宿主与扩展 bundle ID 的前缀和大小写；同步 manifest 与前端更新检测版本，并递增宿主和 appex 的构建号。Xcode 容器的营销版本是独立字段，按 Apple 格式管理，无需照抄扩展的四段版本。按现有签名方式构建；本机 ad-hoc 版本不等于已公证可分发版本。
6. 先验证新构建，再备份并替换稳定位置的应用，注册准确的 appex 路径，刷新 Safari。不要删除扩展数据或重置权限来解决普通升级问题。已授权且生效的权限无需重复询问；确需新的安全设置授权时遵循当前工具权限规则。系统认证交给用户完成，不索取密码。
7. 验证登录头像、首页、设置、视频评论暗/亮主题、普通页及宽屏抽屉各自统一的评论底色、刷新后的持久效果及更新提示。迁移隐藏发送栏功能时，还要验证高度回收、悬停覆盖、箭头固定时视频缩小，以及退出宽屏后发送栏恢复。至少用当前页面和一次刷新验证，保留证据；不能仅凭构建成功声称功能正常。测试无需发表评论、点赞或投稿。输出实际版本、修复摘要、应用位置、验证范围和未解决项。

## 可复用资源

- `assets/safari-background-helper.js` 与 `assets/safari-fetch.js`：此次验证过的专用端口登录态 GET 适配器。只在仍存在同类问题时使用。
- `scripts/test_adapter.cjs [PREPARED_RESOURCES]`：Node 行为测试；不传路径时检查本 skill 的资产，传路径时检查待构建资源中的实际适配器。覆盖来源限制、原标签页、只读 GET、失败回退与取消；不能替代 Safari 实测。
- 从已知原始 1.8.0 重现当前用户版：`python3 scripts/patch_known_baseline.py --source ORIGINAL_RESOURCES --output NEW_RESOURCES --version 1.8.0.6 --hide-widescreen-sender`。本分支的定制版已选择隐藏宽屏发送栏；未要求此定制时省略该选项。输出必须不存在；若不需要全套兼容补丁，不运行此脚本。`--version` 是输出标签，不是历史补丁集选择器。

将中间构建、测试副本放在任务 `work/`，交付物放在 `outputs/`。此 Skill 仅保存在仓库中，不自动安装到技能目录。新版适配产生新经验时，更新本 skill 的适用条件和测试，而非无限叠加 CSS 或宽泛权限。
