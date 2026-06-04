"""传输管理器 — 进度追踪 + 取消 + 超时检测，与 UI 解耦"""
import time
import queue

from PyQt5.QtCore import QObject, pyqtSignal, QTimer


class TransferManager(QObject):
    """管理文件传输的状态、进度和取消。

    引擎 progress_cb/cancel_cb 在后台线程中被调用，
    _on_engine_progress 不能直接 emit PyQt5 信号（跨线程可能失效），
    改为 put 到 queue.Queue，由主线程 QTimer 取出后 emit。
    """

    progressUpdated = pyqtSignal(str, int, int)
    transferCancelled = pyqtSignal(str)
    transferFailed = pyqtSignal(str, str)

    STALE_TIMEOUT = 60

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cancelled = set()
        self._start_times = {}
        self._progress_queue = queue.Queue()

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_progress)
        self._poll_timer.start(100)

        self._stale_timer = QTimer(self)
        self._stale_timer.timeout.connect(self._check_stale)
        self._stale_timer.start(30000)

    def bind_engine(self, instance):
        instance.progress_cb = self._on_engine_progress
        instance.cancel_cb = self._on_engine_cancel_check

    def start_transfer(self, filename: str):
        self._cancelled.discard(filename)
        self._start_times[filename] = time.time()

    def request_cancel(self, filename: str):
        self._cancelled.add(filename)
        self._start_times.pop(filename, None)
        self.transferCancelled.emit(filename)

    def finish_transfer(self, filename: str):
        self._cancelled.discard(filename)
        self._start_times.pop(filename, None)

    def _on_engine_progress(self, filename: str, bytes_done: int, total: int):
        """后台线程调用 → 入队，不直接 emit"""
        if bytes_done > 0:
            self._start_times.pop(filename, None)
        self._progress_queue.put((filename, bytes_done, total))

    def _poll_progress(self):
        """主线程定时消费队列 → 安全 emit"""
        try:
            while True:
                filename, bytes_done, total = self._progress_queue.get_nowait()
                self.progressUpdated.emit(filename, bytes_done, total)
        except queue.Empty:
            pass

    def _on_engine_cancel_check(self, filename: str) -> bool:
        return filename in self._cancelled

    def _check_stale(self):
        now = time.time()
        stale = [f for f, t in self._start_times.items() if now - t > self.STALE_TIMEOUT]
        for fname in stale:
            if fname in self._cancelled:
                self._start_times.pop(fname, None)
                continue
            self._start_times.pop(fname, None)
            self.transferFailed.emit(fname, '对方未接收')
