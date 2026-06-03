# HP-PythonFeiQ v0.6

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
.venv\Scripts\python.exe MainWindow.py
```

## 配置

编辑 `setting.py`：

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
- 自动发现在线用户
- 分组支持

## 文件结构

```
HP-PythonFeiQ_v0.6/
├── MainWindow.py       # 最简 Qt5 GUI（纯代码构建，无 .ui 依赖）
├── WorkThread.py       # 核心引擎：UDP/TCP 协议、消息处理、文件传输（零 Qt 依赖）
├── setting.py          # 配置文件
├── feiqstruct.py       # 数据结构（Packet/User/Message）
├── IPMSG.py            # IPMSG 协议常量
├── SecurityManager.py  # RSA + Blowfish 加解密
├── SocketHandle.py     # UDP Socket 入口
├── TaskManager.py      # 线程池任务调度
├── UserManager.py      # 用户管理 + View 分发
├── LogHelp.py          # 日志
├── blowfish.py         # Blowfish 加密库
└── logging.conf        # 日志配置
```

核心引擎（WorkThread.py 及其依赖）与 GUI 完全解耦，可直接替换为其他 UI 框架。

## 代码精简（v0.6 第二轮）

基于"保留核心引擎、极简 GUI、为换 UI 做准备"的原则，从原项目删除了以下无用代码：

### 删除的文件

| 文件 | 原因 |
|------|------|
| `FeiQ.ui` / `FeiQ.py` | Qt Designer UI 定义，改用纯代码构建 GUI |
| `Widget.py` | 自定义头像绘制委托（130行），改用 QComboBox 纯文本联系人 |
| `res_rc.py` | 编译的头像/表情资源（200+ 个 bmp），不再需要 |
| `emoji/` | 表情包目录 |
| `headpic/` | 头像图片目录 |
| `resource/` | 静态资源目录 |
| `config` | 原项目 git 配置残片 |
| `message_handlers.py` | 从原备份拆出的 handler，已内联回 WorkThread.py |
| `message_senders.py` | 从原备份拆出的 sender，已内联回 WorkThread.py |
| `feiq_pack.py` | 文件夹打包工具，已内联回 WorkThread.py 并修复 bug |
| `Emoji.py` / `Emoji.ui` / `EmojiDialog.py` | 表情功能（从未完整实现） |
| 6 个 `test_*.py` | 开发调试脚本 |
| `capture.py` / `compare_format.py` | 协议分析工具 |
| `main.py` / `unpack_feiq.py` | 废弃入口/工具 |

### 精简后的 MainWindow

| 改动 | 说明 |
|------|------|
| 去 QWebEngineView | 聊天记录改用 QTextEdit（去掉 PyQtWebEngine 依赖） |
| 去双标签页 | 联系人从 QListView+头像改为 QComboBox 下拉选择 |
| 去 .ui 文件 | 布局纯代码构建，无 Qt Designer 依赖 |
| 保留全部功能 | 文字聊天、文件/文件夹/批量收发、接收弹窗完整可用 |

### 编码修复

`IPMSG.ENCODETYPE` 从 `gb2312` 改为 `gbk`（gbk 是 gb2312 超集），解决文件名含繁体字/生僻字时 `UnicodeEncodeError` 崩溃。

最终从 30+ 个文件精简为 **12 个核心文件**（含 logging.conf），引擎零 Qt 依赖。

## 协议说明

- UDP 端口 2425，IPMSG 协议
- 文件传输：先发 UDP 通知（20002 加密信封），再通过 TCP 端口 2425 传输
- 加密格式：`20002:{rsa_cipher_hex}:{bf_cipher_hex}\x000:{outer_info}\0`
- 加密信道内：`{text}\0{file_id}:{filename}:{size_hex}:{timestamp}:{file_type}:`
- 加密信道外（明文附件）：`{filename}:{size_hex}:{timestamp}:{type}:\x07{seq}`，多文件用 `\x07` 连接

## 文件夹传输

真飞秋的文件夹传输采用打包-发送模式：先将文件夹打包成单个二进制文件，再作为"文件"发送。接收方下载后解包还原。

### 打包格式

```
[0x000-0xBFF]  0xC00 字节固定头部 (填充 0)
[0xC00-0xC03]  4 字节占位符
[0xC04-...]    条目链，每个条目格式: {hlen:04x}:{meta}
```

### 条目类型

| type | 含义 | meta 格式 |
|------|------|-----------|
| 1 | 文件 | `{name}:{size:09x}:1:14={mtime}:0=16:` + 二进制数据 |
| 2 | 目录 | `{name}:0:2:14={mtime}:0=16:` |
| 3 | 返回上级 | `.:0:3:14={mtime}:0=16:` |

### TCP 下载命令

| cmd | 值 | 用途 |
|-----|-----|------|
| GETFILEDATA | 96 | 下载原始打包数据（含头部） |
| GETDIRFILES | 98 | 下载目录列表（不含头部） |

请求格式：`{VERSION}:{packno}:{user}:{host}:{cmd}:{packet_hex}:{file_id_hex}:0:\0`

## 批量收发

与真飞秋行为一致：多个文件合并为一条通知，`\x07` 分隔。

通知格式（加密信道外）：
```
# 单文件
filename:size:ts:1:\x07

# 多文件
filename1:size1:ts1:1:\x071:filename2:size2:ts2:1:\x072
```

- 第一个文件无 ID 前缀，后续文件带 `{file_id}:` 前缀
- `\x07` 后跟的数字是文件序号（从 1 开始），单文件无数字
- TCP 请求时 file_id 使用 0-based 索引（第一个文件 id=0）

## 踩坑记录

### 1. 文件夹发送到真飞秋显示"文件传送错误"

**现象：** 数据实际已传完，但真飞秋窗口报错且不关闭。

**根因：** `_pack_feiq_dir` 打包格式三处错误：
- 文件 size 字段宽度应为 `%09x`（9 位固定宽十六进制），不是 `%x`
- 返回上级条目（type=3）name 应为 `.:0:3:...` 不是 `.:.:...`
- 根目录缺少返回上级条目（所有子目录结束后需要一个）

**解决：** 用 Wireshark 抓真飞秋→真飞秋的包，逐字节对比打包文件。

### 2. 接收文件得 0 字节

**现象：** 代码拆分后发送正常，接收下载得 0 字节。

**根因：** 批量下载 `download_batch` 用了解析出的 `file_id`（1-based），而真飞秋对单文件通知期望 `file_id=0`（通知里 `\x07` 后无数字，隐式 id=0）。TCP 请求带 `file_id=1` 导致真飞秋找不到文件。

**解决：** 改用 `enumerate` 的 `idx`（0-based）作为 file_id。

### 3. 文件夹接收不触发解包

**现象：** 收到文件夹通知但下载后不解包，保存为原始二进制文件。

**根因：** Handler 解析加密通知时只取了前 3 个字段（file_id, filename, size），忽略第 5 个字段 `file_type`。导致 `download_file` 始终以 `file_type=1`（普通文件）处理，不执行解包逻辑。

**解决：** 从 `parts[4]` 解析 `file_type` 并传入 `download_file`。

### 4. 选择保存目录无效

**现象：** 接收弹窗选"存到..."后文件仍保存到默认 downloads 目录。

**根因：** `download_batch` 中 `custom_dir` 仅对 `file_type < 2`（普通文件）生效，文件夹走 `else` 分支忽略自定义路径。

**解决：** 文件夹先下载到默认位置解包，再 `shutil.move` 到用户选择的目录。

### 5. MAC/用户名/主机名冲突

**现象：** 两个相同身份的设备无法互相发现。

**根因：** FeiQ 用 `VERSION(MAC) + LOGINNAME + HOSTNAME` 唯一标识设备，相同则互斥。

**解决：** `setting.py` 中 `VERSION` 的 MAC 段必须与本机不同，且用户名和主机名也不能与网络中其他飞秋相同。

## v0.7 GUI（新）

```bat
python gui/main.py
```

QQ 风格聊天界面，位于 `gui/` 文件夹，引擎文件零修改。

### 文件结构

```
gui/
├── main.py              # 入口：高 DPI → UDP 服务 → 引擎 → 窗口
├── main_window.py       # 主窗口：组装 + 信号桥接 + 拖拽 + 托盘
├── contact_panel.py     # 左侧联系人面板（搜索 + 分组树）
├── chat_view.py         # 右侧聊天区（TIM 气泡 + 输入框 + 文件按钮）
├── models.py            # 数据模型：ContactItem, ChatMessage
├── resources.py         # 配色常量、QSS 样式表
├── settings_dialog.py   # 设置对话框（5 标签页）
└── SPEC.md              # 设计规格与实现状态
```

### 功能

- 文字消息 / 文件 / 文件夹 / 批量发送
- 文件接收弹窗（接收/另存为/拒绝）
- 拖拽文件到窗口发送
- 分组折叠联系人 + 搜索
- 系统托盘最小化
- 设置页：保存路径、昵称、防火墙解封、多网段、开机自启
- 高 DPI 适配

### 引擎变更（最小化）

仅加了一个 `progress_cb` 回调钩子，用于文件传输进度显示。

## 已知限制

- **接收文字消息** — 引擎 blowfish 解密偶尔报 `subsection not found`，加密文本偶尔收不到（旧 GUI 同样存在）
- 图片发送未实现（按钮已移除）
- 群聊未实现
- 文件传输进度条待实现（引擎钩子已就绪）
- 换机器需要修改 `setting.py` 中的 MAC/用户名/主机名

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v0.5 | 2026-06-02 | 文件收发基础功能 + 文件夹打包解包 |
| v0.6 | 2026-06-03 | 代码拆分 + 批量收发 + 文件夹接收 + 保存位置弹窗 + 5 个关键 bugfix |
| v0.6r2 | 2026-06-03 | 代码精简：去 QWebEngineView/头像/ui文件等，引擎零 Qt 依赖；编码 gb2312→gbk |
| v0.7 | 2026-06-03 | QQ 风格 PyQt5 GUI：TIM 气泡、分组联系人、拖拽、托盘、设置页、高 DPI |
