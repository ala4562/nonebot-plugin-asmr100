"""工具函数模块"""

import re
import os
import random
import string
import asyncio
import functools
from pathlib import Path
from typing import List, Optional, Callable, Any

from nonebot.log import logger
from . import USER_ERROR_COUNTS
from .config import plugin_config

def run_in_executor(func: Callable) -> Callable:
    """装饰器：将同步函数包装为异步执行"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, functools.partial(func, *args, **kwargs))
    return wrapper

async def async_file_operation(operation: Callable, *args, **kwargs) -> Any:
    """异步执行文件操作"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, functools.partial(operation, *args, **kwargs))

def format_rj_id(rj_id: str) -> str:
    """格式化RJ号为标准格式"""
    rj_id = rj_id.upper()
    if not rj_id.startswith("RJ"):
        rj_id = f"RJ{rj_id}"
    return rj_id

def sanitize_filename(filename: str, prefix: str = "") -> str:
    """清理文件名，确保文件系统兼容性"""
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename)
    
    if prefix:
        sanitized = f"{prefix}_{sanitized}"
    
    if not sanitized or len(sanitized) < 3:
        sanitized = "audio_file"
    
    if len(sanitized) > 200:
        sanitized = sanitized[:200]
    
    return sanitized

def get_file_size_str(size_bytes: int) -> str:
    """将字节转换为可读的文件大小格式"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes/(1024*1024):.2f} MB"
    else:
        return f"{size_bytes/(1024*1024*1024):.2f} GB"

def find_rj_directory(rj_id: str) -> Optional[Path]:
    """查找已下载的RJ目录"""
    from . import DATA_DIR
    rj_id = rj_id.upper()
    for pattern in [f"*{rj_id}*", f"*{rj_id[2:]}*"]:
        matches = list(DATA_DIR.glob(pattern))
        if matches:
            return matches[0]
    return None

def find_audio_files(directory: Path) -> List[Path]:
    """在目录中查找音频文件"""
    audio_exts = plugin_config.asmr_audio_extensions
    
    if not directory.is_dir():
        if directory.suffix.lower() in audio_exts:
            return [directory]
        return []
    
    audio_files = []
    for ext in audio_exts:
        audio_files.extend(directory.glob(f"**/*{ext}"))
    
    return sorted(audio_files)

def check_user_error_limit(user_id: str, increment: bool = False) -> bool:
    """检查用户错误次数是否超过限制"""
    max_error_count = plugin_config.asmr_max_error_count
    
    if user_id not in USER_ERROR_COUNTS:
        USER_ERROR_COUNTS[user_id] = 0
        
    if increment:
        USER_ERROR_COUNTS[user_id] += 1
        
    return USER_ERROR_COUNTS[user_id] < max_error_count

def generate_random_string(length: int = 6) -> str:
    """生成指定长度的随机字符串"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))