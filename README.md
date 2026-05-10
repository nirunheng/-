# Girlfriend Terminal Pet

Windows 桌宠，素材来自 `new_hh/hh.jpg`。

## 0. 准备
选择图片，命名为image.png替换当前目录下的image.png(或者打开prepare_asset.sh,找到 --source "$PROJECT_DIR/./image.png" \自己修改图片读取路径)
若要修改宠物名字，打开./windows_app/app.py找到代码
```python
class PetWindow(QWidget):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
            self.setAttribute(Qt.WA_TranslucentBackground, True)

            self._pet_name = "pet"
            ...
```
修改self.pet_name 为你自己想要的值，或者生成后修改也可以，总的来说就是可以 不管这一步名字修改（废话）。
## 1. 在Linux里生成素材

```bash
python -m pip install -r .\requirements-wsl.txt
cd /home/ni/entertainment/girlfriend_terminal_pet
chmod +x prepare_asset.sh
./prepare_asset.sh
```

生成结果：

- `assets/pet.png`
- `assets/pet.svg`
- `assets/manifest.json`

## 2. 在 Windows 里安装运行依赖

```powershell
python -m pip install -r requirements-windows.txt
```

## 3. 启动桌宠

在 Windows 资源管理器中打开项目目录，双击 `run_windows.bat`。

如果项目保存在 WSL 中，可通过 `\\wsl$` 路径进入对应目录后再双击启动。

## 4. 当前能力

- 透明背景人物显示
- 始终置顶
- 鼠标拖动
- `idle` / `jump` / `sway` / `kiss` 动作
- 桌宠下方显示名字与陪伴时间
- 右键菜单切换动作、缩放、重置位置、修改名字、显示/隐藏陪伴时间、退出

## 5. 右键菜单

右键桌宠可以看到这些控制项：

- `自动循环`
- `Idle`
- `Jump`
- `Sway`
- `Kiss`
- `摸摸头`
- `开启/关闭自动睡觉`
- `缩放大一点`
- `缩放小一点`
- `重置位置`
- `修改名字`
- `显示/隐藏本次陪伴时间`
- `显示/隐藏累计陪伴时间`
- `退出`

## 6. 养成状态

- 左上角显示 `亲密度` 和 `困倦值`
- `摸摸头` 可以增加亲密度
- 亲密度会被永久记录
- `自动睡觉` 开启后，桌宠困了会先提示，然后隐藏去睡约 20 分钟
- `累计陪伴时间` 会被永久记录
- 可以分别显示/隐藏本次陪伴时间和累计陪伴时间
