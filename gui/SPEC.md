# HP-PythonFeiQ v0.7 GUI 重设计规格

## 目标

在 `gui/` 文件夹中用纯 PyQt5 构建 QQ 风格聊天界面，引擎代码（WorkThread.py 等）不做任何修改。

## 引擎接口（不变）

```python
Instance.start(sendfunc, onViewDispatch)    # 初始化，传入 UDP 发送函数和视图回调
Instance.file_recv_cb = callback              # 设置文件接收回调
Instance.appendContent(TextContent(...))      # 发送文字消息
Instance.sendFile(peer_id, filepath)          # 发送单个文件
Instance.sendFolder(peer_id, folderpath)      # 发送文件夹
Instance.sendBatchFiles(peer_id, filepaths)   # 批量发送文件
Instance.stopAll()                            # 关闭

# 回调
onViewDispatch(view)   # view.type() → VIEW_USER / VIEW_CONTENT
file_recv_cb(filename, filesize, filetype) → (save_path, accepted)
```

## 视觉设计

### 配色

| 元素 | 颜色 | 说明 |
|------|------|------|
| 顶栏渐变 | `#ffb74d → #f5a623` | 浓橙暖色，32px高 |
| 顶栏文字 | `#fff` | 白色标题 |
| 侧边栏背景 | `#faf9f6` | 暖白 |
| 联系人选中 | `#fff8f0` | 淡橙高亮 |
| 聊天区背景 | `#fff` | 纯白 |
| 自己发的气泡 | 背景 `#f0f4fb` 边框 `#dce8f6` | 淡蓝 |
| 对方的气泡 | 背景 `#f5f5f5` 边框 `#e0e0e0` | 浅灰 |
| 发送按钮 | `#f5a623` | 浓橙，白字 |
| 在线指示 | `#4caf50` | 绿色圆点 6px |

### 布局（1100×700 默认，适配 1080P，弹性缩放）

```
┌─────────────────────────────────────────────┐
│ HP-PythonFeiQ              [用户名]  32px    │  浓橙渐变顶栏
├────────────┬────────────────────────────────┤
│ 🔍 搜索    │  与 XXX (分组) 聊天中...         │
├────────────┤────────────────────────────────┤
│ ▼ 分组(2)  │                                │
│  ● QT-oh.. │  对方: 嗯在的，发过来吧          │
│    文件发.. │                                │
│  ● Berial2 │  自己: 发了，注意查收            │
│    好的收.. │                                │
│ ▶ 同事(3)  │                                │
│            │                                │
│            │                                │
├────────────┼────────────────────────────────┤
│            │ [📎发送文件] [📁发送文件夹] [📦批量]│
├────────────┼────────────────────────────────┤
│            │ [输入消息...          ] [发送]   │
└────────────┴────────────────────────────────┘
```

- 左侧面板 220px 固定宽度，联系人列表 + 搜索框 + 可折叠分组
- 右侧弹性填充，QSplitter 允许拖拽调整分栏比例
- 气泡最大宽度 60%，TIM 小圆角（8px）+ 细边框

### 联系人条目

每个联系人显示：头像圆圈（32px 渐变色） + 昵称（粗体） + 最后消息预览（灰色小字） + 在线绿点（6px）

分组标题可点击折叠/展开，显示在线人数。

### 消息气泡

- 自己发的：右对齐，淡蓝底 `#f0f4fb` + `#dce8f6` 边框，8px 圆角
- 对方发的：左对齐，浅灰底 `#f5f5f5` + `#e0e0e0` 边框，8px 圆角
- 时间分割线：居中灰色小字 `10:30`
- 每条消息带时间戳

### 高 DPI 适配

```python
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
```

所有尺寸使用相对比例，窗口默认 1100×700（适配 1080P 屏幕）但可自由缩放。

### 头像上传/自定义

- 点击自己的头像区域弹出文件选择框，选择本地图片作为头像
- 支持 PNG/JPG/BMP，自动缩放裁剪为圆形
- 头像存储在 `gui/avatar.png`，下次启动自动加载
- 默认无头像时使用昵称首字生成彩色圆形文字头像

### 系统托盘

- 最小化时隐藏到系统托盘（`QSystemTrayIcon`）
- 托盘图标右键菜单：显示主窗口 / 退出
- 双击托盘图标恢复窗口
- 消息到达时托盘闪烁提示

### 图片发送

- 文件按钮旁新增"📷 发送图片"按钮
- 选择图片文件后，聊天区显示缩略图预览（120×120 以内嵌在气泡中）
- 接收到的图片同样显示缩略图，点击可原图查看
- 底层仍通过现有 `sendFile` 传输，只是前端加预览

### 拖拽发送

- 整个窗口接受文件拖放（`setAcceptDrops(True)`）
- `dragEnterEvent` 时显示半透明橙色蒙层 + "拖拽文件到这里发送" 提示
- `dropEvent` 时获取文件路径列表，调用 `Instance.sendBatchFiles()` 或 `Instance.sendFile()`

## 文件结构

```
gui/
├── __init__.py
├── main_window.py      # 主窗口，组装所有组件
├── contact_panel.py    # 左侧联系人面板（搜索框 + 分组列表）
├── chat_view.py        # 右侧聊天区（消息列表 + 气泡 delegate + 输入框 + 文件按钮）
├── models.py           # 数据模型（ContactItem, ChatMessage）
├── resources.py        # 颜色常量、样式表 QSS
├── settings_dialog.py  # 设置对话框
└── main.py             # 入口：启动 UDP 服务器 + 创建窗口
```

## 功能清单

### 已实现 ✅

- [x] 文字消息发送
- [x] 发送单个文件（含聊天窗气泡提示）
- [x] 发送文件夹（含聊天窗气泡提示）
- [x] 批量发送多个文件（含聊天窗气泡提示）
- [x] 接收文件弹窗（接收/另存为/拒绝）
- [x] 拖拽文件到窗口发送（含聊天窗气泡提示）
- [x] 自动发现在线用户
- [x] 按分组折叠/展开联系人
- [x] 高 DPI 屏幕适配（窗口比例 + QT_SCALE_FACTOR）
- [x] 窗口自由缩放
- [x] 系统托盘最小化（托盘图标 + 右键菜单退出）
- [x] 设置页面（保存路径、昵称头像、防火墙、多网段、开机自启）

### 未实现 / 有问题 ❌

- [x] 文字消息接收 — 已修复：`EncryptTextRecvHandler` 用 `\0` 而非 `:` 定位加密数据边界（v0.7.1）
- [ ] 头像上传/自定义 — UI 入口已有，逻辑未完成
- [ ] 图片发送 — 按钮已移除，待后续版本
- [ ] 文件传输进度条 — 引擎已加 `progress_cb` 钩子，GUI 进度条 UI 待实现
- [ ] 开机自启动注册表 — 代码已有，未完整测试

### 视觉变更（相对于原始 SPEC）

| 原始设计 | 实际实现 | 原因 |
|---------|---------|------|
| 浓橙渐变顶栏 32px | 无自定义顶栏 | 无边框窗口拖拽/缩放问题无法解决，改用系统原生标题栏 |
| 无边框窗口 | 正常 Windows 标题栏 | PyQt5 frameless 在 Win11 下事件处理不可靠 |
| 📷 发送图片按钮 | 已移除 | 用户要求去掉 |
| 顶栏窗口控制按钮 | 使用系统自带 | 随无边框方案一起回退 |
| 设置按钮 | 移到聊天标题栏右侧 | 替代原顶栏中的齿轮按钮 |

## 引擎变更

为支持文件传输进度，在 `WorkThread.py` 中加了最小钩子（不改现有逻辑）：
- `Instance.progress_cb` — 回调属性，签名 `(filename, bytes_done, total_bytes)`
- TCP 发送/接收循环中调用 `progress_cb`
