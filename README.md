# HP-PythonFeiQ v0.8

Python 版飞秋兼容客户端，支持与真飞秋互发消息、文件、文件夹。

> 基于 [PythonFeiQ](https://github.com/thesadabc/PythonFeiQ) 二次开发，感谢原作者。

## 快速开始

### 安装

```bat
install.bat
```

（需要安装 [uv](https://github.com/astral-sh/uv)，脚本会自动创建虚拟环境并安装 pyqt5/rsa 等依赖。）

### 运行

```bat
run.bat
```

或直接：

```bat
.venv\Scripts\python.exe gui\main.py
```

## 配置

编辑 `core/setting.py`：

| 字段 | 说明 |
|------|------|
| `VERSION` | 版本字符串，MAC 部分需要与本机网卡一致（用 `ipconfig /all` 查看） |
| `LOGINNAME` | 登录用户名 |
| `HOSTNAME` | 主机名 |
| `NICKNAME` | 显示昵称 |
| `GROUPNAME` | 分组名称 |

**注意：** `VERSION` 中的 MAC 地址必须与本机不同且不与网络中其他飞秋冲突，否则互发现会失败。

## 功能

- 文字聊天（RSA + Blowfish 加密）
- 发送文件 / 文件夹 / 批量文件
- 接收文件 / 文件夹（弹窗选择保存位置或拒绝）
- 拖拽文件到窗口发送
- 自动发现在线用户 + 分组折叠联系人
- 系统托盘最小化
- 设置页：保存路径、昵称/分组、防火墙解封、多网段、开机自启
- 高 DPI 适配

## 文件结构

```
HP-PythonFeiQ_v0.8/
├── run.bat              # 启动脚本
├── install.bat          # 安装依赖
├── core/                # 核心引擎（零 Qt 依赖）
│   ├── WorkThread.py    # UDP/TCP 协议、消息处理、文件传输
│   ├── setting.py       # 配置文件
│   ├── feiqstruct.py    # 数据结构（Packet/User/Message）
│   ├── IPMSG.py         # IPMSG 协议常量
│   ├── SecurityManager.py  # RSA + Blowfish 加解密
│   ├── SocketHandle.py  # UDP Socket 入口
│   ├── TaskManager.py   # 线程池任务调度
│   ├── UserManager.py   # 用户管理 + View 分发
│   ├── LogHelp.py       # 日志
│   ├── blowfish.py      # Blowfish 加密库
│   └── logging.conf     # 日志配置
└── gui/                 # PyQt5 GUI
    ├── main.py          # 入口
    ├── main_window.py   # 主窗口
    ├── contact_panel.py # 联系人面板
    ├── chat_view.py     # 聊天视图
    ├── bubble_delegate.py  # 气泡渲染
    ├── transfer_manager.py # 传输进度管理
    ├── settings_dialog.py  # 设置对话框
    ├── models.py        # 数据模型
    ├── resources.py     # 配色/QSS
    └── chat_history.py  # 聊天记录持久化
```

核心引擎（`core/` 目录）与 GUI 完全解耦，可直接替换为其他 UI 框架。

## GUI 界面

### 布局

```
┌──────────────────────────────────────────────────┐
│  与 xxx (分组名) 聊天中...            [⚙ 设置]   │
├────────────┬─────────────────────────────────────┤
│ 🔍 搜索    │                                     │
│            │  ┌─────────────────────────────┐    │
│ ▼ 默认分组 │  │  你好！                      │    │
│   ● 张三   │  │                    ╭──────╮ │    │
│   ● 李四   │  │                    │ 好的  │ │    │
│ ▼ 开发组   │  │                    ╰──────╯ │    │
│   ○ 王五   │  │  10:30                       │    │
│            │  └─────────────────────────────┘    │
│            │                                     │
│            │  [📎 发送文件] [📁 发送文件夹]      │
│            │  [📦 批量发送]                      │
│            │  ┌─────────────────────────────┐    │
│            │  │ 输入消息...                  │    │
│            │  └──────────────────── [发送] ──┘    │
└────────────┴─────────────────────────────────────┘
```

- **左侧面板**：搜索框 + 分组折叠树。在线用户绿色圆点 `●`，离线灰色 `○`
- **右侧聊天区**：TIM 风格扁平气泡（自己发浅蓝靠右，别人发浅灰靠左），文件带进度条/取消按钮
- **顶栏**：显示当前聊天对象名称，右侧设置齿轮按钮
- **底栏**：文本输入框（Enter 发送 / Ctrl+Enter 换行）+ 文件按钮

### 使用说明

**发消息**：左侧点联系人 → 输入框打字 → Enter 发送

**发文件**：点 `📎 发送文件` 选择单个文件，或拖拽文件/文件夹到聊天区域

**发文件夹**：点 `📁 发送文件夹` 选择目录，自动打包为飞秋格式发送

**批量发**：点 `📦 批量发送` 多选文件，合并为一条通知发送

**收文件**：收到文件弹窗点"接收"→保存到默认目录；点"另存为"→自选位置；点"拒绝"→不接收

**改昵称/分组**：点 `⚙ 设置` → 个人信息 → 修改后保存，立即生效并通知真飞秋

**最小化**：关闭窗口 → 最小化到系统托盘；双击托盘图标恢复；右键托盘可退出

### GUI 组件详解

| 文件 | 职责 |
|------|------|
| `gui/main.py` | 入口：高 DPI 设置 → 启动 UDP 服务 → 绑定引擎 → 显示窗口 |
| `gui/main_window.py` | 主窗口：组装左右面板、信号桥接（引擎↔UI）、拖拽文件、系统托盘 |
| `gui/contact_panel.py` | 联系人面板：搜索框 + QTreeWidget 分组树，在线/离线状态显示 |
| `gui/chat_view.py` | 聊天视图：QListView + BubbleDelegate 渲染气泡、消息输入框、文件按钮 |
| `gui/bubble_delegate.py` | 气泡渲染：QStyledItemDelegate 自绘 TIM 风格扁平气泡 + 进度条 + 取消按钮 |
| `gui/transfer_manager.py` | 传输管理：queue.Queue + QTimer 安全跨线程进度，取消/超时检测 |
| `gui/settings_dialog.py` | 设置对话框：个人信息/文件路径/防火墙/多网段/开机启动 5 标签页 |
| `gui/models.py` | 数据模型：ContactItem、ChatMessage 纯 Python dataclass，无 Qt 依赖 |
| `gui/resources.py` | 资源：配色常量、头像色池、全局 QSS 样式表、文件大小格式化 |
| `gui/chat_history.py` | 聊天记录：JSON 文件持久化（`gui/chat_history/` 目录），按用户 ID 分文件 |

### 引擎 ↔ GUI 桥接

```
引擎 (core/)                      GUI (gui/)
────────────                     ────────────
Instance.start(sendto, callback)  →  main.py 启动
onViewDispatch(view)              →  _userSignal / _contentSignal
progress_cb(filename, done, tot)  →  TransferManager (queue + QTimer)
file_recv_cb(name, size, type)    →  _fileRecvSignal → 弹窗
cancel_cb(filename)               →  TransferManager._on_engine_cancel_check
sendFile / sendFolder / sendBatch ←  main_window 发送按钮
```

引擎完全不知道 GUI 的存在，只通过回调函数与 GUI 通信。换 UI 框架只需重新实现 `gui/` 目录。

## 协议说明

- UDP 端口 2425，IPMSG 协议
- 文件传输：先发 UDP 通知（20002 加密信封），再通过 TCP 端口 2425 传输
- 加密格式：`20002:{rsa_cipher_hex}:{bf_cipher_hex}\x000:{outer_info}\0`
- 加密信道内：`{text}\0{file_id}:{filename}:{size_hex}:{timestamp}:{file_type}:`
- 加密信道外（明文附件）：`{filename}:{size_hex}:{timestamp}:{type}:\x07{seq}`，多文件用 `\x07` 连接

## 踩坑记录

### 1. 文件夹发送到真飞秋显示"文件传送错误"

**根因：** `_pack_feiq_dir` 打包格式三处错误：size 字段宽度、返回上级条目 name、缺少根目录返回条目。

### 2. MAC/用户名/主机名冲突

**根因：** FeiQ 用 `VERSION(MAC) + LOGINNAME + HOSTNAME` 唯一标识设备，相同则互斥。

## 已知限制

- 图片发送未实现
- 群聊未实现
- 换机器需要修改 `core/setting.py` 中的 MAC/用户名/主机名

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v0.5 | 2026-06-02 | 文件收发基础功能 + 文件夹打包解包 |
| v0.6 | 2026-06-03 | 代码拆分 + 批量收发 + 文件夹接收 + 保存位置弹窗 + 5 个关键 bugfix |
| v0.7 | 2026-06-03 | QQ 风格 PyQt5 GUI：TIM 气泡、分组联系人、拖拽、托盘、设置页、高 DPI |
| v0.7.1 | 2026-06-04 | 修复文字消息接收 bug；引擎 progress_cb 钩子；传输进度条 |
| v0.8 | 2026-06-04 | 核心文件归类到 core/ 目录；设置页支持修改分组名；拖拽/进度条 bugfix；代码清理 |
