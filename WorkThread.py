from LogHelp import logger
import IPMSG
from feiqstruct import *
from TaskManager import *
from UserManager import FeiQUserManager
from SecurityManager import SecurtInstance
import setting
import time
import socket
import os
import shutil

#消息发送类
class MsgSender:
    packet:UdpPacketData = None
    cmd = 0

    def __init__(self):
        self.packet = UdpPacketData()

    def setData(self,me:User,ip,port):
        me.saveToPacket(self.packet)
        self.packet.ip = ip
        self.packet.port = port

    # 序列化数据
    def save(self):
        self.packet.cmd = self.cmd
        self.packet.extra = self.getExtra()

        self.packet.save()

    #子类必须实现
    def getExtra(self):
        pass

#命令发送，没有内容
class CommandSender(MsgSender):
    def __init__(self, cmd):
        MsgSender.__init__(self)
        self.cmd = cmd

    #纯命令的情况，不需要内容
    def getExtra(self):
        return b'\0'


# 命令发送,回应收到报文
class ResponseSender(MsgSender):
    def __init__(self, cmd, packetno):
        MsgSender.__init__(self)
        self.cmd = cmd
        self.packetno = packetno

    # 纯命令的情况，不需要内容
    def getExtra(self):
        return str(self.packetno).encode(IPMSG.ENCODETYPE) + b'\0'

# 发送分组数据
class GroupSender(MsgSender):
    def __init__(self, cmd):
        MsgSender.__init__(self)
        self.cmd = cmd

    # 需要内容
    def getExtra(self):
        return self.packet.nickname.encode(IPMSG.ENCODETYPE) + b'\0' + \
               self.packet.groupname.encode(IPMSG.ENCODETYPE) + b'\0'


class DevReplySender(MsgSender):
    def __init__(self, target_mac):
        MsgSender.__init__(self)
        self.cmd = IPMSG.IPMSG_D9_DEVREPLY
        self._mac = target_mac
    def getExtra(self):
        return self._mac.encode(IPMSG.ENCODETYPE) + b'\0'

#报文处理类
class RecvHandler:
    def __init__(self):
        pass

    def handle(self,msg:Message):
        pass

    # 这是把MainWorkThread的对象传递来，方便回调处理
    def setEngine(self, engine):
        self.engine = engine

    def sendSender(self, sender:MsgSender, ip, port):
        self.engine.putSendMessage(sender, ip, port)

    def updateUser(self, user):
        bAdd = self.engine.usermanager.UpdateUser(user)
        if bAdd: #如果是新增加，那么请求对方的昵称等信息
            sender = GroupSender(IPMSG.IPMSG_ANSENTRY | IPMSG.FEIQ_EXTEND_CMD)
            self.sendSender(sender, user.ip, user.port)


    def removeUser(self, user):
        self.engine.usermanager.RemoveUser(user)


class DebugHandler(RecvHandler):
    def handle(self,msg:Message):
        logger.debug("DebugHandler::%s--->%d--->%s"%(msg.friend.__str__(), msg.cmd, msg.extra.decode(IPMSG.ENCODETYPE)))
        return False

class FilterRecvHandler(RecvHandler):
    def handle(self,msg:Message):
        # 过滤自己的消息：比较主机名和登录名
        if msg.friend.hostname == self.engine.me.hostname and msg.friend.loginname == self.engine.me.loginname:
            return True
        return False

#好友响应我们的上线消息
class AnsEntryRecvHandler(RecvHandler):
    def handle(self,msg:Message):
        if IPMSG.IS_CMD_SET(msg.cmd, IPMSG.IPMSG_ANSENTRY):
            strExtra = msg.extra.decode(IPMSG.ENCODETYPE)
            arrData = strExtra.split('\0')
            if len(arrData) > 2:
                msg.friend.nickname = arrData[0]
                msg.friend.groupname = arrData[1]

            # 回应消息
            sender = CommandSender(IPMSG.IPMSG_OPEN_YOU)
            self.sendSender(sender, msg.friend.ip, msg.friend.port)

            self.updateUser(msg.friend)

            logger.debug('好友回应上线:' + msg.friend.__str__())
            return True

        return False

#飞秋的119协议，上线，回应120
class FeiQRecvAnsEntry(RecvHandler):
    def handle(self, msg: Message):
        if IPMSG.IS_CMD_SET(msg.cmd, IPMSG.IPMSG_OPEN_YOU):
            strExtra = msg.extra.decode(IPMSG.ENCODETYPE)
            arrData = strExtra.split('\0')
            if len(arrData) > 2:
                msg.friend.nickname = arrData[0]
                msg.friend.groupname = arrData[1]

            #回应消息
            sender = CommandSender(IPMSG.IPMSG_RESP_YOU)
            self.sendSender(sender, msg.friend.ip, msg.friend.port)
            self.updateUser(msg.friend)

            logger.debug('飞秋的119协议:' + msg.friend.__str__())
            return True

        return False

#收到用户发送的分组的数据，需要回应,6291457
class GroupRecvHandler(RecvHandler):
    def handle(self, msg: Message):
        if IPMSG.IS_CMD_SET(msg.cmd, IPMSG.IPMSG_BR_ENTRY) and \
                IPMSG.IS_OPT_SET(msg.cmd, IPMSG.FEIQ_EXTEND_CMD):
            strExtra = msg.extra.decode(IPMSG.ENCODETYPE)
            arrData = strExtra.split('\0')
            if len(arrData) >= 2:
                msg.friend.nickname = arrData[0]
                msg.friend.groupname = arrData[1]
            elif len(arrData) >= 1:
                msg.friend.nickname = arrData[0]

            #回应消息
            sender = GroupSender(IPMSG.IPMSG_ANSENTRY|IPMSG.FEIQ_EXTEND_CMD)
            self.sendSender(sender, msg.friend.ip, msg.friend.port)
            self.updateUser(msg.friend)
            logger.debug('飞秋的分组信息:%s'%(msg.friend,))
            return True

        return False
#收到用户分组的数据，不需要回应,6291459
class Group2RecvHandler(RecvHandler):
    def handle(self, msg: Message):
        if IPMSG.IS_CMD_SET(msg.cmd, IPMSG.IPMSG_ANSENTRY) and \
                IPMSG.IS_OPT_SET(msg.cmd, IPMSG.FEIQ_EXTEND_CMD):
            strExtra = msg.extra.decode(IPMSG.ENCODETYPE)
            arrData = strExtra.split('\0')
            if len(arrData) >= 2:
                msg.friend.nickname = arrData[0]
                msg.friend.groupname = arrData[1]
            elif len(arrData) >= 1:
                msg.friend.nickname = arrData[0]

            #回应消息
            #sender = GroupSender(IPMSG.IPMSG_ANSENTRY|IPMSG.FEIQ_EXTEND_CMD)
            #self.sendSender(sender, msg.friend.ip, msg.friend.port)
            #self.updateUser(msg.friend)
            logger.debug('飞秋的分组信息:%s'%(msg.friend,))
            return True

        return False
#好友上线
class BrEntryRecvHandler(RecvHandler):
    def handle(self, msg: Message):
        if IPMSG.IS_CMD_SET(msg.cmd, IPMSG.IPMSG_BR_ENTRY):
            strExtra = msg.extra.decode(IPMSG.ENCODETYPE)
            arrData = strExtra.split(' ')
            if len(arrData) > 2:
                msg.friend.nickname = arrData[0]
                msg.friend.groupname = arrData[1]

            # 回应消息
            sender = CommandSender(IPMSG.IPMSG_ANSENTRY)
            self.sendSender(sender, msg.friend.ip, msg.friend.port)
            self.updateUser(msg.friend)
            logger.debug('好友上线:' + msg.friend.__str__())
            return True

        return False

#好友下线
class BrExitRecvHandler(RecvHandler):
    def handle(self, msg: Message):
        if IPMSG.IS_CMD_SET(msg.cmd, IPMSG.IPMSG_BR_EXIT):

            self.removeUser(msg.friend)
            logger.debug('好友下线:' + msg.friend.__str__())
            return True

        return False

class DevQueryRecvHandler(RecvHandler):
    def handle(self, msg: Message):
        if (msg.cmd & 0xFF) != IPMSG.IPMSG_D8_DEVQUERY:
            return False
        if msg.extra.decode(IPMSG.ENCODETYPE).rstrip('\0') == '0':
            sender = DevReplySender(msg.friend.mac)
            self.sendSender(sender, msg.friend.ip, msg.friend.port)
            return True
        return False

class DevReplyRecvHandler(RecvHandler):
    def handle(self, msg: Message):
        if (msg.cmd & 0xFF) != IPMSG.IPMSG_D9_DEVREPLY:
            return False
        return True

#有时候用户直接发送消息，不会发上线通知，所以先把接收到的用户都放到用户处理里面
class PacketRecvHandler(RecvHandler):
    def handle(self,msg:Message):
        self.updateUser(msg.friend)
        return False

#IPMSG_SENDCHECKOPT
class CheckOptRecvHandler(RecvHandler):
    def handle(self, msg: Message):
        if IPMSG.IS_OPT_SET(msg.cmd, IPMSG.IPMSG_SENDCHECKOPT):
            # 回应消息
            sender = ResponseSender(IPMSG.IPMSG_RECVMSG, msg.packno)
            self.sendSender(sender, msg.friend.ip, msg.friend.port)
        return False

#IPMSG_RECVMSG,对方告知我方已经收到报文
class ReportPacketRecvHandler(RecvHandler):
    def handle(self,msg:Message):
        if IPMSG.IS_CMD_SET(msg.cmd, IPMSG.IPMSG_RECVMSG):
            packno = str(msg.extra.decode())
            self.engine.EraseReleateTask(packno)

        return False


#我方发送请求RSAKEY
class ReqRsaSender(MsgSender):
    def __init__(self):
        MsgSender.__init__(self)
        self.cmd = IPMSG.IPMSG_GETPUBKEY

    # 纯命令的情况，不需要内容
    def getExtra(self):
        return b'21003'

#我方发送RSAKEY
class RepRsaSender(MsgSender):
    def __init__(self):
        MsgSender.__init__(self)
        self.cmd = IPMSG.IPMSG_ANSPUBKEY

    # 纯命令的情况，不需要内容
    def getExtra(self):
        slice1 = b'21003:'
        key = SecurtInstance.getPubKey()
        slice2 = hex(key[0])[2:].encode(IPMSG.ENCODETYPE) #e
        slice3 = b'-'
        slice4 = hex(key[1])[2:].encode(IPMSG.ENCODETYPE)

        return slice1 + slice2 + slice3 + slice4

#对方请求RSA pubkey
class ReqRsaRecvHandler(RecvHandler):
    def handle(self, msg: Message):
        if IPMSG.IS_CMD_SET(msg.cmd, IPMSG.IPMSG_GETPUBKEY):
            strExtra = msg.extra.decode(IPMSG.ENCODETYPE)
            if strExtra.startswith('21003'):
                # 回应消息
                sender = RepRsaSender()
                self.sendSender(sender, msg.friend.ip, msg.friend.port)
            logger.debug('对方请求RSA PUBLIC KEY:' + msg.friend.__str__())
            return True

        return False

#对方发送RSA pubkey
class RepRsaRecvHandler(RecvHandler):
    def handle(self, msg: Message):
        if IPMSG.IS_CMD_SET(msg.cmd, IPMSG.IPMSG_ANSPUBKEY):
            strExtra = msg.extra.decode(IPMSG.ENCODETYPE)
            if strExtra.startswith('21003:'):
                strE,strN = strExtra[6:].split('-')
                intE = int(strE, 16)
                intN = int(strN, 16)
                SecurtInstance.addPubKey(msg.friend.getId(), intE, intN)

                #对方发送密钥后需要通知任务队里的任务,设置用户ID类任务全部执行
                self.engine.SetReleateTaskRun('PUBKEY_' + msg.friend.getId())

            logger.debug('对方发送RSA PUBLIC KEY:' + msg.friend.__str__())
            return True

        return False

#接收文本内容
class TextRecvHandler(RecvHandler):
    def handle(self, msg:Message):
        if not IPMSG.IS_CMD_SET(msg.cmd, IPMSG.IPMSG_SENDMSG):
            return False

        if IPMSG.IS_OPT_SET(msg.cmd, IPMSG.IPMSG_ENCRYPTOPT):
            return False

        strExtra = msg.extra.decode(IPMSG.ENCODETYPE)

        try:
            begin = strExtra.index('{')
            end = strExtra.index('}')
            text = strExtra[:begin]
            format = strExtra[begin+1: end]
        except ValueError:
            text = strExtra[:-1]
            format = ''

        content = TextContent(text, format, msg.friend.getId(), False)
        msg.contents.append(content)

        #测试代码
        #self.engine.appendContent(content)

        return False

#接收加密文本（同时检测文件附件）
class EncryptTextRecvHandler(RecvHandler):
    def handle(self, msg: Message):
        if not IPMSG.IS_CMD_SET(msg.cmd, IPMSG.IPMSG_SENDMSG):
            return False

        # 用字节级解析，避免 \0 在字段中间的问题
        raw_extra = msg.extra.rstrip(b'\0')
        if not raw_extra.startswith(b'20002:'):
            return False

        # 字节级 split: 找前2个冒号后的字段，其余保留
        colon1 = raw_extra.index(b':', 6)  # 跳过 "20002:"
        colon2 = raw_extra.index(b':', colon1 + 1)
        
        encrypted_key_hex = raw_extra[6:colon1].decode('ascii').replace('\x00', '')
        encrypted_data_hex = raw_extra[colon1+1:colon2].decode('ascii').replace('\x00', '')
        remaining = raw_extra[colon2+1:]  # 字节级保留文件名等

        arrSplit = remaining.decode(IPMSG.ENCODETYPE, errors='replace').rstrip('\0').split(':')

        logger.info('EncryptTextRecvHandler: key_hex=%dchars, data_hex=%dchars, remain=%d fields' % (
            len(encrypted_key_hex), len(encrypted_data_hex), len(arrSplit)))
        # 把 remaining 的 \x07 位置用 | 标出来
        sep_positions = [i for i, b in enumerate(remaining) if b == 0x07]
        logger.info('remaining hex dump: %s' % remaining.hex(' '))
        logger.info('remaining \\x07 at positions: %s (count=%d)' % (sep_positions, len(sep_positions)))
        logger.info('remaining repr (first 300 chars): %s' % repr(remaining[:300]))

        # 尝试解密
        try:
            if len(encrypted_data_hex) % 2 != 0:
                encrypted_data_hex = encrypted_data_hex[:-1]  # 截断多出的字符(一般是\0残留)
            logger.info('解密参数: key=%dchars, data=%dchars' % (len(encrypted_key_hex), len(encrypted_data_hex)))
            # 检查位置16的字符
            if len(encrypted_key_hex) > 16:
                ch = encrypted_key_hex[16]
                logger.info('key[16]=0x%02x(%s)' % (ord(ch), repr(ch)))
            key_bytes = bytes.fromhex(encrypted_key_hex)
            data_bytes = bytes.fromhex(encrypted_data_hex)
            logger.info('key_bytes=%d, data_bytes=%d' % (len(key_bytes), len(data_bytes)))
            decryptData = SecurtInstance.decrypt(key_bytes, data_bytes)
            strExtra = decryptData.decode(IPMSG.ENCODETYPE, errors='replace')
            logger.info('解密内容(%d字节): %s' % (len(decryptData), decryptData.hex()))
            # 保存解密令牌，用于 TCP 下载请求
            self._last_file_token = decryptData
        except Exception as e:
            logger.warning('解密失败(step=%s): %s' % (type(e).__name__, str(e)[:80]))
            strExtra = ''

        # 去尾部 \0
        strExtra = strExtra.rstrip('\0')

        # 分离文本和文件信息：文本\0文件信息
        text = strExtra
        file_part = ''
        try:
            null_pos = strExtra.index('\0')
            text = strExtra[:null_pos]
            file_part = strExtra[null_pos+1:]
        except ValueError:
            pass

        # token 数据不含 ':' 就不是文件路径
        if file_part and ':' not in file_part:
            file_part = ''

        # 如果加密体内没有文件信息，检查加密体外（明文附件）
        # FeiQ 格式: filename:size_hex:timestamp:type:\x07seq
        # \x07 是 seq 字段的前缀（FILELIST_SEPARATOR），不是文件分隔符
        # 每组 5 个 : 分隔字段，轮询所有文件
        if not file_part and len(arrSplit) >= 4:
            i = 0
            while i + 4 < len(arrSplit):
                filename = arrSplit[i]
                size_hex = arrSplit[i+1] if i+1 < len(arrSplit) else ''
                type_str = arrSplit[i+3] if i+3 < len(arrSplit) else '1'
                seq_field = arrSplit[i+4] if i+4 < len(arrSplit) else '0'

                if not filename or not size_hex:
                    i += 1
                    continue
                if filename.isdigit() and len(filename) < 5:
                    i += 1
                    continue

                # seq 字段带 \x07 前缀: '\x071' → 1
                # 最后一个文件的 seq 可能只有 \x07 没有数字，fallback 到位置序号
                seq_str = seq_field.replace('\x07', '')
                try:
                    file_size = int(size_hex, 16)
                    file_type = int(type_str) if type_str else 1
                    if seq_str.isdigit():
                        file_id = int(seq_str)
                    elif '\x07' in seq_field:
                        file_id = i // 5 + 1  # \x07 但无数值 → 用位置(1-based)
                    else:
                        file_id = 0  # 无 \x07 → 单文件
                except (ValueError, TypeError):
                    i += 5
                    continue

                logger.info('检测到加密信封外的文件: %s (%d字节) type=%d id=%d' % (filename, file_size, file_type, file_id))
                content = FileContent(file_id, filename, file_size, msg.friend.getId(), False)
                msg.contents.append(content)
                # 收集批量文件，稍后串行下载（飞秋不支持同一 packno 并发）
                if not hasattr(self, '_batch_queue'):
                    self._batch_queue = []
                self._batch_queue.append((msg.friend.ip, msg.packno, file_id, filename, file_size, file_type))
                i += 5  # 每组 5 字段: name, size, ts, type, \x07seq

            # 批量文件：串行下载，一次弹窗确认全部
            if hasattr(self, '_batch_queue') and self._batch_queue:
                queue = self._batch_queue
                self._batch_queue = []
                self.engine.download_batch(queue)

        # 检测加密体内的文件附件: file_id:filename:size_hex:timestamp:file_type:
        if file_part and len(file_part) > 0:
            # 去掉可能的前导 ':'
            if file_part.startswith(':'):
                file_part = file_part[1:]
            parts = file_part.split(':')
            if len(parts) >= 3:
                try:
                    file_id = int(parts[0])
                    filename = parts[1]
                    file_size = int(parts[2], 16) if parts[2] else 0
                    file_type = int(parts[4]) if len(parts) > 4 and parts[4] else 1  # parts[4]=file_type
                    content = FileContent(file_id, filename, file_size, msg.friend.getId(), False)
                    msg.contents.append(content)
                    # 自动下载
                    self.engine.download_file(msg.friend.ip, msg.packno, file_id, filename, file_size, file_type)
                    if not text:
                        return False  # 纯文件消息，处理完毕
                except (ValueError, IndexError):
                    pass

        # 文本格式检测
        if text:
            try:
                begin = text.rindex('{')
                end = text.rindex('}')
                text_body = text[:begin]
                format = text[begin + 1 : end]
            except ValueError:
                text_body = text
                format = ''

            if text_body:
                content = TextContent(text_body, format, msg.friend.getId(), False)
                msg.contents.append(content)

        return False

#发送文本内容
class TextSender(MsgSender):
    def __init__(self, content):
        self.content:TextContent = content
        MsgSender.__init__(self)
        self.cmd = IPMSG.IPMSG_SENDMSG | IPMSG.IPMSG_SENDCHECKOPT

    def getExtra(self):
        rawData = self.content.text
        if len(self.content.format) > 0:
            rawData += '{' + self.content.format + '}'

        rawData += '\0'

        return rawData.encode(IPMSG.ENCODETYPE)

#发送加密文本
class EncryptTxtSender(MsgSender):
    def __init__(self, content):
        self.content:TextContent = content
        MsgSender.__init__(self)
        self.cmd = IPMSG.IPMSG_SENDMSG | IPMSG.IPMSG_SENDCHECKOPT | IPMSG.IPMSG_ENCRYPTOPT

    def getExtra(self):
        rawData = self.content.text
        if len(self.content.format) > 0:
            rawData += '{' + self.content.format + '}'
        rawData += '\0'

        enKey, enMsg = SecurtInstance.encrypt(self.content.peer, rawData.encode(IPMSG.ENCODETYPE))

        resultData = '20002:'+enKey.hex() + ':' + enMsg.hex() + '\0'

        return resultData.encode(IPMSG.ENCODETYPE)


#接收文件附件信息
class FileAttachmentRecvHandler(RecvHandler):
    def handle(self, msg: Message):
        if not IPMSG.IS_CMD_SET(msg.cmd, IPMSG.IPMSG_SENDMSG):
            return False
        if not IPMSG.IS_OPT_SET(msg.cmd, IPMSG.IPMSG_FILEATTACHOPT):
            return False

        # 加密数据先解密
        extra_data = msg.extra
        if IPMSG.IS_OPT_SET(msg.cmd, IPMSG.IPMSG_ENCRYPTOPT):
            encryptData = msg.extra.decode(IPMSG.ENCODETYPE)
            try:
                found = encryptData.index('\0')
                encryptData = encryptData[:found]
            except:
                pass
            arrSplit = encryptData.split(':')
            if len(arrSplit) >= 3 and arrSplit[0] == "20002":
                decryptData = SecurtInstance.decrypt(bytes.fromhex(arrSplit[1]), bytes.fromhex(arrSplit[2]))
                extra_data = decryptData
            else:
                return False

        # 解析文件信息: \0file_id:filename:size_hex:timestamp:file_type:
        strExtra = extra_data.decode(IPMSG.ENCODETYPE, errors='ignore')
        # 跳过开头的文本部分（如果有的话）
        null_pos = strExtra.find('\0')
        if null_pos >= 0:
            file_info = strExtra[null_pos+1:]
        else:
            # 尝试直接解析（可能是纯文件消息）
            file_info = strExtra

        if not file_info or file_info.startswith('\0'):
            return False

        parts = file_info.rstrip('\0').split(':')
        if len(parts) < 3:
            return False

        try:
            file_id = int(parts[0])
            filename = parts[1]
            file_size = int(parts[2], 16) if parts[2] else 0
            file_type = int(parts[4]) if len(parts) > 4 and parts[4] else 1  # parts[4]=file_type
        except (ValueError, IndexError):
            return False

        content = FileContent(file_id, filename, file_size, msg.friend.getId(), False)
        msg.contents.append(content)

        # 自动下载文件
        self.engine.download_file(msg.friend.ip, msg.packno, file_id, filename, file_size, file_type)

        return False

#内容接收结束处理器
class EndRecvHandler(RecvHandler):
    def handle(self, msg:Message):
        for item in msg.contents:
            logger.debug('内容接收结束处理器---->%s'% item)
            self.engine.onRecvContent(item)

#此类主要处理数据，不负责收发消息
class MainWorkThread(TaskManager):
    me:User = User()

    __recvHandler = [

    ]

    def __init__(self):
        self.me.version = setting.VERSION
        self.me.hostname = setting.HOSTNAME
        self.me.loginname = setting.LOGINNAME
        self.me.nickname = setting.NICKNAME
        self.me.groupname = setting.GROUPNAME

        TaskManager.__init__(self, 5, 50)

        self.initRecvHandler()

        self.sendFunc=None
        self._online_peers = set()
        self.file_recv_cb = None  # callback(filename, filesize, filetype) -> (save_path, accepted)
        self.progress_cb = None   # callback(filename, bytes_done, total_bytes)

    #设置内容结束回调函数
    #def setRecvContentCB(self, contentRecvHandler):
    #    self.contentRecvHandler = contentRecvHandler

    #初始化接收处理器
    def initRecvHandler(self):
        #过滤器放最前面
        self.__recvHandler.append(FilterRecvHandler())

        self.__recvHandler.append(DebugHandler())

        self.__recvHandler.append(PacketRecvHandler()) #只有收到对方的报文，就把对方加为好友

        self.__recvHandler.append(ReportPacketRecvHandler()) #对方告知已经收到报文

        self.__recvHandler.append(DevQueryRecvHandler())
        self.__recvHandler.append(DevReplyRecvHandler())

        self.__recvHandler.append(CheckOptRecvHandler())

        self.__recvHandler.append(GroupRecvHandler())
        self.__recvHandler.append(Group2RecvHandler())

        self.__recvHandler.append(AnsEntryRecvHandler())

        self.__recvHandler.append(FeiQRecvAnsEntry())

        self.__recvHandler.append(BrEntryRecvHandler())

        self.__recvHandler.append(BrExitRecvHandler())

        self.__recvHandler.append(ReqRsaRecvHandler())

        self.__recvHandler.append(RepRsaRecvHandler())

        self.__recvHandler.append(EncryptTextRecvHandler())

        self.__recvHandler.append(FileAttachmentRecvHandler())

        self.__recvHandler.append(TextRecvHandler())

        self.__recvHandler.append(EndRecvHandler())

        for handle in self.__recvHandler:
            handle.setEngine(self)

    def onLogin(self):
        for ip, port in setting.INITADDRESS:
            entry = CommandSender(IPMSG.IPMSG_BR_ENTRY | IPMSG.IPMSG_BROADCASTOPT)
            self.putSendMessage(entry, ip, port)

            group = GroupSender(IPMSG.IPMSG_BR_ENTRY | IPMSG.FEIQ_EXTEND_CMD | IPMSG.IPMSG_BROADCASTOPT)
            self.putSendMessage(group, ip, port)
    #启动
    def start(self,sendfunc, onViewCallback):
        self.sendFunc=sendfunc
        self.usermanager = FeiQUserManager(self.appendContent)
        self.usermanager.setViewEvent(onViewCallback)

        # 启动 TCP 文件服务器
        self._pending_files = {}  # file_id -> {filepath, filename, filesize, filectime}
        self._startTcpServer()

        self.onLogin()  # 登录上线

    def _startTcpServer(self):
        """启动 TCP 文件服务器，监听 2425 端口"""
        import threading
        def tcp_loop():
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(('0.0.0.0', setting.PORT))
                sock.listen(5)
                logger.info('TCP文件服务器启动，端口 %d' % setting.PORT)
                while True:
                    conn, addr = sock.accept()
                    logger.info('TCP accept: %s:%d' % (addr[0], addr[1]))
                    threading.Thread(target=self._handleTcpRequest, args=(conn, addr), daemon=True).start()
            except Exception as e:
                logger.error('TCP服务器启动失败(端口%d被占用? 试试 taskkill /f /im FeiQ.exe): %s' % (setting.PORT, str(e)))

        threading.Thread(target=tcp_loop, daemon=True, name='TCP文件服务器').start()

    def _parse_packed_dir_listing(self, filepath):
        """从飞秋打包文件中提取目录列表（原始 hlen:meta 格式，不含文件内容）

        返回 (raw_meta_bytes, parsed_entries)
          raw_meta_bytes: hlen:meta 序列(供 GETDIRFILES 直接发送)
          parsed_entries: [{name, size, etype, data_offset}, ...] 用于 GETFILEDATA 定位
        """
        if not os.path.exists(filepath):
            return None, None
        with open(filepath, 'rb') as f:
            data = f.read()

        HEADER_LEN = 0xC00 + 4
        if len(data) < HEADER_LEN + 5:
            return None, None

        raw_parts = []
        parsed = []
        pos = HEADER_LEN
        data_len = len(data)
        META_END = b':0=16:'
        META_END_LEN = len(META_END)
        first_entry = True

        while pos + 5 <= data_len:
            hlen_bytes = data[pos:pos+5]
            if hlen_bytes[4:5] != b':':
                break
            try:
                hlen = int(hlen_bytes[:4].decode('ascii'), 16)
            except ValueError:
                break
            pos += 5

            if pos + hlen > data_len:
                break

            meta_area = data[pos:pos+hlen]
            marker_pos = meta_area.find(META_END)
            if marker_pos >= 0:
                actual_meta_len = marker_pos + META_END_LEN
                meta = meta_area[:actual_meta_len]
            else:
                meta = meta_area
                actual_meta_len = len(meta_area)

            raw_entry = hlen_bytes + meta
            pos += actual_meta_len

            try:
                meta_text = meta.decode(IPMSG.ENCODETYPE)
            except:
                continue

            meta_parts = meta_text.rsplit(':0=16:')
            if len(meta_parts) < 1:
                continue
            front = meta_parts[0]
            front_parts = front.rsplit(':14=')
            if len(front_parts) < 2:
                continue
            name_size_type = front_parts[0]
            mtime_str = front_parts[1]

            type_split = name_size_type.rsplit(':', 2)
            if len(type_split) < 3:
                continue
            name = type_split[0]
            size_str = type_split[1]
            entry_type = type_split[2]

            try:
                size = int(size_str, 16)
                mtime = int(mtime_str, 16)
                etype = int(entry_type)
            except ValueError:
                continue

            if etype == 3:
                continue
            if etype == 2 and first_entry:
                first_entry = False
                continue
            first_entry = False

            if etype == 2:
                size = 0

            data_offset = pos
            raw_parts.append(raw_entry)
            parsed.append({
                'name': name,
                'size': size,
                'etype': etype,
                'data_offset': data_offset,
            })

            if etype == 1 and pos + size <= data_len:
                pos += size

        if raw_parts:
            return b''.join(raw_parts), parsed
        return None, None

    def _handleTcpRequest(self, conn, addr):
        """处理 TCP 文件下载请求 — 区分 GETDIRFILES(98) 和 GETFILEDATA(96)"""
        logger.info('TCP连接接入: %s:%d' % (addr[0], addr[1]))
        finfo = None
        try:
            conn.settimeout(5)
            # 读取 IPMSG 格式请求
            data = b''
            while True:
                try:
                    chunk = conn.recv(4096)
                except socket.timeout:
                    logger.warning('TCP recv timeout from %s, received so far: %d bytes: %s' % (
                        addr[0], len(data), repr(data[:200])))
                    break
                if not chunk:
                    logger.info('TCP recv EOF from %s (peer closed), total=%d' % (addr[0], len(data)))
                    break
                data += chunk
                logger.info('TCP recv chunk %d bytes from %s, total=%d, ends_with_colon=%s, has_null=%s' % (
                    len(chunk), addr[0], len(data), data.endswith(b':'), b'\0' in data))
                # 真飞秋请求以 : 结尾(不以\0), 收到足够字段就停止
                if data.endswith(b':') or b'\0' in data:
                    break

            if not data:
                logger.warning('TCP no data from %s, closing' % addr[0])
                conn.close()
                return

            logger.info('TCP request raw (%d bytes): %s' % (len(data), repr(data[:300])))

            # 解析请求（feiq 格式）:
            # version:packet(dec):name:host:cmd:packet(hex):fileid(hex):offset(hex):
            request_text = data.decode(IPMSG.ENCODETYPE, errors='replace').rstrip('\0')
            parts = request_text.split(':')
            if len(parts) >= 8:
                cmd = int(parts[4])
                pkt_hex = parts[5]
                fid_hex = parts[6]
                try:
                    req_packet = int(pkt_hex, 16)
                    req_fileid = int(fid_hex, 16)
                except:
                    req_packet = req_fileid = 0

                if cmd == IPMSG.IPMSG_GETFILEDATA or cmd == 0x62:  # 96 or 98
                    logger.info('TCP文件请求: cmd=%d packet=%d file_id=%d from %s' % (
                        cmd, req_packet, req_fileid, addr[0]))

                    # 解析offset参数(如果有)
                    req_offset = 0
                    if len(parts) >= 8:
                        try:
                            req_offset = int(parts[7], 16) if parts[7] else 0
                        except:
                            req_offset = 0

                    # 匹配文件: 先精确packet, 再file_id, 最后fallback到任意pending
                    if req_packet in self._pending_files:
                        finfo = self._pending_files[req_packet]
                    elif req_fileid in self._pending_files:
                        finfo = self._pending_files[req_fileid]
                    elif self._pending_files:
                        closest = min(self._pending_files.keys(), key=lambda k: abs(k - req_packet))
                        logger.info('packet不匹配(%d vs %d), fallback使用pending[%d]' % (
                            req_packet, closest, closest))
                        finfo = self._pending_files[closest]

                    if finfo:
                        filepath = finfo['filepath']
                        file_type = finfo.get('file_type', 1)

                        if cmd == 0x62 and file_type >= 2:
                            # GETDIRFILES: 发送条目数据(跳过0xC04魔数头), 大小与通知一致
                            fsize = os.path.getsize(filepath) if os.path.exists(filepath) else -1
                            HEADER_LEN = 0xC00 + 4
                            logger.info('GETDIRFILES: 流式发送条目数据 %s (%d字节, 去头%d)' % (filepath, fsize, HEADER_LEN))
                            if os.path.exists(filepath):
                                try:
                                    CHUNK = 65536
                                    sent = 0
                                    with open(filepath, 'rb') as f:
                                        f.seek(HEADER_LEN)  # 跳过0xC04头部
                                        while True:
                                            chunk = f.read(CHUNK)
                                            if not chunk:
                                                break
                                            conn.sendall(chunk)
                                            sent += len(chunk)
                                    logger.info('GETDIRFILES发送完成: %d字节 -> %s' % (sent, addr[0]))
                                except Exception as se:
                                    logger.error('发送条目数据失败: %s' % str(se))
                                    raise
                            else:
                                logger.warning('打包文件不存在: %s' % filepath)
                        else:
                            # === GETFILEDATA: 返回文件数据 ===
                            filesize = os.path.getsize(filepath) if os.path.exists(filepath) else -1
                            logger.info('GETFILEDATA: 流式发送 %s (%d字节) offset=%d' % (
                                filepath, filesize, req_offset))
                            conn.settimeout(120)
                            try:
                                CHUNK = 65536
                                total_sent = 0
                                with open(filepath, 'rb') as f:
                                    if req_offset > 0:
                                        f.seek(req_offset)
                                    while True:
                                        chunk = f.read(CHUNK)
                                        if not chunk:
                                            break
                                        conn.sendall(chunk)
                                        total_sent += len(chunk)
                                        if self.progress_cb:
                                            try: self.progress_cb(finfo['filename'], total_sent, filesize)
                                            except: pass
                                logger.info('文件发送完成: %s -> %s (%d字节)' % (
                                    finfo['filename'], addr[0], total_sent))
                            except Exception as se:
                                logger.error('sendall失败(总%d字节): %s' % (len(file_data), str(se)))
                                raise
                            # 单文件(type=1)请求一次即可清理
                            if file_type == 1:
                                to_remove = [k for k, v in self._pending_files.items() if v is finfo]
                                for k in to_remove:
                                    del self._pending_files[k]
                    else:
                        logger.warning('未找到文件 packet=%d file_id=%d (pending keys: %s)' % (
                            req_packet, req_fileid, list(self._pending_files.keys())[:10]))
        except Exception as e:
            import traceback
            logger.error('TCP请求处理失败: %s\n%s' % (str(e), traceback.format_exc()))
        finally:
            conn.close()

    def _handle_more_requests(self, conn, addr, finfo):
        """GETDIRFILES之后继续处理同一连接上的GETFILEDATA请求"""
        filepath = finfo.get('filepath', '')
        parsed_list = finfo.get('_parsed', [])
        logger.info('_handle_more_requests: 文件=%s, 条目数=%d' % (filepath, len(parsed_list)))
        while True:
            try:
                conn.settimeout(30)
                data = b''
                while True:
                    try:
                        chunk = conn.recv(4096)
                    except socket.timeout:
                        logger.info('等待后续请求超时, 关闭连接')
                        conn.close()
                        return
                    if not chunk:
                        logger.info('客户端关闭连接')
                        conn.close()
                        return
                    data += chunk
                    if data.endswith(b':') or b'\0' in data:
                        break

                logger.info('后续请求: %s' % data.decode(IPMSG.ENCODETYPE, errors='replace')[:300])
                request_text = data.decode(IPMSG.ENCODETYPE, errors='replace').rstrip('\0')
                parts = request_text.split(':')
                if len(parts) >= 8:
                    cmd = int(parts[4])
                    if cmd == IPMSG.IPMSG_GETFILEDATA:
                        fid_hex = parts[6]
                        offset_str = parts[7] if len(parts) > 7 else '0'
                        try:
                            req_fileid = int(fid_hex, 16)
                            req_offset = int(offset_str, 16) if offset_str else 0
                        except:
                            req_fileid = req_offset = 0
                        logger.info('GETFILEDATA: file_id=%d(0x%x) offset=%d(0x%x)' % (
                            req_fileid, req_fileid, req_offset, req_offset))

                        seek_pos = 0
                        if parsed_list and req_fileid < len(parsed_list):
                            entry = parsed_list[req_fileid]
                            seek_pos = entry['data_offset']
                            logger.info('索引 %d -> %s offset=0x%x' % (req_fileid, entry['name'], seek_pos))
                        elif req_fileid > 0:
                            seek_pos = req_fileid
                        elif req_offset > 0:
                            seek_pos = req_offset

                        if os.path.exists(filepath):
                            with open(filepath, 'rb') as f:
                                if seek_pos > 0:
                                    logger.info('seek到 0x%x (%d)' % (seek_pos, seek_pos))
                                    f.seek(seek_pos)
                                file_data = f.read()
                            logger.info('发送 %d 字节' % len(file_data))
                            conn.sendall(file_data)
                            logger.info('文件数据发送完成: %d字节' % len(file_data))
                        else:
                            logger.error('打包文件不存在: %s' % filepath)
                    else:
                        logger.info('未知后续命令: %d, 忽略' % cmd)
                else:
                    logger.info('无法解析后续请求')
                conn.close()
                return
            except Exception as e:
                logger.error('处理后续请求失败: %s' % str(e))
                conn.close()
                return

    #停止
    def stopAll(self):
        TaskManager.Stop(self)

    #把接收到的数据包放进去
    def onRecvContent(self,content):
        self.usermanager.AddContent(content)

    #由UDPserver负责把数据放入
    def putRecvMessage(self,packet:UdpPacketData):
        self.CreateImmediatelyTask(self.__func_recv(packet), '接收报文处理')

    #发送数据,属于直接发送，特殊处理不能使用这个函数
    def putSendMessage(self,sender:MsgSender, ip, port, iDelayMillsecond = 0, taskname='',taskkey=''):
        sender.setData(self.me, ip, port)
        self.CreateDelayTask(self.__func_send(sender), iDelayMillsecond, taskname, taskkey)

    def _ensure_online(self, peer_id, addr):
        if peer_id not in self._online_peers:
            self._online_peers.add(peer_id)
            cmd = IPMSG.IPMSG_BR_ENTRY | IPMSG.FEIQ_EXTEND_CMD | IPMSG.IPMSG_BROADCASTOPT
            self.putSendMessage(GroupSender(cmd), addr[0], addr[1],
                               taskname='上线握手', taskkey='ONLINE_'+peer_id)

    #发送数据报文
    def appendContent(self, content:PacketContent):
        if content.type == ContentType.TEXT:
            # 先使用加密发送
            self.sendTextContent(content, True)
        elif content.type == ContentType.KNOCK:
            self.sendTextContent()

    #发送超时消息
    def onPacketTimeout(self, content):
        logger.error('发送报文超时---->%s'%content)

    #发送文本内容
    def sendTextContent(self, content:PacketContent, useEncrypt = True):
        addr = self.usermanager.getAddr(content.peer)
        if addr is None:
            logger.error('发送任务失败，无法获取需要发送的地址:%s'%content.peer)
            return
        self._ensure_online(content.peer, addr)
        if useEncrypt:
            sender = EncryptTxtSender(content)
        else:
            sender = TextSender(content)

        sender.setData(self.me, addr[0], addr[1])

        # 超时后发送消息
        def sendTimeout():
            self.onPacketTimeout(content)

        #发送数据
        def send():
            #批量发送文本
            self.BatchCreateDelayTask(self.__func_send(sender), str(sender.packet.packno), '批量发送文本', 0, 1000, 4)

            #准备到期超时消息,5000ms后超时
            self.CreateDelayTask(sendTimeout, 5000, '消息超时', str(sender.packet.packno))


        if not useEncrypt or SecurtInstance.hsaKey(content.peer):
            send()
        else:
            rsaSender = ReqRsaSender()
            rsaSender.setData(self.me, addr[0], addr[1])
            self.CreateImmediatelyTask(self.__func_send(rsaSender), "请求RAS PUBKEY", 'PUBKEY_' + content.peer)

            self.CreateSwitchTask(send, sendTimeout, 'PUBKEY_' + content.peer, 5000, '请求密钥后发送消息任务')
    #发送弹窗
    def sendKnock(self):
        pass

    # TCP下载文件
    def download_file(self, ip, packno, file_id, filename, file_size, file_type=1):
        """从对方 TCP 下载文件"""
        import os
        download_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
        os.makedirs(download_dir, exist_ok=True)
        default_path = os.path.join(download_dir, filename)

        # 弹窗询问用户
        custom_path = None
        if self.file_recv_cb:
            try:
                custom_path, accepted = self.file_recv_cb(filename, file_size, file_type)
                if not accepted:
                    logger.info('用户拒绝接收: %s' % filename)
                    return
            except Exception as e:
                logger.error('文件接收回调失败: %s' % str(e))

        save_path = custom_path if custom_path else default_path

        def do_download():
            try:
                # 确保父目录存在
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(30)
                sock.connect((ip, setting.PORT))

                # 文件类型: 1=普通文件(96), 2=文件夹(98)
                cmd = IPMSG.IPMSG_GETDIRFILES if file_type >= 2 else IPMSG.IPMSG_GETFILEDATA
                request = '%s:%d:%s:%s:%d:%x:%x:%x:\0' % (
                    setting.VERSION, packno, setting.LOGINNAME, setting.HOSTNAME,
                    cmd, packno, file_id, 0
                )
                logger.info('TCP下载: cmd=%d' % cmd)
                sock.sendall(request.encode(IPMSG.ENCODETYPE))
                logger.info('TCP下载请求(飞秋格式): %s' % request[:80])

                # 关掉接收超时，大文件慢慢收
                sock.settimeout(60)
                received = 0
                with open(save_path, 'wb') as f:
                    if file_type >= 2:
                        # 文件夹：读到连接关闭，不信通知的 file_size
                        while True:
                            chunk = sock.recv(8192)
                            if not chunk: break
                            f.write(chunk)
                            received += len(chunk)
                            if self.progress_cb:
                                try: self.progress_cb(filename, received, file_size)
                                except: pass
                    else:
                        while received < file_size:
                            chunk = sock.recv(min(8192, file_size - received))
                            if not chunk: break
                            f.write(chunk)
                            received += len(chunk)
                            if self.progress_cb:
                                try: self.progress_cb(filename, received, file_size)
                                except: pass
                sock.close()
                if file_type < 2 and received < file_size:
                    logger.error('文件下载不完整: %s (%d/%d字节)' % (filename, received, file_size))
                else:
                    logger.info('文件下载完成: %s -> %s (%d/%d字节)' % (filename, save_path, received, file_size))
                if file_type >= 2 and received > 0:
                    try:
                        unpacked = save_path + '_unpack'
                        _unpack_feiq_dir(save_path, unpacked)
                        # 如果解包后只有一个子目录，展平一层
                        items = os.listdir(unpacked)
                        if len(items) == 1:
                            inner = os.path.join(unpacked, items[0])
                            if os.path.isdir(inner):
                                os.rename(inner, unpacked + '_flat')
                                os.rmdir(unpacked)
                                os.rename(unpacked + '_flat', unpacked)
                        try:
                            os.remove(save_path)
                            final = save_path
                            if os.path.exists(final):
                                shutil.rmtree(final)
                            os.rename(unpacked, final)
                            logger.info('文件夹解包完成: %s' % final)
                        except Exception:
                            logger.info('文件夹解包完成: %s' % unpacked)
                    except Exception as e:
                        logger.error('解包失败: %s' % str(e))
            except Exception as e:
                logger.error('文件下载失败 %s: %s' % (filename, str(e)))

        threading.Thread(target=do_download, daemon=True, name='下载-' + filename).start()

    # 批量文件串行下载（飞秋不支持同一 packno 并发 TCP）
    def download_batch(self, queue):
        """批量下载: 弹一次窗确认全部, 然后串行下载"""
        if not queue:
            return

        # 叫回调一次搞定全部
        if self.file_recv_cb:
            import os
            # 构造批量描述
            names = [q[3] for q in queue]
            total_sz = sum(q[4] for q in queue)
            desc = '%d 个文件 (%s...)' % (len(queue), ', '.join(names[:3]))
            try:
                custom_dir, accepted = self.file_recv_cb(desc, total_sz, -1)  # type=-1 = batch
                if not accepted:
                    logger.info('用户拒绝接收批量文件 (%d个)' % len(queue))
                    return
            except Exception as e:
                logger.error('批量文件回调失败: %s' % str(e))
                custom_dir = None
        else:
            custom_dir = None

        # 串行下载（临时屏蔽回调，避免每个文件再弹窗）
        import threading, time
        saved_cb = self.file_recv_cb
        def do_all():
            self.file_recv_cb = None
            try:
                for idx, (ip, packno, file_id, filename, file_size, file_type) in enumerate(queue):
                    if idx > 0:
                        time.sleep(0.5)
                    if custom_dir:
                        if file_type < 2:
                            self._download_one_to(os.path.join(custom_dir, filename),
                                                 ip, packno, idx, filename, file_size, file_type)
                        else:
                            # 文件夹：先下载到默认位置，再移动到用户选择的目录
                            self._download_one(ip, packno, idx, filename, file_size, file_type)
                            default_src = os.path.join(
                                os.path.dirname(os.path.abspath(__file__)), 'downloads', filename)
                            custom_dst = os.path.join(custom_dir, filename)
                            if os.path.exists(default_src):
                                if os.path.exists(custom_dst):
                                    shutil.rmtree(custom_dst)
                                shutil.move(default_src, custom_dst)
                                logger.info('文件夹已移动到: %s' % custom_dst)
                    else:
                        self._download_one(ip, packno, idx, filename, file_size, file_type)
            finally:
                self.file_recv_cb = saved_cb

        threading.Thread(target=do_all, daemon=True, name='批量下载(%d文件)' % len(queue)).start()

    def _download_sequential(self, queue):
        """queue: list of (ip, packno, file_id, filename, file_size, file_type)"""
        self.download_batch(queue)

    def _download_one_to(self, save_path, ip, packno, file_id, filename, file_size, file_type=1):
        """下载到指定路径"""
        import os, socket
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(30)
            sock.connect((ip, setting.PORT))
            cmd = IPMSG.IPMSG_GETDIRFILES if file_type >= 2 else IPMSG.IPMSG_GETFILEDATA
            request = '%s:%d:%s:%s:%d:%x:%x:%x:\0' % (
                setting.VERSION, packno, setting.LOGINNAME, setting.HOSTNAME,
                cmd, packno, file_id, 0
            )
            sock.sendall(request.encode(IPMSG.ENCODETYPE))
            sock.settimeout(60)
            received = 0
            with open(save_path, 'wb') as f:
                if file_type >= 2:
                    while True:
                        chunk = sock.recv(8192)
                        if not chunk: break
                        f.write(chunk)
                        received += len(chunk)
                else:
                    while received < file_size:
                        chunk = sock.recv(min(8192, file_size - received))
                        if not chunk: break
                        f.write(chunk)
                        received += len(chunk)
            sock.close()
            logger.info('文件下载完成: %s -> %s (%d字节)' % (filename, save_path, received))
        except Exception as e:
            logger.error('文件下载失败 %s: %s' % (filename, str(e)))

    def _download_one(self, ip, packno, file_id, filename, file_size, file_type=1):
        """同步下载单个文件，阻塞到完成"""
        import os, socket
        download_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
        os.makedirs(download_dir, exist_ok=True)
        default_path = os.path.join(download_dir, filename)

        # 弹窗询问用户
        custom_path = None
        if self.file_recv_cb:
            try:
                custom_path, accepted = self.file_recv_cb(filename, file_size, file_type)
                if not accepted:
                    logger.info('用户拒绝接收: %s' % filename)
                    return
            except Exception as e:
                logger.error('文件接收回调失败: %s' % str(e))

        save_path = custom_path if custom_path else default_path
        try:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(30)
            sock.connect((ip, setting.PORT))
            cmd = IPMSG.IPMSG_GETDIRFILES if file_type >= 2 else IPMSG.IPMSG_GETFILEDATA
            request = '%s:%d:%s:%s:%d:%x:%x:%x:\0' % (
                setting.VERSION, packno, setting.LOGINNAME, setting.HOSTNAME,
                cmd, packno, file_id, 0
            )
            sock.sendall(request.encode(IPMSG.ENCODETYPE))
            sock.settimeout(60)
            received = 0
            with open(save_path, 'wb') as f:
                if file_type >= 2:
                    # 文件夹(2)或大文件夹(102)：先按通知大小读，再补读尾部
                    while received < file_size:
                        chunk = sock.recv(min(8192, file_size - received))
                        if not chunk: break
                        f.write(chunk)
                        received += len(chunk)
                    # 读完通知大小后，短超时补读尾部
                    sock.settimeout(5)
                    try:
                        while True:
                            chunk = sock.recv(8192)
                            if not chunk: break
                            f.write(chunk)
                            received += len(chunk)
                    except socket.timeout:
                        pass  # 5 秒没数据，结束
                else:
                    while received < file_size:
                        chunk = sock.recv(min(8192, file_size - received))
                        if not chunk: break
                        f.write(chunk)
                        received += len(chunk)
            sock.close()
            if file_type < 2 and received < file_size:
                logger.error('文件下载不完整: %s (%d/%d字节)' % (filename, received, file_size))
            else:
                logger.info('文件下载完成: %s -> %s (%d/%d字节)' % (filename, save_path, received, file_size))
            if file_type >= 2 and received > 0:
                try:
                    unpacked = save_path + '_unpack'
                    _unpack_feiq_dir(save_path, unpacked)
                    # 如果解包后只有一个子目录，展平一层
                    items = os.listdir(unpacked)
                    if len(items) == 1:
                        inner = os.path.join(unpacked, items[0])
                        if os.path.isdir(inner):
                            os.rename(inner, unpacked + '_flat')
                            os.rmdir(unpacked)
                            os.rename(unpacked + '_flat', unpacked)
                    try:
                        os.remove(save_path)
                        final = save_path
                        if os.path.exists(final):
                            shutil.rmtree(final)
                        os.rename(unpacked, final)
                        logger.info('文件夹解包完成: %s' % final)
                    except Exception:
                        logger.info('文件夹解包完成: %s' % unpacked)
                except Exception as e:
                    logger.error('解包失败: %s' % str(e))

        except Exception as e:
            logger.error('文件下载失败 %s: %s' % (filename, str(e)))

    # 发送文件
    def sendFile(self, peer_id, filepath):
        """发送文件给指定用户 — 使用飞秋 20002 加密信封格式

        格式: 20002:{rsa_cipher_hex}:{bf_cipher_hex}:{filename}:{size_hex}:{timestamp}:1:\0
        文件信息在外层明文，匹配 EncryptTextRecvHandler 的解析逻辑。
        """
        import os
        if not os.path.exists(filepath):
            logger.error('文件不存在: %s' % filepath)
            return

        addr = self.usermanager.getAddr(peer_id)
        if addr is None:
            logger.error('无法获取对方地址: %s' % peer_id)
            return

        self._ensure_online(peer_id, addr)

        filename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath)
        file_ctime = int(os.path.getctime(filepath))

        def do_send():
            # 先创建 sender 获取全局分配的 packno，再注册文件
            sender = CommandSender(IPMSG.IPMSG_SENDMSG | IPMSG.IPMSG_SENDCHECKOPT)
            real_packno = sender.packet.packno
            self._pending_files[real_packno] = {
                'filepath': filepath,
                'filename': filename,
                'filesize': file_size,
                'filectime': file_ctime,
                'file_type': 1,  # 单文件: 请求一次即可清理
            }

            outer_info = '%s:%x:%x:1:\x07' % (filename, file_size, file_ctime)
            if SecurtInstance.hsaKey(peer_id):
                # 加密发送: 文件元数据放在加密内层(真飞秋解密后必须在此找到)
                # 内层格式: \0{file_id}:{filename}:{size_hex}:{mtime}:{type}:\x07
                # 外层 \x000:{outer_info}\0 保留作为兼容回退
                inner_msg = '\0%d:%s:%x:%x:1:\x07' % (real_packno, filename, file_size, file_ctime)
                enKey, enMsg = SecurtInstance.encrypt(peer_id, inner_msg.encode(IPMSG.ENCODETYPE))
                sender.cmd |= IPMSG.IPMSG_ENCRYPTOPT | IPMSG.IPMSG_FILEATTACHOPT | IPMSG.FEIQ_EXTEND_CMD
                extra = '20002:%s:%s\x000:%s\0' % (enKey.hex(), enMsg.hex(), outer_info)
            else:
                # 无对方公钥时降级为明文文件通知
                sender.cmd |= IPMSG.IPMSG_FILEATTACHOPT | IPMSG.FEIQ_EXTEND_CMD
                extra = '0:%s:%x:%x:1:\x07\0' % (filename, file_size, file_ctime)

            def _get_extra():
                return extra.encode(IPMSG.ENCODETYPE)
            sender.getExtra = _get_extra
            sender.setData(self.me, addr[0], addr[1])
            self.CreateImmediatelyTask(self.__func_send(sender), '发送文件通知')
            logger.info('发送文件: %s (%d字节) packno=%d -> %s:%d' % (filename, file_size, real_packno, addr[0], addr[1]))

        if SecurtInstance.hsaKey(peer_id):
            do_send()
        else:
            # 先请求对方公钥
            rsaSender = ReqRsaSender()
            rsaSender.setData(self.me, addr[0], addr[1])
            self.CreateImmediatelyTask(self.__func_send(rsaSender), '请求RSA PUBKEY', 'PUBKEY_' + peer_id)
            self.CreateSwitchTask(do_send, lambda: None, 'PUBKEY_' + peer_id, 5000, '请求密钥后发送文件')

    # 批量发送文件 — 合并为一个通知（与真飞秋行为一致）
    def sendBatchFiles(self, peer_id, filepaths):
        import os, time
        if not filepaths:
            return
        addr = self.usermanager.getAddr(peer_id)
        if addr is None:
            logger.error('无法获取对方地址: %s' % peer_id)
            return
        self._ensure_online(peer_id, addr)

        # 收集文件信息
        file_infos = []
        for fp in filepaths:
            file_infos.append({
                'path': fp,
                'name': os.path.basename(fp),
                'size': os.path.getsize(fp),
                'ctime': int(os.path.getctime(fp)),
            })

        def do_send():
            sender = CommandSender(IPMSG.IPMSG_SENDMSG | IPMSG.IPMSG_SENDCHECKOPT)
            real_packno = sender.packet.packno

            # 注册所有文件到 pending（用递增 file_id）
            for idx, fi in enumerate(file_infos):
                self._pending_files[real_packno + idx] = {
                    'filepath': fi['path'],
                    'filename': fi['name'],
                    'filesize': fi['size'],
                    'filectime': fi['ctime'],
                    'file_type': 1,
                }

            # 构造通知: 真飞秋格式 — 文件用 \x07{id}: 连接
            inner_parts = []
            outer_parts = []
            for idx, fi in enumerate(file_infos):
                if idx == 0:
                    outer_parts.append('%s:%x:%x:1:\x07' % (fi['name'], fi['size'], fi['ctime']))
                    inner_parts.append('\0%d:%s:%x:%x:1:\x07' % (
                        real_packno + idx, fi['name'], fi['size'], fi['ctime']))
                else:
                    outer_parts.append('%d:%s:%x:%x:1:\x07' % (
                        real_packno + idx, fi['name'], fi['size'], fi['ctime']))
                    inner_parts.append('%d:%s:%x:%x:1:\x07' % (
                        real_packno + idx, fi['name'], fi['size'], fi['ctime']))

            outer_info = ''.join(outer_parts)
            inner_msg = ''.join(inner_parts)

            if SecurtInstance.hsaKey(peer_id):
                enKey, enMsg = SecurtInstance.encrypt(peer_id, inner_msg.encode(IPMSG.ENCODETYPE))
                sender.cmd |= IPMSG.IPMSG_ENCRYPTOPT | IPMSG.IPMSG_FILEATTACHOPT | IPMSG.FEIQ_EXTEND_CMD
                extra = '20002:%s:%s\x000:%s\0' % (enKey.hex(), enMsg.hex(), outer_info)
            else:
                sender.cmd |= IPMSG.IPMSG_FILEATTACHOPT | IPMSG.FEIQ_EXTEND_CMD
                extra = '0:%s\0' % outer_info

            def _get_extra():
                return extra.encode(IPMSG.ENCODETYPE)
            sender.getExtra = _get_extra
            sender.setData(self.me, addr[0], addr[1])
            self.CreateImmediatelyTask(self.__func_send(sender), '批量发送文件通知')
            logger.info('批量发送: %d个文件 packno=%d -> %s:%d' % (len(file_infos), real_packno, addr[0], addr[1]))

        if SecurtInstance.hsaKey(peer_id):
            do_send()
        else:
            rsaSender = ReqRsaSender()
            rsaSender.setData(self.me, addr[0], addr[1])
            self.CreateImmediatelyTask(self.__func_send(rsaSender), '请求RSA PUBKEY', 'PUBKEY_' + peer_id)
            self.CreateSwitchTask(do_send, lambda: None, 'PUBKEY_' + peer_id, 5000, '请求密钥后批量发送文件')

    # 发送文件夹
    def sendFolder(self, peer_id, folderpath):
        """发送文件夹 — 后台线程打包，避免大文件夹卡死UI"""
        import os, time, threading
        if not os.path.isdir(folderpath):
            logger.error('不是文件夹: %s' % folderpath)
            return
        addr = self.usermanager.getAddr(peer_id)
        if addr is None:
            logger.error('无法获取对方地址: %s' % peer_id)
            return
        self._ensure_online(peer_id, addr)
        folderpath = os.path.abspath(folderpath)
        threading.Thread(target=self._do_send_folder, args=(peer_id, addr, folderpath), daemon=True, name='打包发送文件夹').start()

    def _do_send_folder(self, peer_id, addr, folderpath):
        import os, time
        try:
            logger.info('开始打包文件夹: %s' % folderpath)
            packed = _pack_feiq_dir(folderpath)
            logger.info('打包完成: %s -> %s (%d字节)' % (folderpath, packed, os.path.getsize(packed)))
        except Exception as e:
            logger.error('打包文件夹失败: %s' % str(e))
            import traceback; logger.error(traceback.format_exc())
            return
        folder_name = os.path.basename(folderpath.rstrip('/\\'))
        HEADER_LEN = 0xC00 + 4
        packed_size = os.path.getsize(packed)
        packed_ctime = int(os.path.getctime(folderpath))
        notify_size = packed_size - HEADER_LEN  # 通知大小=去掉头部后的条目数据大小

        def do_send():
            # 先创建 sender 获取全局分配的 packno
            sender = CommandSender(IPMSG.IPMSG_SENDMSG | IPMSG.IPMSG_SENDCHECKOPT)
            real_packno = sender.packet.packno
            self._pending_files[real_packno] = {
                'filepath': packed,
                'filename': folder_name,
                'filesize': notify_size,
                'filectime': packed_ctime,
                'file_type': 2,
            }

            outer_info = '%s:%x:%x:2:\x07' % (folder_name, notify_size, packed_ctime)
            if SecurtInstance.hsaKey(peer_id):
                # 加密发送: 文件元数据放在加密内层(真飞秋解密后必须在此找到)
                # 内层格式: \0{file_id}:{filename}:{size_hex}:{mtime}:{type}:\x07
                # 外层 \x000:{outer_info}\0 保留作为兼容回退
                inner_msg = '\0%d:%s:%x:%x:2:\x07' % (real_packno, folder_name, packed_size, packed_ctime)
                enKey, enMsg = SecurtInstance.encrypt(peer_id, inner_msg.encode(IPMSG.ENCODETYPE))
                sender.cmd |= IPMSG.IPMSG_ENCRYPTOPT | IPMSG.IPMSG_FILEATTACHOPT | IPMSG.FEIQ_EXTEND_CMD
                extra = '20002:%s:%s\x000:%s\0' % (enKey.hex(), enMsg.hex(), outer_info)
            else:
                sender.cmd |= IPMSG.IPMSG_FILEATTACHOPT | IPMSG.FEIQ_EXTEND_CMD
                extra = '0:%s:%x:%x:2:\x07\0' % (folder_name, packed_size, packed_ctime)

            def _get_extra():
                return extra.encode(IPMSG.ENCODETYPE)
            sender.getExtra = _get_extra
            sender.setData(self.me, addr[0], addr[1])
            self.CreateImmediatelyTask(self.__func_send(sender), '发送文件夹通知')
            logger.info('发送文件夹: %s (%d字节) packno=%d -> %s:%d' % (folder_name, packed_size, real_packno, addr[0], addr[1]))

        if SecurtInstance.hsaKey(peer_id):
            do_send()
        else:
            rsaSender = ReqRsaSender()
            rsaSender.setData(self.me, addr[0], addr[1])
            self.CreateImmediatelyTask(self.__func_send(rsaSender), '请求RSA PUBKEY', 'PUBKEY_' + peer_id)
            self.CreateSwitchTask(do_send, lambda: None, 'PUBKEY_' + peer_id, 5000, '请求密钥后发送文件夹')
    
    def __socketSend(self,addr,message:bytes):
        if self.sendFunc is not None:
            self.sendFunc(message, addr)

    #获取处理接收报文的函数
    def __func_recv(self, packet):
        def func():
            packet.dump() #初步解析数据
            msg=Message()
            msg.friend = User(packet)
            msg.cmd = packet.cmd
            msg.extra = packet.extra
            msg.packno = packet.packno

            for handler in self.__recvHandler:
                if handler.handle(msg):
                    break

            logger.debug('数据报文%d处理完成'%msg.packno)
        return func

    #获取处理发送报文的函数
    def __func_send(self, sender:MsgSender):
        def func():
            logger.debug('开始处理一个发送数据报文')
            sender.save() #封装数据

            addr = (sender.packet.ip, sender.packet.port)
            self.__socketSend(addr, sender.packet.data)
        return func


def _unpack_feiq_dir(filepath, outdir):
    """解包飞秋文件夹格式 — 支持多文件"""
    import os, re
    with open(filepath, 'rb') as f:
        data = f.read()
    
    os.makedirs(outdir, exist_ok=True)
    dir_stack = [outdir]
    
    # 找所有有效的条目: 4位hex(<=200) + ':' + 可读文件名
    import re
    raw_entries = []
    for m in re.finditer(rb'([0-9a-f]{4}):', data):
        hlen = int(m.group(1), 16)
        if hlen < 1 or hlen > 200:
            continue
        content = data[m.end():m.end() + hlen]
        # 检查是不是有效条目：内容以可读字符开头
        if len(content) < 3:
            continue
        first_byte = content[0]
        if not (0x20 <= first_byte < 0x7f or first_byte >= 0x80):  # ASCII可打印或GB2312
            continue
        raw_entries.append({'pos': m.start(), 'len': hlen, 'content': content, 'is_hex': True})
    
    # 过滤：内容含 ':'分隔符才是真实条目
    entries = [e for e in raw_entries if b':' in e['content'][:min(60, len(e['content']))]]
    
    logger.info('解包: 找到 %d 个条目 (原始 %d)' % (len(entries), len(raw_entries)))
    
    # 解析每个条目
    count = 0
    for i, e in enumerate(entries):
        text = e['content'].decode(IPMSG.ENCODETYPE, errors='replace')
        parts = text.split(':', 3)
        if len(parts) < 3:
            continue
        
        name = parts[0]
        field2 = parts[1]
        field3 = parts[2]
        
        try:
            ftype = int(field3.split('=')[0])
        except:
            continue
        
        # 计算二进制数据边界
        next_pos = entries[i+1]['pos'] if i < len(entries) - 1 else len(data)
        
        if ftype == 1:
            # 文件: 二进制数据从 :0=16: 之后开始
            marker = e['content'].rfind(b':0=16:')
            if marker >= 0:
                data_start = e['pos'] + 5 + marker + 6  # 跳过 hex_len:+内容前半+:0=16:
            else:
                data_start = e['pos'] + 5 + e['len']  # fallback
            
            data_end = next_pos
            if data_end > data_start:
                filedata = data[data_start:data_end]
                savepath = os.path.join(dir_stack[-1], name)
                with open(savepath, 'wb') as fout:
                    fout.write(filedata)
                count += 1
        elif ftype in (2, 102):
            dirpath = os.path.join(dir_stack[-1], name)
            os.makedirs(dirpath, exist_ok=True)
            dir_stack.append(dirpath)
            count += 1
        elif ftype == 3 and len(dir_stack) > 1:
            dir_stack.pop()
    
    logger.info('解包完成: %d 个项目 -> %s' % (count, outdir))


def _pack_feiq_dir(folderpath):
    """打包文件夹为飞秋格式 — 完整支持嵌套目录（type=1/2/3）"""
    import os, time, tempfile

    folderpath = os.path.abspath(folderpath)
    root_name = os.path.basename(folderpath.rstrip('/\\'))

    # 收集所有条目的元信息: (meta_bytes, is_dir, entry_bytes_without_hlen)
    def _collect(dirpath):
        results = []
        children = sorted(os.listdir(dirpath))
        for name in children:
            full = os.path.join(dirpath, name)
            mtime = int(os.path.getmtime(full))
            if os.path.isdir(full):
                meta = '%s:000000000:2:14=%x:0=16:' % (name, mtime)
                meta_bytes = meta.encode('gbk', errors='replace')
                results.append((meta_bytes, True, None))  # dir entry
                results.extend(_collect(full))
                ret_meta = '.:0:3:14=%x:0=16:' % mtime
                ret_bytes = ret_meta.encode('gbk', errors='replace')
                results.append((ret_bytes, True, None))  # return entry
            else:
                size = os.path.getsize(full)
                with open(full, 'rb') as f:
                    content = f.read()
                meta = '%s:%09x:1:14=%x:0=16:' % (name, size, mtime)
                meta_bytes = meta.encode('gbk', errors='replace')
                results.append((meta_bytes, False, content))  # file entry
        return results

    # 构建数据
    data = bytearray(b'0<\x00\x00')  # 飞秋魔数头
    data.extend(b'\x00' * (0xC00 - len(data)))  # 填充到 0xC00
    data.extend(b'\x00\x00\x00\x00')  # 真飞秋在条目列表前有4字节占位(0xC00-0xC03)

    # 根目录条目 type=2
    root_mtime = int(os.path.getmtime(folderpath))
    root_meta = '%s:000000000:2:14=%x:0=16:' % (root_name, root_mtime)
    root_meta_bytes = root_meta.encode('gbk', errors='replace')
    data.extend(b'%04x:' % len(root_meta_bytes) + root_meta_bytes)
    root_meta_len = len(root_meta_bytes)

    # 收集所有子条目
    all_entries = _collect(folderpath)

    # 计算每个条目的实际hlen: 飞秋格式 hlen = metadata_len + 5 (所有条目一律+5)
    # 末尾补5字节padding, 确保最后条目的+5不会越界
    for meta_bytes, is_dir, binary in all_entries:
        hlen = len(meta_bytes) + 5
        data.extend(b'%04x:' % hlen + meta_bytes)
        if not is_dir and binary:
            data.extend(binary)

    # 根目录返回条目 type=3 (真飞秋格式要求)
    root_ret_meta = '.:0:3:14=%x:0=16:' % root_mtime
    root_ret_bytes = root_ret_meta.encode('gbk', errors='replace')
    root_ret_hlen = len(root_ret_bytes) + 5
    data.extend(b'%04x:' % root_ret_hlen + root_ret_bytes)

    # 末尾padding: 最后条目+5所需的5字节
    data.extend(b'\x00\x00\x00\x00\x00')

    # 修正根目录条目的hlen (现在知道下一条目头是5字节)
    root_with_next_hlen = root_meta_len + 5
    root_hlen_pos = 0xC00 + 4  # after 4-byte placeholder
    data[root_hlen_pos:root_hlen_pos+4] = b'%04x' % root_with_next_hlen

    # 写入临时文件
    fd, tmppath = tempfile.mkstemp(suffix='_' + root_name, prefix='feiq_pack_')
    os.close(fd)
    with open(tmppath, 'wb') as f:
        f.write(bytes(data))
    return tmppath


Instance = MainWorkThread()