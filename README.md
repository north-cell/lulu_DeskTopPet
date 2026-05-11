# 水豚噜噜桌面宠物

一个 Windows 优先的 Python 桌面宠物 MVP。重点是可爱陪伴：透明置顶、拖拽、桌面行走、跑步、随机表情包、气泡台词、右键菜单和系统托盘。

## 功能

- 透明无边框桌宠窗口
- 现成透明 GIF 水豚噜噜本体，不再使用通用水豚绘制替身
- 自动在桌面底部行走、跑步、睡觉
- 左键拖拽，释放后会下落回桌面底部
- 点击触发气泡台词和随机动图表情包，表情包会在噜噜本体区域播放
- 右键菜单：随机运动、随机表情包、休息一下、设置、隐藏/显示、置顶、退出
- 系统托盘：显示/隐藏、置顶、随机运动、随机表情包、设置、退出
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

当前本地版本包含两类素材：

- `assets/lulu_transparent_gifs/`: 20 张现成透明底水豚噜噜 GIF，用作桌宠本体动作。
- `assets/lulu_stickers/` 和 `assets/lulu_animated_stickers/`: 120 张 SigStick 素材及生成动图，用作随机表情包功能。

这些素材按本地自用处理，不建议直接随公开项目发布。

`assets/manifest.json` 支持两种写法：

- `file`: 单张 PNG/GIF/SVG/WebP
- `files`: 多张 PNG/GIF/SVG/WebP，表情包触发时随机选择一张

表情包分组名称保持为：

- `idle`
- `walk`
- `sleep`
- `happy`
- `dragged`
- `clicked`

`duration_ms` 控制动作持续时间，`weight` 控制随机出现概率，`lines` 控制气泡台词。

## 设置

右键噜噜或系统托盘可以打开“设置”，目前支持：

- 移动速度：40% 到 220%
- 说话间隔：10 到 300 秒
- 保持置顶
- 边缘限制

重新生成动图表情包：

```powershell
python scripts\generate_animated_stickers.py
```

## 打包 Windows 可执行文件

```powershell
pip install -r requirements.txt
pyinstaller lulu-pet.spec
```

打包结果会出现在 `dist/LuluDesktopPet/`。

## 当前边界

首版不包含 Live2D、大模型聊天、语音、壁纸系统和社区功能。后续可以在不改核心状态机的前提下替换素材或增加 AI 对话面板。
