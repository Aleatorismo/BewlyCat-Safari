# BewlyCat Safari 1.8.0.6

这里保存已经在 Safari 中验证的 Chrome 商店 1.8.0 适配和宽屏定制。它是原仓库的可复现补丁层，不是重新编译 `src/` 得到的新版本；原有 `pnpm build-safari` 不会应用这里的补丁。

## 已保存的修改

| 修改 | 实现位置 |
| --- | --- |
| Cookie 事件参数缺失时仍能通知页面更新登录态 | `scripts/patch_known_baseline.py` |
| 携带登录态的只读 API 请求走原标签页，失败回退且尊重取消 | `assets/safari-background-helper.js`、`assets/safari-fetch.js` |
| 评论继承页面主题，避免暗色文字看不清 | 补丁脚本仅修改外部 CSS 的默认 `:host,:root` 规则 |
| 普通页面及宽屏抽屉评论各自保持统一背景 | `var(--bewly-widescreen-sidebar-bg, var(--bew-bg))` |
| 隐藏宽屏弹幕发送栏、回收高度；保留悬停覆盖和固定时视频缩小 | `--hide-widescreen-sender` 选项；复用上游 ResizeObserver 和抽屉逻辑 |
| 防止反复提示刷新 | manifest 与前端版本同时更新为 `1.8.0.6` |
| Safari 宿主/扩展标识大小写一致、构建号递增 | 下方 Xcode 转换与构建步骤 |

4 个原始资源文件改变，新增 1 个内容脚本；原来的 MAIN-world 注入脚本等其余资源保持一致。详细原理及迁移边界见 [兼容说明](references/compatibility.md) 和 [宽屏回归说明](references/widescreen.md)。

## 从已保存的原包复现

需要 Python 3.9+、Node.js 20+、完整 Xcode 和 macOS Safari。在仓库根目录执行，输出目录必须尚不存在：

```sh
python3 safari-port/scripts/extract_crx.py /path/to/BewlyCat.crx safari-port/work/original
python3 safari-port/scripts/patch_known_baseline.py \
  --source safari-port/work/original \
  --output safari-port/work/patched \
  --version 1.8.0.6 --hide-widescreen-sender
node safari-port/scripts/test_adapter.cjs safari-port/work/patched
```

原包来自 [Chrome Web Store](https://chromewebstore.google.com/detail/oopkfefbgecikmfbbapnlpjidoomhjpl)，扩展 ID 为 `oopkfefbgecikmfbbapnlpjidoomhjpl`。2026-10-02 保存的 1.8.0 CRX SHA-256：

```text
fc3227a47ca07d2f273dadb348f47279be2bab8f6bf022f01aa73f6ef46f2099
```

补丁脚本同时校验 4 个原始文件的哈希。商店下载服务可能已经返回新版本；版本号相同也不保证构建字节相同。哈希不匹配时脚本拒绝写入，应按说明语义迁移，不关闭校验、不强套旧压缩变量名。解包脚本检查 ZIP 结构和路径，但不验证 CRX 签名。

## 使用 Apple 官方工具生成宿主

以下使用 Xcode 27 的工具名；较旧 Xcode 使用 `safari-web-extension-converter`，先查看本机 `--help`。为首次安装选定自己的 bundle ID；升级已有安装时复用其实际 ID 和稳定应用路径。

```sh
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer \
  xcrun safari-web-extension-packager safari-port/work/patched \
  --project-location safari-port/work/projects --app-name BewlyCat \
  --bundle-identifier local.bewlycat.safari \
  --macos-only --swift --copy-resources --no-open --no-prompt
```

构建前检查生成的 `BewlyCat.xcodeproj/project.pbxproj`：宿主 `PRODUCT_BUNDLE_IDENTIFIER` 应为指定 ID，扩展应为其加 `.Extension`，前缀大小写必须完全相同。宿主 `ViewController.swift` 中的 `extensionBundleIdentifier` 也必须等于实际扩展 ID。不要对两个 target 同时传入一个 `PRODUCT_BUNDLE_IDENTIFIER` 覆盖值。

```sh
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer xcodebuild \
  -project safari-port/work/projects/BewlyCat/BewlyCat.xcodeproj \
  -scheme BewlyCat -configuration Release \
  -derivedDataPath safari-port/work/build \
  CODE_SIGN_IDENTITY=- CODE_SIGN_STYLE=Manual CURRENT_PROJECT_VERSION=8 build
codesign --verify --deep --strict safari-port/work/build/Build/Products/Release/BewlyCat.app
```

`8` 是此次验证版的构建号，以后升级应递增。宿主与扩展容器营销版本为 `1.0`，Web Extension 的版本为 `1.8.0.6`，两者独立。这是本机 ad-hoc 构建，不是公证发行版。

新构建验证成功后备份旧应用，再复制到原有稳定安装位置。不要在复制之前删除原应用；不要重置扩展数据。Safari 中启用扩展并授权 B 站；本机未签名构建还需要允许未签名扩展。遵循实际权限提示，由用户完成系统认证。转换警告、构建成功和签名验证均不能替代功能回归。

## 维护与验证

- `scripts/test_adapter.cjs` 覆盖端口来源、目标 origin、原标签页、GET 限制、失败回退、取消。
- [SKILL.md](SKILL.md) 是仓库内的转换与升级工作流，不会自动安装到个人技能目录。
- Safari 回归需覆盖登录显示、普通/宽屏评论、暗/亮主题、隐藏发送栏、悬停覆盖、箭头固定、退出和刷新。已完成的实际验证范围见两份参考说明；当前背景修复最后一轮实测为暗色，不能据此声称亮色全部通过。
- 不提交下载包、生成的 Xcode 工程、`.app`、DerivedData、日志、浏览器会话、账号数据或个人安装路径。这些在 `work/`/`outputs/` 内生成并已忽略。

本目录的资产及脚本保留此前验证过的实现。源码级迁移到未知新版是后续工作，需要重新验证；不能将这次提交描述为所有未来版本的自动适配。
