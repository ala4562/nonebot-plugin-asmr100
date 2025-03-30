"""
nonebot-plugin-asmr100
~~~~~~~~~~~~~~~~~~~~

一个用于在QQ群中分享ASMR音声的NoneBot2插件
"""

import os
from pathlib import Path

from nonebot import require, logger

# 确保依赖已安装
require("nonebot_plugin_htmlrender")
require("nonebot_plugin_localstore")

# 导入这些插件提供的功能
import nonebot_plugin_localstore as store

from .config import Config, plugin_config, check_dependencies

# 全局状态存储
USER_SEARCH_STATES = {}
USER_ERROR_COUNTS = {}

# 使用 localstore 获取数据目录
DATA_DIR = store.get_plugin_data_dir()
DATA_DIR.mkdir(parents=True, exist_ok=True)
logger.info(f"ASMR100 插件数据目录: {DATA_DIR}")

# 检查依赖
check_dependencies()

# 现在导入命令模块 - 在全局变量定义之后
from .commands.play import play
from .commands.search import search, search_next

__plugin_meta__ = PluginMetadata(
    name="asmr100",
    description="能在群里听音声，支持下载后发送文件",
    usage='''发送"听音声"+RJxxxxx +编号(可选)来下载并发送音声文件; 
发送"搜音声"+关键词(用空格或"/"分割不同tag) +页数(可选)来搜索音声;
发送"听音声"+RJxxxxx +目录名称 来下载指定文件夹内的所有音声并压缩''',
    type="application",
    homepage="https://github.com/ala4562/nonebot-plugin-asmr100",
    config=Config,
    supported_adapters={"~onebot.v11"},
)

# 导出模块内容
__all__ = ["play", "search", "search_next"]