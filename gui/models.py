"""数据模型 — 纯 Python 数据类，无 Qt 依赖"""
from dataclasses import dataclass, field
from typing import List, Optional
import datetime


@dataclass
class ContactItem:
    """联系人条目"""
    user_id: str           # 引擎用户 ID
    nickname: str          # 昵称
    groupname: str         # 分组名
    ip: str = ''
    port: int = 0
    online: bool = True
    last_message: str = ''  # 最后一条消息预览
    last_time: Optional[datetime.datetime] = None
    avatar_path: str = ''   # 头像文件路径，空则用文字头像


@dataclass
class ChatMessage:
    """聊天消息"""
    peer_id: str           # 对端 ID
    text: str              # 消息文本
    is_send: bool          # True=自己发的, False=收到的
    time: datetime.datetime = field(default_factory=datetime.datetime.now)
    msg_type: str = 'text'  # 'text' | 'image' | 'file'
    file_path: str = ''     # 图片/文件本地路径（用于预览）
    file_name: str = ''     # 原始文件名
    file_size: int = 0      # 文件大小（字节）
