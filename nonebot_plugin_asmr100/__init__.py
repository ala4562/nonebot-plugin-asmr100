"""ASMR音声分享插件"""

import asyncio
from datetime import datetime, time, timedelta
from typing import Optional

from nonebot import require, logger, get_driver
from nonebot.plugin import PluginMetadata

require("nonebot_plugin_htmlrender")
require("nonebot_plugin_localstore")

import nonebot_plugin_localstore as store

from .config import Config, check_ffmpeg_dependency
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
    homepage="https://github.com/ala4562/nonebot-plugin-asmr100",
    config=Config,
    supported_adapters={"~onebot.v11"},
    extra={"author": "ala4562"},
)

__all__ = ["play", "search", "search_next"]

driver = get_driver()
cleanup_task: Optional[asyncio.Task] = None

async def clean_cache_files():
    """清理所有缓存文件和压缩包"""
    try:
        import shutil

        if not DATA_DIR.exists():
            return

        total_size = 0
        deleted_count = 0

        for rj_folder in DATA_DIR.iterdir():
            if rj_folder.is_dir():
                folder_size = sum(f.stat().st_size for f in rj_folder.rglob('*') if f.is_file())
                total_size += folder_size

                try:
                    await async_file_operation(shutil.rmtree, str(rj_folder))
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"删除文件夹失败 {rj_folder}: {str(e)}")

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
            next_run = datetime.combine(now.date(), time(3))
            if next_run <= now:
                next_run += timedelta(days=1)

            sleep_seconds = max(0, (next_run - now).total_seconds())
            logger.info(
                "下次缓存清理时间: %s",
                next_run.strftime('%Y-%m-%d %H:%M:%S'),
            )

            await asyncio.sleep(sleep_seconds)
            await clean_cache_files()

        except asyncio.CancelledError:
            logger.info("缓存清理调度器已取消")
            break
        except Exception as e:
            logger.error(f"清理调度器错误: {str(e)}")
            await asyncio.sleep(3600)

@driver.on_startup
async def startup():
    """启动时的检查"""
    check_ffmpeg_dependency()
    logger.info("ASMR插件已启动")

    global cleanup_task
    if cleanup_task is None or cleanup_task.done():
        cleanup_task = asyncio.create_task(schedule_cleanup())
    logger.info("缓存清理调度器已启动，将在每日凌晨3:00执行清理")

@driver.on_shutdown
async def shutdown():
    """关闭时清理"""
    logger.info("ASMR插件正在关闭...")

    global cleanup_task
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            logger.info("缓存清理调度器已停止")
