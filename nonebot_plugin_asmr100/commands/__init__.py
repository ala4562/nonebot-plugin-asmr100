"""命令处理模块"""

from nonebot import on_command
from nonebot.plugin import require

# 注册命令
play = on_command("听音声", block=True, priority=5)
search = on_command("搜音声", block=True, priority=5)
search_next = on_command("搜索下一页", block=True, priority=5)

__all__ = ["play", "search", "search_next"]