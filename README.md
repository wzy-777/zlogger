# zlogger

多进程安全的时间轮转日志记录器，基于标准库 `logging` 封装。

## 特点

- `SafeTimedRotatingFileHandler`：原子 rename 轮转，多个进程共享同一日志文件时不丢历史日志，已有备份绝不删除/覆盖
- 控制台 + 文件双输出，文件按天（午夜）轮转，默认保留 7 天
- 开箱即用，无需配置

## 安装

```bash
pip install zlogger-mp
```

## 使用

```python
from zlogger import Logger

log = Logger(name="test", log_file="test.log", log_dir="log").get_logger()
log.debug("调试信息（仅控制台输出）")
log.info("普通信息（控制台 + 文件）")
log.warning("警告信息（控制台 + 文件）")
log.error("错误信息（控制台 + 文件）")
```

单例方式（全局共享一个 logger）：

```python
from zlogger import LoggerSingleton

log = LoggerSingleton.get_logger(name="myapp", log_file="myapp.log")
log.info("hello")
```

## License

MIT
