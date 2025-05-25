"""数据源和API交互模块"""

import os
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import aiohttp
from math import ceil

from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment

from .config import plugin_config
from .utils import async_file_operation
from nonebot_plugin_htmlrender import md_to_pic


async def get_work_info(rj_id: str) -> Dict[str, Any]:
    """获取音声作品信息"""
    headers = plugin_config.asmr_http_headers
    base_url = plugin_config.asmr_api_base_url
    timeout = plugin_config.asmr_api_timeout
    
    if rj_id.upper().startswith("RJ"):
        rj_id = rj_id[2:]
    
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{base_url}/workInfo/{rj_id}"
            res = await session.get(url, headers=headers, timeout=timeout)
            
            if res.status != 200:
                logger.error(f"获取音声信息失败，状态码: {res.status}")
                return {}
            
            return await res.json()
        except Exception as e:
            logger.error(f"获取音声信息时发生错误: {str(e)}")
            return {}

async def get_tracks(rj_id: str) -> Dict[str, Any]:
    """获取音声轨道列表"""
    headers = plugin_config.asmr_http_headers
    base_url = plugin_config.asmr_api_base_url
    timeout = plugin_config.asmr_api_timeout
    
    if rj_id.upper().startswith("RJ"):
        rj_id = rj_id[2:]
    
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{base_url}/tracks/{rj_id}"
            response = await session.get(url, headers=headers, timeout=timeout)
            
            if response.status != 200:
                logger.error(f"获取音轨失败，状态码: {response.status}")
                return {}
            
            return await response.json()
        except Exception as e:
            logger.error(f"获取音轨时发生错误: {str(e)}")
            return []

async def search_works(keyword: str, page: int = 1) -> Dict[str, Any]:
    """搜索音声作品"""
    headers = plugin_config.asmr_http_headers
    base_url = plugin_config.asmr_api_base_url
    timeout = plugin_config.asmr_api_timeout
    
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{base_url}/search/{keyword}?order=dl_count&sort=desc&page={page}&subtitle=0&includeTranslationWorks=true"
            res = await session.get(url, headers=headers, timeout=timeout)
            
            if res.status != 200:
                logger.error(f"搜索失败，状态码: {res.status}")
                return {"works": [], "pagination": {"totalCount": 0, "currentPage": page}}
            
            return await res.json()
        except Exception as e:
            logger.error(f"搜索过程中出错: {str(e)}")
            return {"works": [], "pagination": {"totalCount": 0, "currentPage": page}}

async def download_file(url: str, save_path: Path) -> Path:
    """下载文件到指定路径"""
    headers = plugin_config.asmr_http_headers
    
    if save_path.exists():
        return save_path
    
    try:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = save_path.with_suffix('.tmp')
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"下载文件时服务器返回错误: {response.status}")
                
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                
                # 创建空文件
                def create_file():
                    with open(temp_path, 'wb') as f:
                        pass
                
                await async_file_operation(create_file)
                
                def write_chunk(chunk):
                    with open(temp_path, 'ab') as f:
                        f.write(chunk)
                
                chunk_size = 1024 * 1024  # 1MB
                async for chunk in response.content.iter_chunked(chunk_size):
                    await async_file_operation(write_chunk, chunk)
                    downloaded += len(chunk)
                    
                    # 及时释放chunk内存
                    del chunk
                    
                    if downloaded % (10 * 1024 * 1024) < chunk_size and total_size > 0:
                        progress = (downloaded / total_size) * 100
                        logger.info(f"下载进度: {progress:.2f}% ({downloaded/(1024*1024):.2f}MB/{total_size/(1024*1024):.2f}MB)")
        
        await async_file_operation(os.rename, temp_path, save_path)
        return save_path
    
    except Exception as e:
        if 'temp_path' in locals() and temp_path.exists():
            try:
                await async_file_operation(os.remove, temp_path)
            except:
                pass
        raise e

async def send_search_results(bot: Bot, event: MessageEvent, r: Dict[str, Any]) -> None:
    """发送搜索结果"""
    if len(r.get("works", [])) == 0:
        if r.get("pagination", {}).get("totalCount", 0) == 0:
            await bot.send(event, "搜索结果为空", at_sender=True)
            return
        elif r.get("pagination", {}).get("currentPage", 1) > 1:
            count = int(r["pagination"]["totalCount"])
            max_pages = ceil(count/20)
            await bot.send(event, f"此搜索结果最多{max_pages}页", at_sender=True)
            return
    
    title = []
    rid = []
    imgs = []
    ars = []
    
    for result2 in r["works"]:
        title.append(result2["title"])
        ars.append(result2["name"])
        imgs.append(result2["mainCoverUrl"])
        ids = str(result2["id"])
        if len(ids) == 7 or len(ids) == 5:
            ids = "RJ0" + ids
        else:
            ids = "RJ" + ids
        rid.append(ids)
        
    msg2 = f'### <div align="center">搜索结果</div>\n' \
          f'| 封面 | 序号 | RJ号 |\n' \
          '| --- | --- | --- |\n'
    msg = ""
    for i in range(len(title)):
        msg += str(i+1) + ". 【" + rid[i] + "】 " + title[i] + "\n"
        msg2 += f'|<img width="250" src="{imgs[i]}"/> | {str(i+1)}. |【{rid[i]}】|\n'
    msg += "请发送听音声+RJ号+节目编号（可选）来下载要听的资源\n发送\"搜索下一页\"查看更多结果"
    
    try:
        output = await md_to_pic(md=msg2)
        await bot.send(event, MessageSegment.image(output), at_sender=True)
    except Exception as e:
        logger.error(f"生成图片失败: {str(e)}")
        await bot.send(event, "搜索结果：\n" + msg, at_sender=True)
    else:
        await bot.send(event, msg, at_sender=True)