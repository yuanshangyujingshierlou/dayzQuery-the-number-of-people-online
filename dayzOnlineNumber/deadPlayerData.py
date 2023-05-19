import threading
import time


class DataRecorder:
    def __init__(self):
        self.data = {}
        self.lock = threading.Lock()  # 添加锁以防止并发访问

        self.cleanup_thread = threading.Thread(target=self.cleanup_expired_data, daemon=True)
        self.cleanup_thread.start()

    def add_data(self, key, value):
        with self.lock:
            self.data[key] = {"value": value, "timestamp": time.time()}

    def remove_data(self, key):
        with self.lock:
            if key in self.data:
                del self.data[key]

    # 查询数据是否存在
    def has_data(self, key):
        with self.lock:
            return key in self.data

    def cleanup_expired_data(self):
        while True:
            with self.lock:
                for key, value in list(self.data.items()):  # 使用list函数创建data的副本以避免字典大小改变错误
                    if (time.time() - value["timestamp"]) > 15:
                        del self.data[key]
            time.sleep(1)  # 每隔一秒钟检查一次是否有过期数据
