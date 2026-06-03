"""HP-PythonFeiQ v0.7 GUI 入口"""
import sys
import os
import socket
import threading

# 确保引擎模块可导入（gui/ 的父目录）
ENGINE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ENGINE_DIR not in sys.path:
    sys.path.insert(0, ENGINE_DIR)

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from gui.main_window import MainWindow

from SocketHandle import UdpHandle
from socketserver import UDPServer
from WorkThread import Instance
import setting


def main():
    # 高 DPI 适配
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # 启动 UDP 服务器
    udp_server = UDPServer((setting.IPADDRESS, setting.PORT), UdpHandle)
    udp_server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    server_thread = threading.Thread(
        target=udp_server.serve_forever, name='UDP-Server', daemon=True)
    server_thread.start()

    # 创建窗口
    window = MainWindow()

    # 绑定飞秋引擎
    Instance.start(udp_server.socket.sendto, window.onViewDispatch)
    Instance.file_recv_cb = window._file_recv_handler

    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
