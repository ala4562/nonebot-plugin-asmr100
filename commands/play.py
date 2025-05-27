"""播放命令处理模块"""

import re
import traceback
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from nonebot.params import CommandArg, ArgPlainText
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, Message, MessageSegment
from nonebot.log import logger
from nonebot_plugin_htmlrender import md_to_pic
import aiohttp

from ..states import USER_ERROR_COUNTS
from ..config import plugin_config
from ..utils import format_rj_id, sanitize_filename, detect_file_extension, generate_folder_letter, generate_unique_zip_filename
from ..data_source import get_work_info, download_file, get_tracks
from ..file_handler import (
    download_folder_files, 
    download_single_file_zip, 
    download_all_files, 
    safe_upload_file,
    )
from . import play

@play.handle()
async def handle_play(bot: Bot, event: MessageEvent, state: T_State, arg: Message = CommandArg()):
    """处理听音声命令"""
    user_id = str(event.user_id)
    USER_ERROR_COUNTS[user_id] = 0
    
    arg_text = arg.extract_plain_text().strip()
    if not arg_text:
        await play.finish("请输入正确的RJ号！", at_sender=True)
        return
    
    arg_parts = arg_text.split()
    raw_rj_id = arg_parts[0]
    
    if not raw_rj_id.upper().startswith("RJ"):
        await play.finish("输入的RJ号不符合格式，必须以RJ开头！", at_sender=True)
        return
    
    rj_id = format_rj_id(raw_rj_id)
    
    await play.send(f"正在查询音声信息 {rj_id}！", at_sender=True)
    
    # 参数解析
    folder_name = None
    track_index = None
    compress_single = False
    
    if len(arg_parts) > 1:
        second_arg = arg_parts[1]
        if second_arg.lower() == "all":
            track_index = "all"
        elif second_arg.lower() in ["zip", "压缩"]:
            track_index = 0
            compress_single = True
        else:
            # 检查是否是数字+压缩标识
            num_match = re.match(r'^(\d+)', second_arg)
            if num_match:
                track_index = int(num_match.group(1)) - 1
                if track_index < 0:
                    track_index = 0
                if "zip" in second_arg.lower() or "压缩" in second_arg:
                    compress_single = True
            else:
                folder_name = second_arg
    
    try:
        work_info = await get_work_info(rj_id)
        
        work_title = work_info.get("title")
        if not work_title:
            await play.finish("没有此音声信息或还没有资源", at_sender=True)
            return
        
        circle_name = work_info.get("name", "未知社团")
        cover_url = work_info.get("mainCoverUrl", "")
        
        from .. import DATA_DIR
        safe_rj_id = sanitize_filename(rj_id)
        rj_dir = DATA_DIR / safe_rj_id
        rj_dir.mkdir(exist_ok=True)
        
        tracks = await get_tracks(rj_id)
        
        if not tracks:
            await play.finish("获取音轨失败，请稍后再试", at_sender=True)
            return
        
        # 处理音轨数据
        keywords = []
        urls = []
        folders = {}
        folder_files = {}
        file_to_folder = {}
        
        async def process_item(item, folder_path=None):
            if item.get("type") == "audio":
                file_index = len(keywords)
                keywords.append(item.get("title", ""))
                urls.append(item.get("mediaDownloadUrl", ""))
                
                if folder_path:
                    file_to_folder[file_index] = folder_path
                    
                    if folder_path not in folder_files:
                        folder_files[folder_path] = []
                    folder_files[folder_path].append({
                        "index": file_index,
                        "title": item.get("title", ""),
                        "url": item.get("mediaDownloadUrl", ""),
                        "type": "audio"
                    })
            
            elif item.get("type") == "folder":
                current_folder_path = item.get("title", "") if not folder_path else f"{folder_path}/{item.get('title', '')}"
                
                if current_folder_path not in folders:
                    folders[current_folder_path] = []
                folders[current_folder_path].extend(item.get("children", []))
                
                for child in item.get("children", []):
                    await process_item(child, current_folder_path)
        
        for track_item in tracks:
            await process_item(track_item)
        
        if not keywords or not urls:
            await play.finish("未找到可下载的音频文件", at_sender=True)
            return
        
        # 保存状态
        state["keywords"] = keywords
        state["urls"] = urls
        state["rj_dir"] = str(rj_dir)
        state["title"] = work_title
        state["circle"] = circle_name
        state["cover_url"] = cover_url
        state["rj_id"] = rj_id
        state["folders"] = folders
        state["folder_files"] = folder_files
        
        # 处理文件夹下载请求
        if folder_name is not None:
            folder_found = False
            for folder in folders.keys():
                if folder_name.lower() in folder.lower():
                    folder_found = True
                    try:
                        await play.send(f"将下载文件夹 '{folder}' 中的所有文件", at_sender=True)
                        zip_path, zip_size_str = await download_folder_files(folders[folder], folder, str(rj_dir), rj_id)
                        
                        msg = await safe_upload_file(bot, event, zip_path, rj_id)
                        await play.send(msg, at_sender=True)
                        return
                    except Exception as e:
                        logger.error(f"下载文件夹内容时出错: {str(e)}")
                        await play.send(f"下载文件夹内容时出错: {str(e)}", at_sender=True)
                        return
            
            if not folder_found:
                await play.send(f"没有找到名为 '{folder_name}' 的文件夹，显示所有可用内容", at_sender=True)
        
        # 处理全部下载请求
        if track_index == "all":
            try:
                await play.send(f"将下载所有音轨并创建压缩包，共 {len(keywords)} 个文件", at_sender=True)
                zip_path, zip_size_str = await download_all_files(urls, keywords, str(rj_dir), rj_id)
                
                msg = await safe_upload_file(bot, event, zip_path, rj_id)
                await play.send(msg, at_sender=True)
                return
            except Exception as e:
                logger.error(f"下载所有文件时出错: {str(e)}")
                await play.send(f"下载或压缩文件时出错: {str(e)}", at_sender=True)
                return
        
        # 处理单个文件下载请求
        if track_index is not None and track_index != "all" and 0 <= track_index < len(keywords):
            await play.send(f"正在下载 {keywords[track_index]}，请稍候...", at_sender=True)
            try:
                extension = detect_file_extension(keywords[track_index])
                safe_filename = sanitize_filename(keywords[track_index])
                file_path = Path(rj_dir) / f"{safe_filename}{extension}"
                
                await download_file(urls[track_index], file_path)
                
                if compress_single:
                    await play.send(f"正在创建压缩包...", at_sender=True)
                    zip_path, zip_size_str = await download_single_file_zip(urls[track_index], keywords[track_index], str(rj_dir), rj_id, track_index)
                    
                    msg = await safe_upload_file(bot, event, zip_path, rj_id)
                    await play.send(msg, at_sender=True)
                else:
                    msg = await safe_upload_file(bot, event, str(file_path), rj_id, keywords[track_index], track_index)
                    await play.send(msg, at_sender=True)
                return
                
            except Exception as e:
                logger.error(f"下载单个文件时出错: {str(e)}")
                await play.send(f"下载或发送文件时出错: {str(e)}", at_sender=True)
                await play.send("将显示所有可用音频", at_sender=True)
        
        # 生成音声内容列表
        await generate_content_list(play, work_title, circle_name, cover_url, folders, folder_files, keywords, file_to_folder, state)
        
    except aiohttp.ClientError as e:
        logger.error(f"网络请求失败: {str(e)}")
        await play.finish("网络连接失败，请稍后再试", at_sender=True)
    except Exception as e:
        logger.error(f"处理失败: {str(e)}")
        logger.error(traceback.format_exc())
        await play.finish(f"获取音声信息或下载列表时出错: {str(e)}", at_sender=True)

async def generate_content_list(play_handler, title, circle, img, folders, folder_files, keywords, file_to_folder, state):
    """生成音声内容列表"""
    md_content = f'### <div align="center">音声内容列表</div>\n'
    md_content += f'|<img width="250" src="{img}"/> |{title}  社团名：{circle}|\n'
    md_content += f'| :---: | --- |\n'
    
    if folders:
        folder_list = list(folders.keys())
        md_content += f'| **序号** | **文件夹/文件** |\n'
        
        # 修复文件夹字母序号计算
        folder_letters = {}
        for folder_idx, folder_name in enumerate(folder_list):
            folder_letter = generate_folder_letter(folder_idx)
            folder_letters[folder_name] = folder_letter
            
            file_count = len(folder_files.get(folder_name, []))
            
            folder_display = folder_name
            folder_depth = folder_name.count('/')
            if folder_depth > 0:
                indent = "&nbsp;&nbsp;&nbsp;&nbsp;" * folder_depth
                folder_display = f"{indent}📁 {folder_name.split('/')[-1]}"
            else:
                folder_display = f"📁 {folder_name}"
                
            md_content += f'| **{folder_letter}** | **{folder_display}** ({file_count}个文件) |\n'
            
            if folder_name in folder_files:
                for file_info in folder_files[folder_name]:
                    file_indent = "&nbsp;&nbsp;&nbsp;&nbsp;" * (folder_depth + 1)
                    md_content += f'| {file_info["index"]+1} | {file_indent}↳ {file_info["title"]} |\n'
    
    state["folder_letters"] = folder_letters
    
    root_files = []
    for i, title in enumerate(keywords):
        if i not in file_to_folder:
            root_files.append({"index": i, "title": title})
    
    if root_files:
        if folders:
            md_content += f'| - | **不在文件夹中的文件** |\n'
        else:
            md_content += f'| **序号** | **文件** |\n'
        
        for file_info in root_files:
            md_content += f'| {file_info["index"]+1} | {file_info["title"]} |\n'
    
    # 默认使用图片模式，失败时使用文字模式
    try:
        img = await md_to_pic(md_content, width=600)
        await play_handler.send(MessageSegment.image(img), at_sender=True)
        await play_handler.send("回复数字下载对应文件，回复文件夹字母下载整个文件夹，回复 all 下载全部", at_sender=True)
    except Exception as e:
        logger.error(f"生成图片失败: {str(e)}")
        text_content = await generate_text_content(title, circle, folders, folder_files, keywords, file_to_folder, folder_letters)
        await play_handler.finish(text_content, at_sender=True)

async def generate_text_content(title, circle, folders, folder_files, keywords, file_to_folder, folder_letters):
    """生成纯文本内容"""
    content = f"🎵 音声: {title}\n👥 社团: {circle}\n"
    
    if folders:
        content += f"\n📂 文件夹列表:\n"
        for folder_name, folder_letter in folder_letters.items():
            file_count = len(folder_files.get(folder_name, []))
            folder_display = folder_name.split('/')[-1] if '/' in folder_name else folder_name
            content += f"{folder_letter}. 📁 {folder_display} ({file_count}个文件)\n"
    
    content += f"\n🎧 音频列表:\n"
    for i, keyword in enumerate(keywords):
        if i not in file_to_folder or len(keywords) <= 10:
            content += f"{i+1}. {keyword}\n"
    
    if len(keywords) > 10:
        content += f"... 还有 {len(keywords) - 10} 个文件\n"
    
    content += "\n💡 操作提示:\n"
    content += "• 回复数字下载对应文件\n"
    if folders:
        content += "• 回复文件夹字母下载整个文件夹\n"
    content += "• 回复 all 下载全部文件"
    
    return content

@play.got("track_choice")
async def handle_track_choice(bot: Bot, event: MessageEvent, state: T_State, choice: str = ArgPlainText("track_choice")):
    """处理音轨选择"""
    choice = choice.strip()
    
    keywords = state.get("keywords", [])
    urls = state.get("urls", [])
    rj_dir = state.get("rj_dir", "")
    rj_id = state.get("rj_id", "")
    folder_letters = state.get("folder_letters", {})
    folders = state.get("folders", {})
    folder_files = state.get("folder_files", {})
    
    # 处理文件夹字母选择
    if choice.upper() in folder_letters.values():
        for folder_name, folder_letter in folder_letters.items():
            if choice.upper() == folder_letter:
                try:
                    await play.send(f"将下载文件夹 '{folder_name}' 中的所有文件", at_sender=True)
                    zip_path, zip_size_str = await download_folder_files(folders[folder_name], folder_name, rj_dir, rj_id)
                    
                    msg = await safe_upload_file(bot, event, zip_path, rj_id)
                    await play.send(msg, at_sender=True)
                    return
                except Exception as e:
                    logger.error(f"下载文件夹内容时出错: {str(e)}")
                    await play.send(f"下载文件夹内容时出错: {str(e)}", at_sender=True)
                    return
    
    # 处理全部下载
    if choice.lower() == "all":
        try:
            await play.send(f"将下载所有音轨并创建压缩包，共 {len(keywords)} 个文件", at_sender=True)
            zip_path, zip_size_str = await download_all_files(urls, keywords, rj_dir, rj_id)
            
            msg = await safe_upload_file(bot, event, zip_path, rj_id)
            await play.send(msg, at_sender=True)
        except Exception as e:
            logger.error(f"下载所有文件时出错: {str(e)}")
            await play.send(f"下载或压缩文件时出错: {str(e)}", at_sender=True)
        return
    
    # 处理数字选择
    if choice.isdigit():
        track_index = int(choice) - 1
        if 0 <= track_index < len(keywords):
            state["selected_track"] = track_index
            state["selected_keyword"] = keywords[track_index]
            state["selected_url"] = urls[track_index]
            
            download_options = [
                "1. 直接发送",
                "2. 压缩包发送"
            ]
            
            options_text = f"🎵 已选择: {keywords[track_index]}\n\n"
            options_text += "📥 请选择下载方式:\n"
            options_text += "\n".join(download_options)
            
            await play.send(options_text, at_sender=True)
        else:
            await play.send("输入的序号超出范围", at_sender=True)
            return

@play.got("download_method")
async def handle_download_method(bot: Bot, event: MessageEvent, state: T_State, method: str = ArgPlainText("download_method")):
    """处理下载方法选择"""
    method = method.strip()
    
    track_index = state.get("selected_track")
    keyword = state.get("selected_keyword")
    url = state.get("selected_url")
    rj_dir = state.get("rj_dir")
    rj_id = state.get("rj_id")
    
    if track_index is None or not keyword or not url:
        await play.finish("会话状态丢失，请重新开始", at_sender=True)
        return
    
    await play.send(f"正在下载 {keyword}，请稍候...", at_sender=True)
    
    try:
        if method == "1":
            # 直接发送
            extension = detect_file_extension(keyword)
            safe_filename = sanitize_filename(keyword)
            file_path = Path(rj_dir) / f"{safe_filename}{extension}"
            
            await download_file(url, file_path)
            
            msg = await safe_upload_file(bot, event, str(file_path), rj_id, keyword, track_index)
            await play.send(msg, at_sender=True)
            
        elif method == "2":
            # 压缩包发送
            await play.send(f"正在创建压缩包...", at_sender=True)
            zip_path, zip_size_str = await download_single_file_zip(url, keyword, rj_dir, rj_id, track_index)
            
            msg = await safe_upload_file(bot, event, zip_path, rj_id)
            await play.send(msg, at_sender=True)
    except Exception as e:
        logger.error(f"下载或发送文件时出错: {str(e)}")
        await play.send(f"下载或发送文件时出错: {str(e)}", at_sender=True)