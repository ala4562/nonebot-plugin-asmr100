"""配置模块"""

from pathlib import Path
from pydantic import BaseModel, validator
from nonebot import get_driver

class Config(BaseModel):
    """ASMR100插件配置"""
    
    # 数据目录
    asmr_data_dir: Path = Path("data/asmr100")
    
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
    
    @validator("asmr_data_dir", pre=True)
    def validate_data_dir(cls, v):
        """验证并转换数据目录"""
        if isinstance(v, str):
            return Path(v)
        return v

# 从环境变量中加载配置
driver = get_driver()

@driver.on_startup
async def check_dependencies():
    """检查系统依赖"""
    logger_prefix = "[ASMR100]"
    try:
        # 检查ffmpeg
        process = await asyncio.create_subprocess_exec(
            "ffmpeg", "-version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            get_driver().logger.info(f"{logger_prefix} ffmpeg 已安装，支持音频格式转换")
        else:
            get_driver().logger.warning(f"{logger_prefix} ffmpeg 未找到，音频格式转换功能将不可用")
    except Exception:
        get_driver().logger.warning(f"{logger_prefix} ffmpeg 未找到，音频格式转换功能将不可用")
    
    try:
        # 检查7z
        process = await asyncio.create_subprocess_exec(
            "7z", "--help",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            get_driver().logger.info(f"{logger_prefix} 7z 已安装，支持高强度加密")
        else:
            get_driver().logger.warning(f"{logger_prefix} 7z 未找到，将使用备用加密方式")
            
            # 尝试检查zip命令
            try:
                process = await asyncio.create_subprocess_exec(
                    "zip", "--version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    get_driver().logger.info(f"{logger_prefix} zip 命令已安装，将使用zip加密")
                else:
                    get_driver().logger.warning(f"{logger_prefix} zip 命令未找到，将使用内置弱加密")
            except Exception:
                get_driver().logger.warning(f"{logger_prefix} zip 命令未找到，将使用内置弱加密")
    except Exception:
        get_driver().logger.warning(f"{logger_prefix} 7z 和 zip 均未找到，将使用内置弱加密")

# 检查 driver.config 的类型并相应处理
driver_config = get_driver().config
if isinstance(driver_config, dict):
    plugin_config = Config.parse_obj(driver_config)
else:
    # 如果不是字典，尝试使用 dict() 或直接使用默认值
    try:
        config_dict = dict(driver_config)
        plugin_config = Config.parse_obj(config_dict)
    except (TypeError, ValueError):
        # 如果转换失败，使用默认配置
        plugin_config = Config()