"""ASMR音声分享插件"""

import os
from pathlib import Path
import asyncio
from datetime import datetime, time

from nonebot import require, logger, get_driver, get_bot
from nonebot.plugin import PluginMetadata

require("nonebot_plugin_htmlrender")
require("nonebot_plugin_localstore")

import nonebot_plugin_localstore as store

from .config import Config, check_ffmpeg_dependency, plugin_config
from .utils import cleanup_user_states, async_file_operation

DATA_DIR = store.get_plugin_data_dir()
DATA_DIR.mkdir(parents=True, exist_ok=True)

from .commands.play import play
from .commands.search import search, search_next

__plugin_meta__ = PluginMetadata(
    name="ASMR音声分享插件",
    description="分享ASMR音声资源",
    usage="发送 搜音声+关键词 或 听音声+RJ号 使用插件",
    type="application",
    homepage="https://github.com/your-repo",
    config=Config,
    supported_adapters={"~onebot.v11"},
)

__all__ = ["play", "search", "search_next"]

driver = get_driver()

async def clean_cache_files():
    """清理所有缓存文件和压缩包"""
    try:
        import shutil
        
        if not DATA_DIR.exists():
            return
        
        total_size = 0
        deleted_count = 0
        
        # 遍历所有RJ目录
        for rj_folder in DATA_DIR.iterdir():
            if rj_folder.is_dir():
                # 计算文件夹大小
                folder_size = sum(f.stat().st_size for f in rj_folder.rglob('*') if f.is_file())
                total_size += folder_size
                
                # 删除整个文件夹
                try:
                    await async_file_operation(shutil.rmtree, str(rj_folder))
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"删除文件夹失败 {rj_folder}: {str(e)}")
        
        # 清理用户状态
        await cleanup_user_states()
        
        if deleted_count > 0:
            size_mb = total_size / (1024 * 1024)
            logger.info(f"定时清理完成: 删除了 {deleted_count} 个缓存目录，释放空间 {size_mb:.2f}MB")
        else:
            logger.info("定时清理完成: 无缓存文件需要清理")
            
    except Exception as e:
        logger.error(f"定时清理任务失败: {str(e)}")

async def schedule_cleanup():
    """调度清理任务"""
    while True:
        try:
            now = datetime.now()
            # 计算到凌晨3点的时间差
            next_run = now.replace(hour=3, minute=0, second=0, microsecond=0)
            if next_run <= now:
                # 如果已经过了今天的3点，则设为明天的3点
                next_run = next_run.replace(day=next_run.day + 1)
            
            sleep_seconds = (next_run - now).total_seconds()
            logger.info(f"下次缓存清理时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            
            await asyncio.sleep(sleep_seconds)
            await clean_cache_files()
            
        except Exception as e:
            logger.error(f"清理调度器错误: {str(e)}")
            # 发生错误时等待1小时后重试
            await asyncio.sleep(3600)

@driver.on_startup
async def startup():
    """启动时的检查"""
    check_ffmpeg_dependency()
    logger.info("ASMR插件已启动")
    
    # 启动清理任务
    asyncio.create_task(schedule_cleanup())
    logger.info("缓存清理调度器已启动，将在每日凌晨3:00执行清理")

@driver.on_shutdown  
async def shutdown():
    """关闭时清理"""
    logger.info("ASMR插件正在关闭...")