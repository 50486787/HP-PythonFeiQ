"""聊天记录 JSON 持久化 — 独立文件，与 UI 无关"""
import json
import os
from datetime import datetime

from gui.models import ChatMessage


def _default_dir():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chat_history')


def _msg_to_dict(msg: ChatMessage) -> dict:
    return {
        'peer_id': msg.peer_id,
        'text': msg.text,
        'is_send': msg.is_send,
        'time': msg.time.isoformat(),
        'msg_type': msg.msg_type,
        'file_name': msg.file_name,
        'file_size': msg.file_size,
        'transfer_done': msg.transfer_done,
    }


def _dict_to_msg(d: dict) -> ChatMessage:
    return ChatMessage(
        peer_id=d.get('peer_id', ''),
        text=d.get('text', ''),
        is_send=d.get('is_send', True),
        time=datetime.fromisoformat(d.get('time', datetime.now().isoformat())),
        msg_type=d.get('msg_type', 'text'),
        file_name=d.get('file_name', ''),
        file_size=d.get('file_size', 0),
        transfer_done=d.get('transfer_done', False),
    )


def save_messages(peer_id: str, messages: list, save_dir: str = None):
    """保存某个会话的全部消息到 JSON 文件"""
    directory = save_dir or _default_dir()
    os.makedirs(directory, exist_ok=True)
    safe_name = peer_id.replace(':', '_').replace('\\', '_').replace('/', '_')
    path = os.path.join(directory, f'{safe_name}.json')
    data = [_msg_to_dict(m) for m in messages]
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_messages(peer_id: str, save_dir: str = None) -> list:
    """从 JSON 文件加载会话消息"""
    directory = save_dir or _default_dir()
    safe_name = peer_id.replace(':', '_').replace('\\', '_').replace('/', '_')
    path = os.path.join(directory, f'{safe_name}.json')
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return [_dict_to_msg(d) for d in data if isinstance(d, dict)]
    except (json.JSONDecodeError, OSError):
        return []
