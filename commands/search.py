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

async def perform_search(bot: Bot, event: MessageEvent, keyword: str, page: int):
    """执行搜索操作"""
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
    user_id = str(event.user_id)
    
    arg_text = arg.extract_plain_text().strip()
    arg = arg_text.split()
    if not arg:
        await search.send('请输入搜索关键词(空格或"/"分割不同tag)和搜索页数(可选)！比如"搜音声 伪娘 催眠 1"', at_sender=True)
        return
    
    if len(arg) == 1:
        keyword = arg[0].replace(" ", "%20").replace("/", "%20")
        y = 1
    elif len(arg) >= 2:
        try:
            y = int(arg[-1])
            keyword = " ".join(arg[:-1]).replace(" ", "%20").replace("/", "%20")
        except ValueError:
            keyword = " ".join(arg).replace(" ", "%20").replace("/", "%20")
            y = 1
    
    USER_ERROR_COUNTS[user_id] = 0
    
    USER_SEARCH_STATES[user_id] = {
        "keyword": keyword,
        "page": y
    }
    
    await search.send(f"正在搜索音声{keyword.replace('%20', ' ')}，第{y}页！", at_sender=True)
    
    await perform_search(bot, event, keyword, y)
    
@search_next.handle()
async def handle_search_next(bot: Bot, event: MessageEvent, state: T_State):
    """处理搜索下一页命令"""
    user_id = str(event.user_id)
    
    if user_id not in USER_SEARCH_STATES:
        await search_next.send("您还没有进行过搜索，请先使用\"搜音声\"命令", at_sender=True)
        return
    
    search_state = USER_SEARCH_STATES[user_id]
    keyword = search_state["keyword"]
    next_page = search_state["page"] + 1
    
    USER_SEARCH_STATES[user_id]["page"] = next_page
    USER_ERROR_COUNTS[user_id] = 0
    
    await search_next.send(f"正在搜索音声{keyword.replace('%20', ' ')}，第{next_page}页！", at_sender=True)
    
    await perform_search(bot, event, keyword, next_page)