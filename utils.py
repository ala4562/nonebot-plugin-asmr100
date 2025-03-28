"""工具函数"""

import re
import os
import random
import string
from pathlib import Path
from typing import List, Optional

from nonebot.log import logger
from . import USER_ERROR_COUNTS
from .config import plugin_config

def format_rj_id(rj_id: str) -> str:
    """
    格式化RJ号
    
    参数:
        rj_id: 原始RJ号
        
    返回:
        格式化后的RJ号
    """
    rj_id = rj_id.upper()
    if not rj_id.startswith("RJ"):
        rj_id = f"RJ{rj_id}"
    return rj_id

def sanitize_filename(filename: str, prefix: str = "") -> str:
    """
    清理文件名，确保文件名安全
    
    参数:
        filename: 原始文件名
        prefix: 可选前缀，例如RJ号
        
    返回:
        安全的文件名
    """
    # 替换文件系统中不允许的字符
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename)
    
    # 添加前缀（如果提供）
    if prefix:
        sanitized = f"{prefix}_{sanitized}"
    
    # 确保文件名不为空
    if not sanitized or len(sanitized) < 3:
        sanitized = "audio_file"
    
    # 限制文件名长度（如果太长）
    if len(sanitized) > 200:  # 使用较宽松的长度限制
        sanitized = sanitized[:200]
    
    return sanitized

def get_file_size_str(size_bytes: int) -> str:
    """
    将字节转换为友好的大小表示
    
    参数:
        size_bytes: 文件大小(字节)
        
    返回:
        友好的大小字符串，如 "1.5 MB"
    """
    # 小于1KB
    if size_bytes < 1024:
        return f"{size_bytes} B"
    # 小于1MB
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.2f} KB"
    # 小于1GB
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes/(1024*1024):.2f} MB"
    # 大于等于1GB
    else:
        return f"{size_bytes/(1024*1024*1024):.2f} GB"

def find_rj_directory(rj_id: str) -> Optional[Path]:
    """
    查找已下载的RJ目录
    
    参数:
        rj_id: RJ号
        
    返回:
        目录路径，若不存在则返回None
    """
    data_dir = plugin_config.asmr_data_dir
    rj_id = rj_id.upper()
    for pattern in [f"*{rj_id}*", f"*{rj_id[2:]}*"]:
        matches = list(data_dir.glob(pattern))
        if matches:
            return matches[0]
    return None

def find_audio_files(directory: Path) -> List[Path]:
    """
    在目录中查找音频文件
    
    参数:
        directory: 要搜索的目录
        
    返回:
        音频文件路径列表
    """
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
    """
    检查用户错误次数是否超过阈值
    
    参数:
        user_id: 用户ID
        increment: 是否增加错误计数
        
    返回:
        布尔值，True表示未超过阈值，False表示已超过阈值
    """
    max_error_count = plugin_config.asmr_max_error_count
    
    if user_id not in USER_ERROR_COUNTS:
        USER_ERROR_COUNTS[user_id] = 0
        
    if increment:
        USER_ERROR_COUNTS[user_id] += 1
        
    return USER_ERROR_COUNTS[user_id] < max_error_count

def generate_random_string(length: int = 6) -> str:
    """
    生成指定长度的随机字符串
    
    参数:
        length: 字符串长度
        
    返回:
        随机字符串
    """
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))