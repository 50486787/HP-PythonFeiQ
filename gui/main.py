"""HP-PythonFeiQ v0.7 GUI 入口"""
import sys
import os
import socket
import threading
import traceback


def _excepthook(exc_type, exc_value, exc_tb):
    """全局异常捕获 — 打印到 stderr 并弹窗"""
    tb_text = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    sys.stderr.write(tb_text)
    sys.stderr.flush()
    # 尝试弹窗报错
    try:
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.critical(None, '程序崩溃', tb_text[-500:])
    except Exception:
        pass
    sys.__excepthook__(exc_type, exc_value, exc_tb)


sys.excepthook = _excepthook

# 高 DPI：必须在 QApplication 创建之前设置
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

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
    # 高 DPI 适配（必须在 QApplication 构造前）
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # 根据屏幕尺寸计算默认窗口大小（约占屏幕 65%）
    screen = app.primaryScreen()
    if screen:
        screen_geom = screen.availableGeometry()
        win_w = max(int(screen_geom.width() * 0.62), 900)
        win_h = max(int(screen_geom.height() * 0.58), 600)
    else:
        win_w, win_h = 1100, 700

    # 启动 UDP 服务器
    udp_server = UDPServer((setting.IPADDRESS, setting.PORT), UdpHandle)
    udp_server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    server_thread = threading.Thread(
        target=udp_server.serve_forever, name='UDP-Server', daemon=True)
    server_thread.start()

    # 创建窗口
    window = MainWindow(win_w, win_h)

    # 绑定飞秋引擎
    Instance.start(udp_server.socket.sendto, window.onViewDispatch)
    Instance.file_recv_cb = window._file_recv_handler

    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
