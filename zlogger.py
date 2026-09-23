import logging
from logging.handlers import TimedRotatingFileHandler
import os
import time


class SafeTimedRotatingFileHandler(TimedRotatingFileHandler):
    """
    多进程安全的时间轮转文件处理器：
    原子 rename 轮转 + 已有备份绝不删除/覆盖，多个进程共享同一日志文件时不丢历史日志
    """

    def doRollover(self):
        """
        重写doRollover方法，处理Windows文件权限问题
        """
        if self.stream:
            self.stream.close()
            self.stream = None

        # 获取当前时间
        currentTime = int(time.time())
        dstNow = time.localtime(currentTime)[-1]
        t = self.rolloverAt - self.interval
        if self.utc:
            timeTuple = time.gmtime(t)
        else:
            timeTuple = time.localtime(t)
            dstThen = timeTuple[-1]
            if dstNow != dstThen:
                if dstNow:
                    addend = 3600
                else:
                    addend = -3600
                timeTuple = time.localtime(t + addend)

        dfn = self.rotation_filename(self.baseFilename + "." + time.strftime(self.suffix, timeTuple))

        # 原子 rename 备份，不用 copy+truncate：
        # 多进程/多 handler 共享同一日志文件时，由第一个轮转的进程完成备份；
        # 备份已存在说明其他进程已轮转过，直接跳过 —— 任何情况下都不删除、不覆盖已有备份
        if os.path.exists(dfn):
            pass
        elif os.path.exists(self.baseFilename):
            try:
                os.rename(self.baseFilename, dfn)
            except FileNotFoundError:
                # base 刚被其他进程轮转走，无需再处理
                pass
            except OSError as e:
                # 轮转失败仅告警，不影响后续写日志
                print(f"日志轮转失败: {e}")

        # 删除旧的备份文件
        if self.backupCount > 0:
            for s in self.getFilesToDelete():
                try:
                    os.remove(s)
                except Exception:
                    pass

        # 重新计算下次轮转时间
        if not self.delay:
            self.stream = self._open()

        newRolloverAt = self.computeRollover(currentTime)
        while newRolloverAt <= currentTime:
            newRolloverAt = newRolloverAt + self.interval

        if (self.when == 'MIDNIGHT' or self.when.startswith('W')) and not self.utc:
            dstAtRollover = time.localtime(newRolloverAt)[-1]
            if dstNow != dstAtRollover:
                if not dstNow:
                    addend = -3600
                else:
                    addend = 3600
                newRolloverAt += addend
        self.rolloverAt = newRolloverAt


class Logger:
    def __init__(self, name: str, log_file: str = "app.log", log_dir: str = "log",
                 console: bool = True):
        """
        创建一个日志记录器
        :param name: 记录器名称
        :param log_file: 日志文件名
        :param log_dir: 日志文件保存目录
        :param console: 是否输出到控制台（stderr）。stderr 被重定向到日志文件时
                        （如 systemd StandardError=append:）应设为 False，避免同一条日志重复落盘
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False
        # 确保日志目录存在
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        log_path = os.path.join(log_dir, log_file)

        # 日志格式
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(name)s] [%(filename)s:%(lineno)d] [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # 控制台 Handler（console=False 时不注册，日志仅写入文件）
        console_handler = None
        if console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            console_handler.setFormatter(formatter)

        # 文件 Handler（使用改进的TimedRotatingFileHandler）
        file_handler = SafeTimedRotatingFileHandler(
            filename=log_path,
            when="midnight",
            interval=1,
            backupCount=7,
            encoding="utf-8",
            delay=True
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)

        # 先清空已存在的handlers
        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        # 绑定 Handler
        if console_handler:
            self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

    def get_logger(self) -> logging.Logger:
        """返回 logger 对象"""
        return self.logger


class LoggerSingleton:
    _logger = None

    @classmethod
    def get_logger(cls, name="websocket", log_file="websocket.log", log_dir="log",
                   console=True):
        if cls._logger is None:
            cls._logger = Logger(name, log_file, log_dir, console=console).get_logger()
        return cls._logger

# 使用示例
if __name__ == "__main__":
    log = Logger(name="test", log_file="test.log", log_dir="log").get_logger()
    log.debug("调试信息（仅控制台输出）")
    log.info("普通信息（控制台 + 文件）")
    log.warning("警告信息（控制台 + 文件）")
    log.error("错误信息（控制台 + 文件）")
    log.critical("严重错误（控制台 + 文件）")