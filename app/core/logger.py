import logging
from logging.handlers import RotatingFileHandler # 日志轮转
from pathlib import Path
from .config import settings

def setup_logger(name:str|None=None) -> logging.Logger:
    project_root = Path(__file__).resolve().parents[2]
    log_dir = project_root / settings.LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    # log_dir = Path(settings.LOG_DIR)
    # log_dir.mkdir(parents=True, exist_ok=True)#exist_ok如果文件夹已经存在，程序会抛出 FileExistsError   parents允许创建多级目录。

    logger = logging.getLogger(name)# 获取或创建日志记录器按照文件名称创建
    logger.setLevel(settings.LOG_LEVEL.upper())# 日志等级
    logger.propagate = False  # 防止重复日志

    if logger.handlers:
        return logger
    # 统一日志格式
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler = logging.StreamHandler()# 默认情况下，它将日志发送到 sys.stderr（标准错误流），也就是你运行程序的终端或控制台窗口。
    console_handler.setFormatter(formatter)#如果不执行这一行，控制台输出的日志将只有最原始的消息内容（例如：用户已登录），而没有时间戳和文件名等关键调试信息。
    
    file_handler = RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)


    error_handler = RotatingFileHandler(
        log_dir / "error.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)


    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)

    return logger


