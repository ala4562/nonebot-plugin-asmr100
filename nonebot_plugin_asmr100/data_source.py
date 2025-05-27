"""数据源和API交互模块"""

import os
import aiohttp
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, Union
from math import ceil

from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, MessageSegment
from nonebot_plugin_htmlrender import md_to_pic

from .config import plugin_config
from .utils import async_file_operation

# 配置常量
CHUNK_SIZE = 1024 * 1024  # 1MB
PROGRESS_REPORT_INTERVAL = 10 * 1024 * 1024  # 10MB

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
            async with session.get(url, headers=headers, timeout=timeout) as res:
                if res.status != 200:
                    logger.error(f"获取音声信息失败，状态码: {res.status}")
                    return {}
                
                return await res.json()
        except aiohttp.ClientError as e:
            logger.error(f"网络请求错误: {str(e)}")
            return {}
        except Exception as e:
            logger.error(f"获取音声信息时发生未知错误: {str(e)}")
            return {}

async def get_tracks(rj_id: str) -> List[Dict[str, Any]]:
    """获取音声轨道列表"""
    headers = plugin_config.asmr_http_headers
    base_url = plugin_config.asmr_api_base_url
    timeout = plugin_config.asmr_api_timeout
    
    if rj_id.upper().startswith("RJ"):
        rj_id = rj_id[2:]
    
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{base_url}/tracks/{rj_id}"
            async with session.get(url, headers=headers, timeout=timeout) as response:
                if response.status != 200:
                    logger.error(f"获取音轨失败，状态码: {response.status}")
                    return []
                
                result = await response.json()
                # 确保返回列表格式
                if isinstance(result, list):
                    return result
                elif isinstance(result, dict) and 'tracks' in result:
                    return result['tracks']
                else:
                    return []
        except aiohttp.ClientError as e:
            logger.error(f"网络请求错误: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"获取音轨时发生未知错误: {str(e)}")
            return []

async def search_works(keyword: str, page: int = 1) -> Dict[str, Any]:
    """搜索音声作品"""
    headers = plugin_config.asmr_http_headers
    base_url = plugin_config.asmr_api_base_url
    timeout = plugin_config.asmr_api_timeout
    
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{base_url}/search/{keyword}?order=dl_count&sort=desc&page={page}&subtitle=0&includeTranslationWorks=true"
            async with session.get(url, headers=headers, timeout=timeout) as res:
                if res.status != 200:
                    logger.error(f"搜索失败，状态码: {res.status}")
                    return {"works": [], "pagination": {"totalCount": 0, "currentPage": page}}
                
                return await res.json()
        except aiohttp.ClientError as e:
            logger.error(f"搜索网络请求错误: {str(e)}")
            return {"works": [], "pagination": {"totalCount": 0, "currentPage": page}}
        except Exception as e:
            logger.error(f"搜索过程中出错: {str(e)}")
            return {"works": [], "pagination": {"totalCount": 0, "currentPage": page}}

async def download_file(url: str, save_path: Path) -> Path:
    """下载文件到指定路径"""
    headers = plugin_config.asmr_http_headers
    
    if save_path.exists():
        return save_path
    
    temp_path = save_path.with_suffix('.tmp')
    
    try:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=f"下载文件时服务器返回错误: {response.status}"
                    )
                
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                
                def create_file():
                    with open(temp_path, 'wb') as f:
                        pass
                
                await async_file_operation(create_file)
                
                def write_chunk(chunk):
                    with open(temp_path, 'ab') as f:
                        f.write(chunk)
                
                async for chunk in response.content.iter_chunked(CHUNK_SIZE):
                    await async_file_operation(write_chunk, chunk)
                    downloaded += len(chunk)
                    
                    del chunk
                    
                    if downloaded % PROGRESS_REPORT_INTERVAL < CHUNK_SIZE and total_size > 0:
                        progress = (downloaded / total_size) * 100
                        logger.info(f"下载进度: {progress:.2f}% ({downloaded/(1024*1024):.2f}MB/{total_size/(1024*1024):.2f}MB)")
        
        await async_file_operation(os.rename, temp_path, save_path)
        return save_path
    
    except aiohttp.ClientError as e:
        logger.error(f"下载网络错误: {str(e)}")
        if temp_path.exists():
            try:
                await async_file_operation(os.remove, temp_path)
            except OSError:
                pass
        raise e
    except OSError as e:
        logger.error(f"文件操作错误: {str(e)}")
        if temp_path.exists():
            try:
                await async_file_operation(os.remove, temp_path)
            except OSError:
                pass
        raise e
    except Exception as e:
        logger.error(f"下载未知错误: {str(e)}")
        if temp_path.exists():
            try:
                await async_file_operation(os.remove, temp_path)
            except OSError:
                pass
        raise e

async def send_search_results(bot: Bot, event: MessageEvent, r: Dict[str, Any]) -> None:
    """发送搜索结果"""
    works = r.get("works", [])
    pagination = r.get("pagination", {})
    
    if not works:
        total_count = pagination.get("totalCount", 0)
        if total_count == 0:
            await bot.send(event, "搜索结果为空", at_sender=True)
            return
        elif pagination.get("currentPage", 1) > 1:
            max_pages = ceil(total_count / 20)
            await bot.send(event, f"此搜索结果最多{max_pages}页", at_sender=True)
            return
    
    title = []
    rid = []
    imgs = []
    ars = []
    
    for result in works:
        title.append(result.get("title", "未知标题"))
        ars.append(result.get("name", "未知社团"))
        imgs.append(result.get("mainCoverUrl", ""))
        
        work_id = str(result.get("id", ""))
        if len(work_id) == 7 or len(work_id) == 5:
            work_id = "RJ0" + work_id
        else:
            work_id = "RJ" + work_id
        rid.append(work_id)
        
    md_content = f'### <div align="center">搜索结果</div>\n' \
                f'| 封面 | 序号 | RJ号 |\n' \
                '| --- | --- | --- |\n'
    
    text_msg = ""
    for i in range(len(title)):
        text_msg += f"{i+1}. 【{rid[i]}】 {title[i]}\n"
        md_content += f'|<img width="250" src="{imgs[i]}"/> | {i+1}. |【{rid[i]}】|\n'
    
    text_msg += "请发送听音声+RJ号+节目编号（可选）来下载要听的资源\n发送\"搜索下一页\"查看更多结果"
    
    try:
        output = await md_to_pic(md=md_content)
        await bot.send(event, MessageSegment.image(output), at_sender=True)
        await bot.send(event, text_msg, at_sender=True)
    except Exception as e:
        logger.error(f"生成图片失败: {str(e)}")
        await bot.send(event, f"搜索结果：\n{text_msg}", at_sender=True)