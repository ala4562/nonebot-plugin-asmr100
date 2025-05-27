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
from .states import USER_ERROR_COUNTS, USER_SEARCH_STATES
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

def detect_file_extension(title: str) -> str:
    """检测音频或视频文件的扩展名"""
    title_lower = title.lower()

    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v']
    for ext in video_extensions:
        if title_lower.endswith(ext):
            return ext
        elif ext in title_lower:
            return ext

    if title_lower.endswith('.wav'):
        return '.wav'
    elif title_lower.endswith('.flac'):
        return '.flac'
    elif title_lower.endswith('.ogg'):
        return '.ogg'
    elif title_lower.endswith('.m4a'):
        return '.m4a'
    elif title_lower.endswith('.mp3'):
        return '.mp3'

    elif '.wav' in title_lower:
        return '.wav'
    elif '.flac' in title_lower:
        return '.flac'
    elif '.ogg' in title_lower:
        return '.ogg'
    elif '.m4a' in title_lower:
        return '.m4a'
    else:
        return '.mp3'

def is_video_file(filename: str) -> bool:
    """检测是否为视频文件"""
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v']
    filename_lower = filename.lower()
    

    for ext in video_extensions:
        if filename_lower.endswith(ext):
            return True
    
    for ext in video_extensions:
        if ext in filename_lower:
            return True
    
    return False

def is_audio_file(filename: str) -> bool:
    """检测是否为音频文件"""
    filename_lower = filename.lower()
    audio_extensions = ['.mp3', '.wav', '.ogg', '.flac', '.m4a']

    for ext in audio_extensions:
        if filename_lower.endswith(ext):
            return True

    for ext in audio_extensions:
        if ext in filename_lower:
            return True
    
    return False

def should_convert_to_mp3(filename: str, is_single_file: bool = False) -> bool:
    """判断是否应该转换为MP3格式
    
    Args:
        filename: 文件名
        is_single_file: 是否为单文件下载
        
    Returns:
        bool: 是否应该转换
    """

    if is_video_file(filename):
        return False

    if not is_audio_file(filename):
        return False

    if is_single_file:
        return False

    if filename.lower().endswith('.mp3'):
        return False

    return True

def sanitize_filename(filename: str, prefix: str = "") -> str:
    """清理文件名，确保文件系统兼容性和安全性"""

    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", filename)

    sanitized = re.sub(r'^[.\s]+', "", sanitized)

    sanitized = re.sub(r'[.\s]+$', "", sanitized)

    reserved_names = {'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 
                     'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4', 
                     'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'}
    if sanitized.upper() in reserved_names:
        sanitized = f"file_{sanitized}"
    
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

def generate_folder_letter(index: int) -> str:
    """生成文件夹的字母序号"""
    if index < 26:
        return chr(65 + index)  # A-Z
    else:

        first = chr(65 + (index // 26) - 1)
        second = chr(65 + (index % 26))
        return f"{first}{second}"

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

def generate_unique_zip_filename(rj_id: str, file_type: str = "single") -> str:
    """生成唯一的ZIP文件名"""
    rj_number = re.sub(r'[^0-9]', '', rj_id)
    timestamp = int(asyncio.get_event_loop().time())
    return f"{rj_number}_{file_type}_{timestamp}.zip"

async def cleanup_user_states(max_age_hours: int = 24):
    """清理过期的用户状态"""
    import time
    current_time = time.time()
    
    # 清理搜索状态
    expired_users = []
    for user_id, state in USER_SEARCH_STATES.items():
        if 'timestamp' in state:
            if current_time - state['timestamp'] > max_age_hours * 3600:
                expired_users.append(user_id)
    
    for user_id in expired_users:
        del USER_SEARCH_STATES[user_id]
    
    if expired_users:
        USER_ERROR_COUNTS.clear()
    
    if expired_users:
        logger.info(f"清理了 {len(expired_users)} 个过期用户状态")