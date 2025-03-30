"""配置模块"""

from pathlib import Path
import shutil
import asyncio
import subprocess
from pydantic import BaseModel
from nonebot import get_plugin_config, logger
from nonebot.plugin import PluginMetadata

class Config(BaseModel):
    """ASMR100插件配置"""
    
    # 数据目录
    asmr_data_dir: Path = Path("nonebot_plugin_asmr100")
    
    # HTTP请求头
    asmr_http_headers: dict = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
    }
    
    # 支持的音频格式
    asmr_audio_extensions: list = ['.mp3', '.wav', '.ogg', '.flac', '.m4a']
    
    # 压缩包密码
    asmr_zip_password: str = "afu3355"
    
    # 最大错误尝试次数
    asmr_max_error_count: int = 3
    
    # API基础URL
    asmr_api_base_url: str = "https://api.asmr-200.com/api"
    
    # 超时设置(秒)
    asmr_api_timeout: int = 15

# 创建全局配置对象
plugin_config = get_plugin_config(Config)

# 检查系统依赖的更可靠方法
def has_command(command):
    """检查命令是否存在"""
    return shutil.which(command) is not None

async def check_dependencies():
    """检查系统依赖，使用更可靠的方法"""
    logger_prefix = "[ASMR100]"
    
    # 检查ffmpeg
    if has_command("ffmpeg"):
        logger.info(f"{logger_prefix} ffmpeg 已安装，支持音频格式转换")
    else:
        # 尝试以另一种方式检查
        try:
            result = subprocess.run(["ffmpeg", "-version"], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE, 
                                   text=True, 
                                   check=False)
            if result.returncode == 0:
                logger.info(f"{logger_prefix} ffmpeg 已安装，支持音频格式转换")
            else:
                logger.warning(f"{logger_prefix} ffmpeg 未找到或无法执行，音频格式转换功能可能不可用")
        except Exception:
            logger.warning(f"{logger_prefix} ffmpeg 检测失败，但不影响主要功能，音频格式转换可能不可用")
    
    # 检查7z
    sevenz_found = False
    if has_command("7z"):
        sevenz_found = True
        logger.info(f"{logger_prefix} 7z 已安装，支持高强度加密")
    else:
        # 尝试以另一种方式检查
        try:
            result = subprocess.run(["7z"], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE, 
                                   text=True, 
                                   check=False)
            if result.returncode == 0 or result.returncode == 7:  # 7z在没有参数时会返回错误码7
                sevenz_found = True
                logger.info(f"{logger_prefix} 7z 已安装，支持高强度加密")
        except Exception:
            logger.warning(f"{logger_prefix} 7z 检测失败，将尝试备用加密方式")
    
    # 如果没找到7z，检查zip
    if not sevenz_found:
        if has_command("zip"):
            logger.info(f"{logger_prefix} zip 命令已安装，将使用zip加密")
        else:
            try:
                result = subprocess.run(["zip", "--version"], 
                                       stdout=subprocess.PIPE, 
                                       stderr=subprocess.PIPE, 
                                       text=True, 
                                       check=False)
                if result.returncode == 0:
                    logger.info(f"{logger_prefix} zip 命令已安装，将使用zip加密")
                else:
                    logger.warning(f"{logger_prefix} 未找到可用的压缩工具，将使用内置弱加密")
            except Exception:
                logger.warning(f"{logger_prefix} 未找到可用的压缩工具，将使用内置弱加密")
    
    # 最后，告诉用户所有功能都会工作，只是某些情况下性能或安全性可能降低
    logger.info(f"{logger_prefix} 插件已启动，所有核心功能可用")