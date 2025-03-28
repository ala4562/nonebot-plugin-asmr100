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

from .. import USER_ERROR_COUNTS
from ..config import plugin_config
from ..utils import format_rj_id, sanitize_filename, check_user_error_limit
from ..data_source import get_work_info,download_file, get_tracks
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
    # 重置用户错误计数
    USER_ERROR_COUNTS[user_id] = 0
    
    arg = arg.extract_plain_text().strip().split()
    
    if not arg:
        await play.finish("请输入正确的RJ号！", at_sender=True)
        return
    
    raw_rj_id = arg[0]
    
    if not raw_rj_id.upper().startswith("RJ"):
        await play.finish("输入的RJ号不符合格式，必须以RJ开头！", at_sender=True)
        return
    
    rj_id = format_rj_id(raw_rj_id)
    
    await play.send(f"正在查询音声信息 {rj_id}！", at_sender=True)
    
    # 判断是否指定了文件夹
    folder_name = None
    track_index = None
    compress_single = False
    
    if len(arg) > 1:
        # 检查是否是"all"关键字
        if arg[1].lower() == "all":
            track_index = "all"
        # 检查是否是zip关键字
        elif arg[1].lower() in ["zip", "压缩"]:
            track_index = 0  # 默认下载第一个
            compress_single = True
        else:
            try:
                # 尝试解析为数字
                num_part = re.match(r'^(\d+)', arg[1])
                if num_part:
                    track_index = int(num_part.group(1)) - 1
                    if track_index < 0:
                        track_index = 0
                    
                    # 检查是否有压缩标志
                    if "zip" in arg[1].lower() or "压缩" in arg[1]:
                        compress_single = True
                else:
                    # 可能是文件夹名称
                    folder_name = arg[1]
            except ValueError:
                # 不是数字，视为文件夹名
                folder_name = arg[1]
    
    try:
        # 获取RJ基本信息
        work_info = await get_work_info(rj_id)
        
        try:
            name = work_info["title"]
        except KeyError:
            await play.finish("没有此音声信息或还没有资源", at_sender=True)
            return
        
        ar = work_info.get("name", "未知社团")
        img = work_info.get("mainCoverUrl", "")
        
        # 创建RJ专用目录
        safe_rj_id = sanitize_filename(rj_id)
        rj_dir = plugin_config.asmr_data_dir / safe_rj_id
        rj_dir.mkdir(exist_ok=True)
        
        # 获取音频列表
        tracks = await get_tracks(rj_id)
        
        if not tracks:
            await play.finish("获取音轨失败，请稍后再试", at_sender=True)
            return
        
        # 解析音轨信息部分需要修改，现在我们需要跟踪每个文件是否在文件夹中
        keywords = []
        urls = []
        folders = {}  # 文件夹名称 -> 文件列表
        folder_files = {}  # 保存每个文件夹包含的文件信息
        file_to_folder = {}  # 文件索引 -> 文件夹名称（用于跟踪文件所属文件夹）
        
        async def process_item(item, folder_path=None):
            if item["type"] == "audio":
                file_index = len(keywords)  # 当前文件的索引
                keywords.append(item["title"])
                urls.append(item["mediaDownloadUrl"])
                
                # 如果文件在文件夹中，记录这种关系
                if folder_path:
                    file_to_folder[file_index] = folder_path
                    
                    # 记录文件夹中的文件
                    if folder_path not in folder_files:
                        folder_files[folder_path] = []
                    folder_files[folder_path].append({
                        "index": file_index,
                        "title": item["title"],
                        "url": item["mediaDownloadUrl"]
                    })
            
            elif item["type"] == "folder":
                current_folder = item["title"]
                # 记录文件夹结构
                if current_folder not in folders:
                    folders[current_folder] = []
                folders[current_folder].extend(item.get("children", []))
                
                # 递归处理子文件夹和文件
                for child in item.get("children", []):
                    await process_item(child, current_folder)
        
        for result2 in tracks:
            await process_item(result2)
        
        if not keywords or not urls:
            await play.finish("未找到可下载的音频文件", at_sender=True)
            return
        
        # 保存状态
        state["keywords"] = keywords
        state["urls"] = urls
        state["rj_dir"] = str(rj_dir)
        state["title"] = name
        state["circle"] = ar
        state["cover_url"] = img
        state["rj_id"] = rj_id
        state["folders"] = folders
        
        # 如果指定了文件夹，下载该文件夹
        if folder_name is not None:
            # 检查文件夹是否存在
            folder_found = False
            for folder in folders.keys():
                if folder_name.lower() in folder.lower():
                    folder_found = True
                    try:
                        # 下载文件夹中的所有文件并压缩
                        await play.send(f"将下载文件夹 '{folder}' 中的所有文件", at_sender=True)
                        zip_path, zip_size_str = await download_folder_files(folders[folder], folder, str(rj_dir), rj_id)
                        
                        # 上传ZIP文件
                        success, msg = await safe_upload_file(bot, event, zip_path, rj_id)
                        await play.send(msg, at_sender=True)
                        return
                    except Exception as e:
                        await play.send(f"下载文件夹内容时出错: {str(e)}", at_sender=True)
                        return
            
            if not folder_found:
                await play.send(f"没有找到名为 '{folder_name}' 的文件夹，显示所有可用内容", at_sender=True)
        
        # 下载所有文件并压缩
        if track_index == "all":
            try:
                await play.send(f"将下载所有音轨并创建压缩包，共 {len(keywords)} 个文件", at_sender=True)
                zip_path, zip_size_str = await download_all_files(urls, keywords, str(rj_dir), rj_id)
                
                # 上传ZIP文件
                success, msg = await safe_upload_file(bot, event, zip_path, rj_id)
                await play.send(msg, at_sender=True)
                return
            except Exception as e:
                await play.send(f"下载或压缩文件时出错: {str(e)}", at_sender=True)
                return
        
        # 如果指定了音轨编号且有效，直接下载并发送
        if track_index is not None and track_index != "all" and 0 <= track_index < len(keywords):
            await play.send(f"正在下载 {keywords[track_index]}，请稍候...", at_sender=True)
            try:
                # 确定文件后缀名
                if ".wav" in keywords[track_index].lower():
                    extension = ".wav"
                elif ".flac" in keywords[track_index].lower():
                    extension = ".flac"
                elif ".ogg" in keywords[track_index].lower():
                    extension = ".ogg"
                elif ".m4a" in keywords[track_index].lower():
                    extension = ".m4a"
                else:
                    extension = ".mp3"
                
                # 使用原始文件名 - 只做基本的安全处理
                safe_filename = sanitize_filename(keywords[track_index])
                file_path = Path(state["rj_dir"]) / f"{safe_filename}{extension}"
                
                # 使用aiohttp下载
                await download_file(urls[track_index], file_path)
                
                if compress_single:
                    # 创建单个文件的压缩包
                    await play.send(f"正在创建压缩包...", at_sender=True)
                    zip_path, zip_size_str = await download_single_file_zip(urls[track_index], keywords[track_index], str(rj_dir), rj_id, track_index)
                    
                    # 上传ZIP文件
                    success, msg = await safe_upload_file(bot, event, zip_path, rj_id)
                    await play.send(msg, at_sender=True)
                else:
                    # 直接上传文件
                    success, msg = await safe_upload_file(bot, event, str(file_path), rj_id, keywords[track_index], track_index)
                    await play.send(msg, at_sender=True)
                return
                
            except Exception as e:
                await play.send(f"下载或发送文件时出错: {str(e)}", at_sender=True)
                await play.send("将显示所有可用音频", at_sender=True)
        
        # 准备显示可用内容 - 改进显示逻辑，为文件夹添加序号并缩进显示文件
        md_content = f'### <div align="center">音声内容列表</div>\n'
        md_content += f'|<img width="250" src="{img}"/> |{name}  社团名：{ar}|\n'
        md_content += f'| :---: | --- |\n'
        
        # 先显示文件夹及其内容
        if folders:
            folder_list = list(folders.keys())
            md_content += f'| **序号** | **文件夹/文件** |\n'
            
            # 为每个文件夹分配字母序号 (A, B, C...)
            for folder_idx, folder_name in enumerate(folder_list):
                folder_letter = chr(65 + folder_idx)  # 65是大写字母A的ASCII码
                if folder_idx >= 26:  # 如果超过26个文件夹，使用双字母
                    folder_letter = chr(64 + (folder_idx // 26)) + chr(65 + (folder_idx % 26))
                
                # 获取文件夹中的文件数量
                file_count = 0
                if folder_name in folder_files:
                    file_count = len(folder_files[folder_name])
                
                md_content += f'| **{folder_letter}** | 📁 **{folder_name}** ({file_count}个文件) |\n'
                
                # 缩进显示文件夹中的文件
                if folder_name in folder_files:
                    for file_info in folder_files[folder_name]:
                        md_content += f'| {file_info["index"]+1} | &nbsp;&nbsp;&nbsp;&nbsp;↳ {file_info["title"]} |\n'
            
            # 保存文件夹序号映射
            state["folder_letters"] = {folder_list[i]: chr(65 + i) for i in range(min(len(folder_list), 26))}
            for i in range(26, len(folder_list)):
                state["folder_letters"][folder_list[i]] = chr(64 + (i // 26)) + chr(65 + (i % 26))
            
            # 保存文件夹名称到内容的映射
            state["folder_files"] = folder_files
        
        # 显示不在文件夹中的音轨
        root_files = []
        for i, title in enumerate(keywords):
            if i not in file_to_folder:
                root_files.append({"index": i, "title": title})
        
        if root_files:
            if folders:  # 如果有文件夹，添加一个分隔标题
                md_content += f'| - | **不在文件夹中的文件** |\n'
            else:  # 如果没有文件夹，添加一个标题行
                md_content += f'| **序号** | **音轨名称** |\n'
                
            for file_info in root_files:
                md_content += f'| {file_info["index"]+1} | {file_info["title"]} |\n'
        
        try:
            output = await md_to_pic(md=md_content)
            await play.send(MessageSegment.image(output), at_sender=True)
        except Exception as e:
            # 发送文本版本
            text_content = f"【{rj_id}】{name} - {ar}\n\n"
            
            if folders:
                folder_list = list(folders.keys())
                text_content += "文件夹列表：\n"
                
                # 使用相同的字母序号系统
                for folder_idx, folder_name in enumerate(folder_list):
                    folder_letter = chr(65 + folder_idx)
                    if folder_idx >= 26:
                        folder_letter = chr(64 + (folder_idx // 26)) + chr(65 + (folder_idx % 26))
                    
                    file_count = 0
                    if folder_name in folder_files:
                        file_count = len(folder_files[folder_name])
                    
                    text_content += f"{folder_letter}. 📁 {folder_name} ({file_count}个文件)\n"
                    
                    # 缩进显示文件夹中的文件
                    if folder_name in folder_files:
                        for file_info in folder_files[folder_name]:
                            text_content += f"    {file_info['index']+1}. {file_info['title']}\n"
                
                text_content += "\n"
            
            # 不在文件夹中的文件
            if root_files:
                if folders:
                    text_content += "不在文件夹中的文件:\n"
                else:
                    text_content += "音轨列表:\n"
                    
                for file_info in root_files:
                    text_content += f"{file_info['index']+1}. {file_info['title']}\n"
            
            await play.send(text_content, at_sender=True)
        
        # 简化操作提示，添加文件夹字母序号说明
        if folders:
            await play.send("请发送：数字序号(下载单曲)/数字+zip(压缩下载)/全部(打包所有)/字母序号(打包指定文件夹)", at_sender=True)
        else:
            await play.send("请发送：序号(下载单曲)/序号+zip(压缩下载)/全部(打包所有)", at_sender=True)
        
    except Exception as e:
        logger.error(f"处理失败: {str(e)}")
        logger.error(traceback.format_exc())
        await play.finish(f"获取音声信息或下载列表时出错: {str(e)}", at_sender=True)

@play.got("track_choice")
async def handle_track_choice(bot: Bot, event: MessageEvent, state: T_State, choice: str = ArgPlainText("track_choice")):
    """处理用户选择"""
    user_id = str(event.user_id)
    try:
        # 检查是否要下载所有文件
        if choice.strip() in ["全部", "all", "ALL", "All"]:
            await play.send(f"将下载所有音轨并创建压缩包，请稍候...", at_sender=True)
            try:
                urls = state["urls"]
                keywords = state["keywords"]
                rj_dir = state["rj_dir"]
                rj_id = state.get("rj_id", "")
                
                zip_path, zip_size_str = await download_all_files(urls, keywords, rj_dir, rj_id)
                
                # 上传ZIP文件
                success, msg = await safe_upload_file(bot, event, zip_path, rj_id)
                await play.send(msg, at_sender=True)
                return
            except Exception as e:
                await play.send(f"下载或压缩文件时出错: {str(e)}", at_sender=True)
                return
                
        # 检查是否是文件夹字母序号
        folder_letters = state.get("folder_letters", {})
        if folder_letters:
            # 将输入转换为大写以便匹配
            choice_upper = choice.strip().upper()
            
            # 反向查找，根据字母找到文件夹名称
            selected_folder = None
            for folder_name, letter in folder_letters.items():
                if letter == choice_upper:
                    selected_folder = folder_name
                    break
            
            if selected_folder:
                folder_files = state.get("folder_files", {})
                rj_dir = state["rj_dir"]
                rj_id = state.get("rj_id", "")
                
                if selected_folder in folder_files and folder_files[selected_folder]:
                    try:
                        # 创建文件夹数据结构，用于download_folder_files函数
                        folder_items = []
                        for file_info in folder_files[selected_folder]:
                            folder_items.append({
                                "type": "audio",
                                "mediaDownloadUrl": file_info["url"],
                                "title": file_info["title"]
                            })
                        
                        await play.send(f"将下载文件夹 '{selected_folder}' 中的 {len(folder_items)} 个文件", at_sender=True)
                        zip_path, zip_size_str = await download_folder_files(folder_items, selected_folder, rj_dir, rj_id)
                        
                        # 上传ZIP文件
                        success, msg = await safe_upload_file(bot, event, zip_path, rj_id)
                        await play.send(msg, at_sender=True)
                        return
                    except Exception as e:
                        await play.send(f"下载文件夹内容时出错: {str(e)}", at_sender=True)
                        return
                
        # 检查是否是文件夹名称
        folders = state.get("folders", {})
        if folders:
            for folder_name in folders.keys():
                if choice.strip().lower() in folder_name.lower():
                    rj_dir = state["rj_dir"]
                    rj_id = state.get("rj_id", "")
                    
                    try:
                        # 下载文件夹内容并创建压缩包
                        await play.send(f"将下载文件夹 '{folder_name}' 中的文件", at_sender=True)
                        zip_path, zip_size_str = await download_folder_files(folders[folder_name], folder_name, rj_dir, rj_id)
                        
                        # 上传ZIP文件
                        success, msg = await safe_upload_file(bot, event, zip_path, rj_id)
                        await play.send(msg, at_sender=True)
                        return
                    except Exception as e:
                        await play.send(f"下载文件夹内容时出错: {str(e)}", at_sender=True)
                        return
        
        # 检查是否为数字+zip格式（例如"3 zip"或"3zip"）
        zip_match = re.match(r'^(\d+)[\s_-]*(zip|压缩|打包)$', choice.strip())
        if zip_match:
            index = int(zip_match.group(1)) - 1
            urls = state["urls"]
            keywords = state["keywords"]
            rj_dir = state["rj_dir"]
            rj_id = state.get("rj_id", "")
            
            if not (0 <= index < len(urls)):
                # 检查错误次数
                if not check_user_error_limit(user_id, increment=True):
                    # 错误次数过多，不再回复
                    await play.finish()
                    return
                    
                await play.reject(f"请发送正确的数字 (1-{len(urls)}) 或发送\"全部\"下载所有文件")
                return
            
            url = urls[index]
            title = keywords[index]
            
            await play.send(f"正在下载 {title} 并创建压缩包，请稍候...", at_sender=True)
            
            try:
                # 下载并创建ZIP
                zip_path, zip_size_str = await download_single_file_zip(url, title, rj_dir, rj_id, index)
                
                # 上传ZIP文件
                success, msg = await safe_upload_file(bot, event, zip_path, rj_id)
                await play.send(msg, at_sender=True)
                return
            except Exception as e:
                await play.finish(f"下载或压缩文件时出错: {str(e)}", at_sender=True)
                return
        
        # 否则按照序号下载单个文件
        try:
            index = int(choice) - 1
            urls = state["urls"]
            keywords = state["keywords"]
            rj_dir = state["rj_dir"]
            rj_id = state.get("rj_id", "")
            
            if not (0 <= index < len(urls)):
                # 检查错误次数
                if not check_user_error_limit(user_id, increment=True):
                    # 错误次数过多，不再回复
                    await play.finish()
                    return
                
                await play.reject(f"请发送正确的数字 (1-{len(urls)}) 或发送\"全部\"下载所有文件")
                return
            
            # 重置错误计数
            USER_ERROR_COUNTS[user_id] = 0
            
            # 询问用户是否需要压缩
            state["selected_index"] = index
            state["selected_url"] = urls[index]
            state["selected_title"] = keywords[index]
            
            await play.send(f"已选择: {keywords[index]}\n请选择下载方式:\n1. 直接下载\n2. 压缩下载（带密码）", at_sender=True)
            
        except ValueError:
            # 检查错误次数
            if not check_user_error_limit(user_id, increment=True):
                # 错误次数过多，不再回复
                await play.finish()
                return
                
            await play.reject("请发送正确的数字、文件夹名或发送\"全部\"下载所有文件")
    except Exception as e:
        logger.error(f"处理选择时出错: {str(e)}")
        logger.error(traceback.format_exc())
        await play.finish(f"处理选择时出错: {str(e)}", at_sender=True)

@play.got("download_method")
async def handle_download_method(bot: Bot, event: MessageEvent, state: T_State, method: str = ArgPlainText("download_method")):
    """处理下载方式选择"""
    user_id = str(event.user_id)
    
    # 如果没有选择索引，表示这是第一次输入，直接返回
    if "selected_index" not in state:
        return
    
    try:
        index = state["selected_index"]
        url = state["selected_url"]
        title = state["selected_title"]
        rj_dir = state["rj_dir"]
        rj_id = state.get("rj_id", "")
        
        # 根据用户选择的方式处理
        if method.strip() in ["2", "zip", "压缩", "打包"]:
            # 压缩下载
            await play.send(f"正在下载 {title} 并创建压缩包，请稍候...", at_sender=True)
            
            try:
                # 下载并创建ZIP
                zip_path, zip_size_str = await download_single_file_zip(url, title, rj_dir, rj_id, index)
                
                # 上传ZIP文件
                success, msg = await safe_upload_file(bot, event, zip_path, rj_id)
                await play.send(msg, at_sender=True)
            except Exception as e:
                await play.finish(f"下载或压缩文件时出错: {str(e)}", at_sender=True)
        else:
            # 直接下载
            await play.send(f"正在下载 {title}，请稍候...", at_sender=True)

            try:
                # 确定文件后缀名
                if ".wav" in title.lower():
                    extension = ".wav"
                elif ".flac" in title.lower():
                    extension = ".flac"
                elif ".ogg" in title.lower():
                    extension = ".ogg"
                elif ".m4a" in title.lower():
                    extension = ".m4a"
                else:
                    extension = ".mp3"
                
                # 使用原始文件名 - 只做基本的安全处理
                safe_filename = sanitize_filename(title)
                file_path = Path(rj_dir) / f"{safe_filename}{extension}"
                
                # 使用aiohttp下载
                await download_file(url, file_path)
                
                # 使用安全上传函数
                success, msg = await safe_upload_file(bot, event, str(file_path), rj_id, title, index)
                await play.send(msg, at_sender=True)
            except Exception as e:
                logger.error(f"下载或发送文件时出错: {str(e)}")
                logger.error(traceback.format_exc())
                await play.finish(f"下载或发送文件时出错: {str(e)}", at_sender=True)
    except Exception as e:
        logger.error(f"处理下载方式时出错: {str(e)}")
        if check_user_error_limit(user_id, increment=True):
            await play.reject("请选择正确的下载方式: 1. 直接下载 或 2. 压缩下载")
        else:
            # 错误次数过多，不再回复
            await play.finish()