# 已验证修复与新版迁移

基线：Chrome BewlyCat 1.8.0，Safari 本地修复版现为 1.8.0.6（构建 8），Xcode 27.0 (27A266a)，2026-10-03 至 2026-10-04 验证。这里的结论来自该组合，未来浏览器、插件和 B 站页面可能变化。

## 登录态与后台事件

**症状**：B 站已登录，BewlyCat 仍显示登录入口；部分后台请求没有携带网站会话。

**有效改动**：后台 `doCachedRequest(message,api,tab,cookies,signal)` 内复制 api 对象并附加原请求 `tab?.id`，仅将既有 `fetch(requestUrl,fetchOpt)` 改为 `bewlySafariFetch(requestUrl,fetchOpt,api._safariTabId)`。附加 assets 中的后台 helper，在 manifest 原 isolated 内容脚本组首位加载 `safari-fetch.js`。不要放进 MAIN world。

适配器通过 `tabs.connect(tabId, {name:'bewly:safari:authenticated-get',frameId:0})` 向**发起请求的标签页**请求数据。限定既有 `credentials:include` 的 GET、精确 `https://api.bilibili.com` origin；内容脚本再次检查来源扩展、目标 origin 和 URL userinfo，使用该标签页现有登录态 fetch。12 秒内容请求超时、13 秒端口超时；关闭/失联回退原 fetch，取消请求保持取消，不重发。不要选任意 B 站标签页，否则会混淆 profile/账号；不要扩展到 POST、其它域或导出 cookie。

**事件异常**：旧监听器解构 `cookies.onChanged` 的参数，Safari 有时参数缺失。改成接收 `changeInfo`，使用 `changeInfo?.cookie`；没有 cookie 时触发 `scheduleBroadcastLoginStateChanged()` 并返回，正常路径照旧。

历史线索：[WebKit 260676](https://bugs.webkit.org/show_bug.cgi?id=260676)、[WebKit 267514](https://bugs.webkit.org/show_bug.cgi?id=267514)。它们是排查线索，不代表当前系统一定仍有问题。先观察实际代码和运行行为。

普通 `runtime.onMessage` 桥接曾被原有监听器干扰，专用端口方案通过测试。不要为修复登录关闭 Safari 跨站跟踪保护。此次只验证了登录显示和读取；不能宣称所有账号写操作、多账号切换都完整验证。

## 暗色评论文字难以辨认

用户使用 **BewlyCat 内置暗色**，不是 Noir。Safari 外部内容样式中的 `:host,:root{...}` 给 B 站评论 Shadow DOM 宿主重新设置浅色默认主题变量，使文字与背景接近。

只修改 manifest 引用的 `dist/contentScripts/style.css`：将那条默认令牌规则的 `:host,:root{` 限定为 `:root{`，让评论组件继承页面主题。1.8.0 中匹配一次；新版需定位对应规则和变量来源，不做全局替换。

不要改 `index.global.js` 里 BewlyCat 自有 Shadow UI 的内嵌主题规则；它仍需要原本的 host 令牌。验证页面根节点、`bili-comments` 和评论子组件的 `--bew-text-1`、`--bew-bg` 及计算颜色在暗/亮模式一致，临时测试主题后恢复原设置。

## 评论背景应跟随所在容器

此前文字修复后，普通页面一级评论整块背景仍比页面亮。1.8.0.4 将其改用 `var(--bew-bg)`，解决了普通页灰块，却让灰色宽屏抽屉出现深色卡片。**该旧规则已被 1.8.0.6 替代，不要再重放旧背景值，也不要叠加两套修复。** 同一外部内容 CSS 的最终规则为：

```css
/* Safari: comment cards follow their current container in both themes.
   Widescreen drawer tokens are inherited only while inside that drawer. */
:host(bili-comment-renderer),
:host(bili-comment-renderer) #body {
  background-color: var(--bewly-widescreen-sidebar-bg, var(--bew-bg)) !important;
}
```

抽屉变量由 `#bewly-widescreen-root` 提供，评论移入时继承；移出后变量消失，自动回退普通页面底色。不要全局设置该变量或重写 `--bew-bg`，否则会污染其它控件。保持主题跟随，不写死纯黑或灰色；保留输入框、标签、图片及交互状态有用途的底色。新版先确认 host 名称、`#body` 和变量作用域仍匹配。曾尝试在 MAIN-world 注入脚本修正 `#body.dark`，效果不成立，已撤回；最终 `inject.global.js` 与上游完全一致。

普通视频页、宽屏抽屉及二者切换已验证；实测颜色和 Shadow DOM 重新创建的注意事项见 [宽屏定制与回归](widescreen.md)。1.8.0.6 的这一轮实际验证为暗色，未来升级仍应复查亮色，不能把主题变量设计当成亮色现场测试已完成。

## 版本同步

只改 manifest 会使前端反复提示“需要刷新”。1.8.0 内 `dist/contentScripts/index.global.js` 的 `const mr="1.8.0";` 是对应前端版本常量，当前同步为 1.8.0.6；变量 `mr` 仅对这个压缩构建有效。新版定位更新检测的实际常量，勿全局替换所有版本字符串。保留原上游版本记录，并明确本地修订号；不要将新版降级到历史版本。

## 构建、安装和回归

使用官方工具当前帮助确认参数；此次用了 macOS-only、Swift、copy-resources、no-open、no-prompt，名称 BewlyCat。转换器一度让宿主 bundle ID 大小写与 appex 前缀不一致，导致验证失败；修正一致即可，不必重做扩展功能。`type`/`world` 警告不等同于必然不支持。

此次构建命令模板（路径按任务调整，构建号递增）：

```sh
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer xcodebuild \
  -project 'projects/BewlyCat/BewlyCat.xcodeproj' -scheme BewlyCat \
  -configuration Release -derivedDataPath 'work/build/BewlyCat' \
  CODE_SIGN_IDENTITY=- CODE_SIGN_STYLE=Manual CURRENT_PROJECT_VERSION=9 build
```

保存完整日志；检查最终 `.app` 和 `.appex` 的 Info.plist 版本与 ID，再运行 `codesign --verify --deep --strict`。这是签名完整性验证，不等于公证或 Safari 功能验证。先备份旧 app，使用 `ditto` 安装到现有稳定路径，必要时 `pluginkit -a` 注册准确的内嵌 appex，再打开宿主、刷新 Safari 检查实际加载版本。不要同时注册一堆不同路径的旧副本。失败时恢复旧 app 并重新注册，保留失败日志。

本机无正式开发者证书时采用 ad-hoc；Safari 需要“允许未签名的扩展”，重启后可能需重新打开。用户以前完成过认证和网站授权，不要假定新会话拥有未授予的新权限，也不要对已生效的设置反复索取确认。关于当前签名/运行要求，可查 Apple 官方 [运行 Safari Web Extension](https://developer.apple.com/documentation/safariservices/running-your-safari-web-extension)。

验证顺序按现场情况安排：资源语法检查 → 适配器行为测试 → Release 构建/签名 → Safari 首页登录头像与设置 → 评论暗/亮主题、楼中楼、灰块、输入框 → 刷新后的持续效果。记录未覆盖项目。UI 操作无效时读取新状态后再尝试；不要把点击成功当成启用成功。无法自动勾选或系统认证需用户操作时，精确说明剩余步骤。

## 最小改动审计

1.8.0 最终与原始 22 文件相比：4 个修改（background/index.js、contentScripts/index.global.js、style.css、manifest.json），新增 safari-fetch.js；其它文件包括 MAIN 注入脚本未改。源码未全量重写。下一版不强求同样数量，但每处差异应有具体目的。原 Chrome update_url 并不会为本地 Safari 包自动转换和重打补丁；以后更新需要重新打包并验证。
