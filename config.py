"""插件配置模块"""

from pathlib import Path
import shutil
import asyncio
import subprocess
from pydantic import BaseModel
from nonebot import get_plugin_config, logger
from nonebot.plugin import PluginMetadata

class Config(BaseModel):
    """ASMR100插件配置"""
    
    # HTTP请求头配置
    asmr_http_headers: dict = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
    }
    
    # 支持的音频格式
    asmr_audio_extensions: list = ['.mp3', '.wav', '.ogg', '.flac', '.m4a']
    
    # 压缩包密码
    asmr_zip_password: str = "afu3355"
    
    # 最大错误尝试次数
    asmr_max_error_count: int = 3
    
    # API配置
    asmr_api_base_url: str = "https://api.asmr-200.com/api"
    asmr_api_timeout: int = 15

# 全局配置实例
plugin_config = get_plugin_config(Config)

def has_command(command):
    """检查系统命令是否可用"""
    return shutil.which(command) is not None

def check_ffmpeg_dependency():
    """检查ffmpeg依赖"""
    if has_command("ffmpeg"):
        logger.info("ffmpeg已安装，支持音频格式转换")
    else:
        logger.warning("ffmpeg未找到，音频格式转换功能可能不可用")

async def check_dependencies():
    """检查系统依赖"""
    logger_prefix = "[ASMR100]"
    
    # 检查ffmpeg
    check_ffmpeg_dependency()
    
    # 检查7z压缩工具
    sevenz_found = False
    if has_command("7z"):
        sevenz_found = True
        logger.info(f"{logger_prefix} 7z 已安装，支持高强度加密")
    else:
        try:
            process = await asyncio.create_subprocess_exec(
                "7z",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 or process.returncode == 7:
                sevenz_found = True
                logger.info(f"{logger_prefix} 7z 已安装，支持高强度加密")
        except Exception:
            logger.warning(f"{logger_prefix} 7z 检测失败，将尝试备用加密方式")
    
    # 检查zip命令
    if not sevenz_found:
        if has_command("zip"):
            logger.info(f"{logger_prefix} zip 命令已安装，将使用zip加密")
        else:
            try:
                process = await asyncio.create_subprocess_exec(
                    "zip", "--version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    logger.info(f"{logger_prefix} zip 命令已安装，将使用zip加密")
                else:
                    logger.warning(f"{logger_prefix} 未找到可用的压缩工具，将使用内置加密")
            except Exception:
                logger.warning(f"{logger_prefix} 未找到可用的压缩工具，将使用内置加密")
    
    logger.info(f"{logger_prefix} 插件初始化完成，所有核心功能可用")