# 水豚噜噜桌面宠物

一个 Windows 优先的 Python 桌面宠物 MVP。重点是可爱陪伴：透明置顶、拖拽、桌面行走、跑步、顺序播放表情包、气泡台词、右键菜单和系统托盘。

## 功能

- 透明无边框桌宠窗口
- 现成透明 GIF 水豚噜噜本体，不再使用通用水豚绘制替身
- 自动在桌面底部行走、跑步、睡觉
- 左键拖拽，释放后会下落回桌面底部
- 单击触发气泡台词，双击按文件夹顺序循环播放动图表情包，播放期间噜噜停在原地
- 右键“休息一下”会切换为 `qq_lulu_04.gif`，并固定在屏幕右下角
- 右键菜单：休息一下、隐藏/显示、置顶、退出
- 系统托盘：显示/隐藏、置顶、休息一下、退出
- 表情包素材和台词通过 `assets/manifest.json` 替换

## 运行

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m lulu_pet
```

如果只想验证核心逻辑，不需要安装 PySide6：

```powershell
python -m unittest discover -s tests -v
```

## 水豚噜噜素材

- `assets/lulu_transparent_gifs/`: 20 张现成透明底水豚噜噜 GIF，用作桌宠本体动作。

这些素材按本地自用处理，不建议直接随公开项目发布。

表情包播放会跳过几张低清或带场景背景的原始 GIF，避免在桌宠区域出现明显噪点、发糊或背景块。

`assets/manifest.json` 支持两种写法：

- `file`: 单张 PNG/GIF/SVG/WebP
- `files`: 多张 PNG/GIF/SVG/WebP，表情包触发时按文件夹素材顺序循环播放

表情包分组名称保持为：

- `idle`
- `walk`
- `sleep`
- `happy`
- `dragged`
- `clicked`

`duration_ms` 控制动作持续时间，`weight` 控制随机出现概率，`lines` 控制气泡台词。

## 打包 Windows 可执行文件

```powershell
pip install -r requirements.txt
pyinstaller lulu-pet.spec
```

打包结果会出现在 `dist/LuluDesktopPet/`。

### 发给别人使用

当前打包方式是 PyInstaller 的 one-folder 模式，`LuluDesktopPet.exe` 不是一个完全独立的单文件程序。它依赖同目录下的 `_internal/`、`assets/`、`config/` 等运行文件，所以只把：

```text
dist/LuluDesktopPet/LuluDesktopPet.exe
```

单独发给别人通常无法运行。

正确分发方式：

1. 打包后进入 `dist/`。
2. 把整个 `LuluDesktopPet/` 文件夹压缩成 zip。
3. 发给对方这个 zip。
4. 对方解压后运行里面的 `LuluDesktopPet.exe`。

对方电脑建议使用 Windows 10/11。如果首次运行被 Windows SmartScreen 拦截，选择“更多信息”再继续运行即可。不要把 exe 从文件夹里单独拖出来运行，否则资源文件路径会丢失。

## 当前边界

首版不包含 Live2D、大模型聊天、语音、壁纸系统和社区功能。后续可以在不改核心状态机的前提下替换素材或增加 AI 对话面板。
