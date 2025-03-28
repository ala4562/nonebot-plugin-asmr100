"""搜索命令处理模块"""

import re
import traceback
from typing import Dict, Any

from nonebot.params import CommandArg
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, Message
from nonebot.log import logger

from .. import USER_SEARCH_STATES, USER_ERROR_COUNTS
from ..data_source import search_works, send_search_results
from ..utils import check_user_error_limit
from . import search, search_next

# 提取共同的搜索执行逻辑为一个函数
async def perform_search(bot: Bot, event: MessageEvent, keyword: str, page: int):
    """
    执行搜索逻辑
    
    参数:
        bot: Bot实例
        event: 消息事件
        keyword: 搜索关键词
        page: 页码
    """
    try:
        search_result = await search_works(keyword, page)
        await send_search_results(bot, event, search_result)
    except Exception as e:
        logger.error(f"搜索过程中出错: {str(e)}")
        logger.error(traceback.format_exc())
        await bot.send(event, f"搜索过程中出错: {str(e)}", at_sender=True)

@search.handle()
async def handle_search(bot: Bot, event: MessageEvent, state: T_State, arg: Message = CommandArg()):
    """处理搜音声命令"""
    """处理搜音声命令"""
    # 获取用户ID
    user_id = str(event.user_id)
    
    arg_text = arg.extract_plain_text().strip()
    arg = arg_text.split()
    if not arg:
        await search.send('请输入搜索关键词(空格或"/"分割不同tag)和搜索页数(可选)！比如"搜音声 伪娘 催眠 1"', at_sender=True)
        return
    
    # 处理关键词和页码
    if len(arg) == 1:
        # 将所有空格转换为%20，以支持空格分隔标签
        keyword = arg[0].replace(" ", "%20").replace("/", "%20")
        y = 1
    elif len(arg) >= 2:
        # 尝试从最后一个参数解析页码
        try:
            y = int(arg[-1])
            # 如果最后一个参数是页码，关键词就是除了最后一个之外的所有参数
            keyword = " ".join(arg[:-1]).replace(" ", "%20").replace("/", "%20")
        except ValueError:
            # 如果最后一个参数不是页码，所有参数都是关键词
            keyword = " ".join(arg).replace(" ", "%20").replace("/", "%20")
            y = 1
    
    # 重置用户错误计数
    USER_ERROR_COUNTS[user_id] = 0
    
    # 保存当前用户的搜索状态
    USER_SEARCH_STATES[user_id] = {
        "keyword": keyword,
        "page": y
    }
    
    await search.send(f"正在搜索音声{keyword.replace('%20', ' ')}，第{y}页！", at_sender=True)
    
    # 执行搜索逻辑
    await perform_search(bot, event, keyword, y)
    
@search_next.handle()
async def handle_search_next(bot: Bot, event: MessageEvent, state: T_State):
    """处理搜索下一页命令"""
    # 获取用户ID
    user_id = str(event.user_id)
    
    # 检查用户是否有搜索状态
    if user_id not in USER_SEARCH_STATES:
        await search_next.send("您还没有进行过搜索，请先使用\"搜音声\"命令", at_sender=True)
        return
    
    # 获取用户的搜索状态并增加页码
    search_state = USER_SEARCH_STATES[user_id]
    keyword = search_state["keyword"]
    next_page = search_state["page"] + 1
    
    # 更新搜索状态
    USER_SEARCH_STATES[user_id]["page"] = next_page
    
    # 重置用户错误计数
    USER_ERROR_COUNTS[user_id] = 0
    
    await search_next.send(f"正在搜索音声{keyword.replace('%20', ' ')}，第{next_page}页！", at_sender=True)
    
    # 执行搜索逻辑
    await perform_search(bot, event, keyword, next_page)