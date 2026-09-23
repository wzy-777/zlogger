# zlogger

多进程安全的时间轮转日志记录器，基于标准库 `logging` 封装。

## 特点

- `SafeTimedRotatingFileHandler`：原子 rename 轮转，多个进程共享同一日志文件时不丢历史日志，已有备份绝不删除/覆盖
- 控制台 + 文件双输出，文件按天（午夜）轮转，默认保留 7 天
- `console=False` 可关闭控制台输出（适配 systemd 等重定向 stderr 的部署场景）
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

关闭控制台输出（仅写文件）：

```python
log = Logger(name="test", log_file="test.log", log_dir="log", console=False).get_logger()
```

## 与 systemd 一起使用

systemd 托管服务时，`StandardOutput` / `StandardError` **不要指向与 `log_file` 相同的文件**，建议指向独立文件：

```ini
[Service]
ExecStart=/path/to/python /path/to/app.py
StandardOutput=append:/path/to/log/app-stderr.log
StandardError=append:/path/to/log/app-stderr.log
```

原因有二：

1. **重复落盘**：console handler 默认输出到 stderr。若 `StandardError` 与 `log_file` 是同一文件，同一条日志会通过 file handler 和重定向的 stderr 各写一次。此时应使用 `console=False` 关闭控制台输出。
2. **轮转后输出丢失**：systemd 在服务启动时打开重定向文件并长期持有 fd，而 fd 绑定的是 inode 不是路径。轮转时 `os.rename` 会把旧 inode 改名为历史备份，systemd 的后续输出（未捕获异常的 traceback、uvicorn 访问日志等）仍写入这个旧 inode——先是写进历史文件，`backupCount` 清理后更是**静默丢失**且磁盘空间不释放。

指向独立文件即可同时规避两个问题：zlogger 独占 `log_file`（轮转安全），systemd 捕获的其他输出在 `app-stderr.log` 中随时可查。

## License

MIT
