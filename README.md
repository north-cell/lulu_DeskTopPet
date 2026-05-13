# Lulu Desktop Pet 🦫

水豚噜噜桌面宠物。一个 Windows 优先的小型桌宠应用，会在桌面底部走来走去、被你拎起来、落下、睡觉、换形象，也会在右键菜单和系统托盘里提供常用操作。

> 适合想要一个轻量、可爱、开箱即用的桌面陪伴小工具。

## 下载使用 🚀

### 方式一：下载打包版 📦

推荐普通用户使用打包版，不需要安装 Python。

1. 打开项目的 GitHub Releases 页面。
2. 下载最新版本里的 `LuluDesktopPet.rar`。
3. 解压整个压缩包。
4. 进入解压后的 `LuluDesktopPet/` 文件夹。
5. 双击运行 `LuluDesktopPet.exe`。

注意：不要只把 `LuluDesktopPet.exe` 单独拖出来运行。这个程序依赖同目录下的 `_internal/`、`assets/`、`config/` 等文件夹，必须保持整个文件夹结构完整。

如果 Windows SmartScreen 提示风险，可以点“更多信息”，再选择“仍要运行”。这是未签名个人应用常见提示。

### 方式二：从源码运行 🛠️

适合开发者或想自己改素材、改逻辑的用户。

```powershell
git clone https://github.com/north-cell/lulu_DeskTopPet.git
cd lulu_DeskTopPet

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python -m lulu_pet
```

也可以直接运行：

```powershell
python run_lulu_pet.py
```

## 怎么玩 🎮

- 左键单击：触发一次互动。
- 左键拖拽：把噜噜拎起来；松手后噜噜会下落回桌面底部。
- 双击：播放一个噜噜动图表情包。
- 右键：打开菜单，可以进入专注模式、玩小游戏、休息、签订契约、隐藏/显示、暂停移动、保持置顶、退出。
- 右键 `专注模式`：开始专注或查看学习记录。
- 右键 `小游戏`：打开“打噜鼠”或“贪吃噜”。
- 右键 `签订契约`：输入你希望噜噜称呼你的名字。之后气泡里原本的 `shouting` 会替换成这个称呼。
- 右键 `更换形象`：在“游泳噜噜”、“睡衣噜噜”和“得瑟噜噜”之间切换。
- 系统托盘图标：也可以打开显示/隐藏、专注模式、休息、签订契约、暂停移动、置顶、开机自启动、退出等操作。

### 签订契约 💌

- 通过噜噜右键菜单或系统托盘菜单选择 `签订契约`。
- 在弹窗里输入最多 12 个字符的称呼，例如你的名字、昵称或代号。
- 确认后，噜噜会把气泡台词里的 `shouting` 替换成你的称呼。
- 称呼会保存到 `config/settings.json`，下次启动仍然生效。
- 如果取消弹窗，或输入空白内容，原来的称呼不会改变。

### 专注模式 🍊

- 通过噜噜右键菜单或系统托盘菜单进入专注模式。
- 进入后噜噜会回到屏幕右下角，停止移动，并暂时不允许拖拽。
- 每次进入专注模式时，会随机选取一个 12 到 25 分钟之间的整数分钟作为本次动画切换间隔。
- 噜噜会按本次随机间隔依次切换 `1.gif` 到 `5.gif`；切到 `5.gif` 后会保持该动画，直到结束专注模式。
- 噜噜头顶上方会出现一个小橘子计时器，从 `00:00` 开始正计时。
- 双击小橘子计时器，或在右键/托盘菜单选择 `结束专注模式`，即可退出。
- 退出时噜噜会播放结束动画，并显示“谢谢你陪本噜噜大王学习 + 本次专注时长”的气泡。
- 专注满 1 分钟后会写入学习记录，可在 `专注模式` 菜单里查看。
- 专注期间，普通拖拽、双击表情包和小游戏入口不会打断专注状态。

### 小游戏 🕹️

- `打噜鼠`：全屏反应类小游戏，适合短暂放松。
- `贪吃噜`：全屏贪吃类小游戏。
- 进入小游戏时，桌宠会临时隐藏并暂停移动；游戏结束后恢复到进入前的显示/隐藏和移动状态。
- 专注模式期间不会启动小游戏，避免破坏专注状态。

## 功能特性 ✨

- 🪟 透明无边框桌宠窗口
- 🐾 桌面底部自动行走、跑步、睡觉
- 🤏 拖拽后自然下落，拎起和下落时使用专属噜噜形象
- 🎞️ 双击按素材顺序播放透明 GIF 表情包
- 🍊 专注模式：右下角陪伴、随机间隔专属动画、小橘子正计时、学习记录、结束感谢气泡
- 💬 气泡台词：支持用 `shouting` 占位符生成专属称呼
- 💌 签订契约：用户可以在菜单里自定义噜噜对自己的称呼
- 🕹️ 小游戏：打噜鼠、贪吃噜
- 📌 右键菜单和系统托盘菜单，支持暂停移动、保持置顶和开机自启动
- 👕 可切换游泳、睡衣、得瑟三种形象
- 🍂 暖棕色噜噜风格菜单
- 📦 PyInstaller 打包支持

## 系统要求 💻

打包版：

- Windows 10/11
- 不需要手动安装 Python

源码运行：

- Windows 10/11
- Python 3.10+
- PySide6

## 自己打包 🧰

如果你想从源码生成 Windows 可执行版本：

```powershell
pip install -r requirements.txt
pyinstaller lulu-pet.spec
```

打包完成后，结果会生成在：

```text
dist/LuluDesktopPet/
```

分发给别人时，请压缩整个 `dist/LuluDesktopPet/` 文件夹，而不是只发送 exe。

## 素材与配置 🎨

主要素材目录：

```text
assets/lulu_transparent_gifs/
assets/lulu_FocusMode/
```

`assets/lulu_FocusMode/` 用于专注模式：

- `1.gif` 到 `4.gif`：按每次专注开始时随机生成的切换间隔依次切换。
- `5.gif`：完成前 4 次切换后持续显示，直到结束专注模式。
- `6.gif`：结束专注模式时播放一次。

配置文件：

```text
assets/manifest.json
config/settings.json
config/focus_records.json
```

- `assets/manifest.json` 可配置动作素材和台词。
- `config/settings.json` 保存窗口大小、置顶、说话间隔、边缘限制、开机自启动、移动速度和契约称呼。
- `config/focus_records.json` 保存专注模式学习记录。

### 气泡台词与称呼

`assets/manifest.json` 里的每个动作都可以配置 `lines`。台词中可以写 `shouting` 作为称呼占位符：

```json
{
  "lines": [
    "shouting今天也闪闪发光。",
    "本噜噜大王偷偷看了看shouting，嗯，今天也很可爱。"
  ]
}
```

用户签订契约后，程序不会改写 `assets/manifest.json`，而是在显示气泡时把 `shouting` 替换成用户保存的称呼。默认称呼配置在 `config/settings.json`：

```json
{
  "contract_name": "shouting"
}
```

建议台词保持可爱、淘气、陪伴感强的噜噜语气；如果一句话里不需要用户称呼，也可以不写 `shouting`。

动作素材支持单文件：

```json
{
  "file": "example.gif"
}
```

也支持多文件顺序播放：

```json
{
  "files": ["a.gif", "b.gif", "c.gif"]
}
```

## 开发 🧪

安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

运行测试：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

项目结构：

```text
lulu_pet/      应用代码
assets/        桌宠素材和动作配置
config/        本地设置
tests/         单元测试
scripts/       素材处理和辅助脚本
```

常用入口：

```text
run_lulu_pet.py       源码运行快捷入口
lulu_pet/__main__.py  python -m lulu_pet 入口
lulu-pet.spec         PyInstaller 打包配置
```

## 说明 📌

这是一个偏个人向、轻量级的桌宠项目，目标是“下载后能直接陪你待在桌面上”。目前不包含 Live2D、语音、AI 聊天或插件市场。

素材请按你的使用场景确认授权后再公开分发。
