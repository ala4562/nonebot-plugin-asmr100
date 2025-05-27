"""文件处理和下载模块"""

import os
import re
import tempfile
import shutil
import zipfile
import asyncio
from pathlib import Path
from typing import List, Tuple, Optional

from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, GroupMessageEvent

from .config import plugin_config
from .utils import (
    sanitize_filename, 
    detect_file_extension, 
    get_file_size_str, 
    generate_unique_zip_filename,
    async_file_operation,
    should_convert_to_mp3
)

async def convert_to_mp3(audio_file_path: str) -> str:
    """将音频文件转换为MP3格式"""
    try:
        if audio_file_path.lower().endswith('.mp3'):
            return audio_file_path
        
        mp3_file_path = os.path.splitext(audio_file_path)[0] + '.mp3'
        
        if os.path.exists(mp3_file_path):
            return mp3_file_path
        
        process = await asyncio.create_subprocess_exec(
            'ffmpeg', '-i', audio_file_path, '-vn', '-ar', '44100', '-ac', '2', '-b:a', '192k', mp3_file_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            if os.path.exists(audio_file_path) and os.path.exists(mp3_file_path):
                try:
                    await async_file_operation(os.remove, audio_file_path)
                except OSError:
                    pass
            return mp3_file_path
        else:
            logger.warning(f"ffmpeg转换失败，使用原文件: {stderr.decode()}")
            return audio_file_path
    except FileNotFoundError:
        logger.warning("ffmpeg未找到，跳过音频转换")
        return audio_file_path
    except Exception as e:
        logger.error(f"转换过程中出错: {str(e)}")
        return audio_file_path

async def create_secure_zip(file_paths: List[str], zip_path: str, password: Optional[str] = None) -> str:
    """创建加密的ZIP文件"""
    if password is None:
        password = plugin_config.asmr_zip_password
        
    temp_zip_path = zip_path + ".temp.zip"
        
    try:
        def create_zip():
            with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in file_paths:
                    if os.path.exists(file_path):
                        original_filename = os.path.basename(file_path)
                        zipf.write(file_path, original_filename)
        
        await async_file_operation(create_zip)
        
        # 尝试使用外部工具加密
        encrypted_success = False
        
        try:
            # 尝试使用7z
            encrypted_temp_path = zip_path + ".encrypted.7z"
            process = await asyncio.create_subprocess_exec(
                '7z', 'a', '-p' + password, encrypted_temp_path, temp_zip_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and os.path.exists(encrypted_temp_path):
                await async_file_operation(shutil.move, encrypted_temp_path, zip_path)
                await async_file_operation(os.remove, temp_zip_path)
                encrypted_success = True
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.warning(f"7z加密失败: {str(e)}")
        
        if not encrypted_success:
            try:
                # 尝试使用zip命令
                encrypted_temp_path = zip_path + ".encrypted.zip"
                process = await asyncio.create_subprocess_exec(
                    'zip', '-P', password, encrypted_temp_path, temp_zip_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0 and os.path.exists(encrypted_temp_path):
                    await async_file_operation(shutil.move, encrypted_temp_path, zip_path)
                    await async_file_operation(os.remove, temp_zip_path)
                    encrypted_success = True
            except FileNotFoundError:
                pass
            except Exception as e:
                logger.warning(f"zip加密失败: {str(e)}")
        
        
        if not encrypted_success:
            try:
                import pyminizip
                pyminizip.compress(temp_zip_path, zip_path, password, 5)
                await async_file_operation(os.remove, temp_zip_path)
                encrypted_success = True
            except ImportError:
                logger.warning("pyminizip未安装，使用无加密ZIP")
            except Exception as e:
                logger.warning(f"pyminizip加密失败: {str(e)}")
        
        
        if not encrypted_success:
            await async_file_operation(shutil.move, temp_zip_path, zip_path)
        
        if not os.path.exists(zip_path):
            raise Exception("ZIP文件创建失败")
        
        return zip_path
        
    except Exception as e:
        # 清理临时文件
        temp_path = temp_zip_path
        if os.path.exists(temp_path):
            try:
                await async_file_operation(os.remove, temp_path)
            except OSError:
                pass
        raise e

async def download_folder_files(folder_items: List[dict], folder_name: str, rj_dir: str, rj_id: str) -> Tuple[str, str]:
    """下载指定文件夹中的所有音频文件并创建ZIP"""
    downloaded_files = []
    
    try:
        clean_folder_name = folder_name.replace('/', '_').replace('\\', '_')
        folder_path = Path(rj_dir) / sanitize_filename(clean_folder_name)
        folder_path.mkdir(exist_ok=True)
        
        async def process_items(items, current_path):
            nonlocal downloaded_files
            
            for item in items:
                if item.get("type") == "audio":
                    url = item.get("mediaDownloadUrl") or item.get("url")
                    title = item.get("title", "")
                    
                    if not url or not title:
                        continue
                    
                    extension = detect_file_extension(title)
                    safe_filename = sanitize_filename(title)
                    file_path = current_path / f"{safe_filename}{extension}"
                    
                    try:
                        from .data_source import download_file
                        await download_file(url, file_path)
                        
                        original_path = str(file_path)
                        # 多文件下载时，只转换音频为MP3（不包括视频）
                        if should_convert_to_mp3(title, is_single_file=False):
                            mp3_path = await convert_to_mp3(original_path)
                            if mp3_path != original_path:
                                file_path = Path(mp3_path)
                        
                        downloaded_files.append(str(file_path))
                    except Exception as e:
                        logger.error(f"下载文件失败 {title}: {str(e)}")
                
                elif item.get("type") == "folder" and "children" in item:
                    sub_folder_name = sanitize_filename(item.get("title", ""))
                    sub_folder_path = current_path / sub_folder_name
                    sub_folder_path.mkdir(exist_ok=True)
                    
                    await process_items(item["children"], sub_folder_path)
        
        await process_items(folder_items, folder_path)
        
        if downloaded_files:
            display_name = folder_name.split('/')[-1] if '/' in folder_name else folder_name
            zip_filename = generate_unique_zip_filename(rj_id, f"folder_{sanitize_filename(display_name)}")
            zip_path = os.path.join(rj_dir, zip_filename)
            
            await create_secure_zip(downloaded_files, zip_path)
            
            zip_size = os.path.getsize(zip_path)
            zip_size_str = get_file_size_str(zip_size)
            
            return zip_path, zip_size_str
        else:
            raise Exception("没有成功下载任何文件")
    except Exception as e:
        logger.error(f"下载文件夹内容时出错: {str(e)}")
        raise e

async def download_single_file_zip(url: str, title: str, rj_dir: str, rj_id: str, track_index: int) -> Tuple[str, str]:
    """下载单个音频文件并创建ZIP（不转换格式）"""
    try:
        extension = detect_file_extension(title)
        safe_filename = sanitize_filename(title)
        file_path = Path(rj_dir) / f"{safe_filename}{extension}"
        
        from .data_source import download_file
        await download_file(url, file_path)
        
        
        zip_filename = generate_unique_zip_filename(rj_id, f"single_{track_index}")
        zip_path = os.path.join(rj_dir, zip_filename)
        
        await create_secure_zip([str(file_path)], zip_path)
        
        zip_size = os.path.getsize(zip_path)
        zip_size_str = get_file_size_str(zip_size)
        
        return zip_path, zip_size_str
    except Exception as e:
        logger.error(f"下载单个文件时出错: {str(e)}")
        raise e

async def download_all_files(urls: List[str], keywords: List[str], rj_dir: str, rj_id: str) -> Tuple[str, str]:
    """下载所有音频文件并创建ZIP"""
    downloaded_files = []
    
    try:
        for index, (url, title) in enumerate(zip(urls, keywords)):            
            extension = detect_file_extension(title)
            safe_filename = sanitize_filename(title)
            file_path = Path(rj_dir) / f"{safe_filename}{extension}"
            
            try:
                from .data_source import download_file
                await download_file(url, file_path)
                
                original_path = str(file_path)
                # 多文件下载时，只转换音频为MP3（不包括视频）
                if should_convert_to_mp3(title, is_single_file=False):
                    mp3_path = await convert_to_mp3(original_path)
                    if mp3_path != original_path:
                        file_path = Path(mp3_path)
                
                downloaded_files.append(str(file_path))
            except Exception as e:
                logger.error(f"下载文件失败 {title}: {str(e)}")
        
        if downloaded_files:
            zip_filename = generate_unique_zip_filename(rj_id, "all")
            zip_path = os.path.join(rj_dir, zip_filename)
            
            await create_secure_zip(downloaded_files, zip_path)
            
            zip_size = os.path.getsize(zip_path)
            zip_size_str = get_file_size_str(zip_size)
            
            return zip_path, zip_size_str
        else:
            raise Exception("没有成功下载任何文件")
    except Exception as e:
        logger.error(f"下载所有文件时出错: {str(e)}")
        raise e

async def safe_upload_file(bot: Bot, event: MessageEvent, original_file_path: str, rj_id: str = "", track_name: str = "", track_index: int = 0) -> str:
    """安全上传文件到QQ"""
    original_file_path = str(original_file_path)
    processed_file_path = original_file_path
    
    # 单文件下载不进行格式转换，保持原始格式
    
    file_size = os.path.getsize(processed_file_path)
    file_size_str = get_file_size_str(file_size)
    
    # 确定文件扩展名
    file_ext = Path(processed_file_path).suffix.lower()
    if not file_ext:
        file_ext = ".mp3"
    
    # 生成上传文件名
    rj_number = re.sub(r'[^0-9]', '', rj_id)
    original_filename = os.path.basename(processed_file_path)
    
    if file_ext == ".zip":
        upload_filename = original_filename
    else:
        if not original_filename.startswith(rj_number) and rj_number:
            upload_filename = f"{rj_number}_{original_filename}"
        else:
            upload_filename = original_filename
    
    # 创建临时文件用于上传
    temp_dir = tempfile.gettempdir()
    temp_file_path = os.path.join(temp_dir, upload_filename)
    
    try:
        await async_file_operation(shutil.copy2, processed_file_path, temp_file_path)
        logger.info(f"文件已复制到临时目录: {temp_file_path}")
        
        abs_path = os.path.abspath(temp_file_path)
        
        # 尝试上传文件
        try:
            logger.info(f"尝试上传文件: {abs_path}，文件名: {upload_filename}")
            if isinstance(event, GroupMessageEvent):
                await bot.upload_group_file(
                    group_id=event.group_id,
                    file=abs_path,
                    name=upload_filename
                )
            else:
                await bot.upload_private_file(
                    user_id=event.user_id,
                    file=abs_path,
                    name=upload_filename
                )
            
            file_type = file_ext.replace(".", "").upper()
            if file_ext == ".zip":
                password = plugin_config.asmr_zip_password
                success_msg = f"压缩包 ({file_size_str}) 发送中，请稍等！密码: {password}"
            else:
                success_msg = f"文件 ({file_size_str}) [{file_type}] 发送中，请稍等！"
            
            return success_msg
            
        except Exception as e:
            logger.warning(f"文件上传失败: {str(e)}")
            
            file_type = file_ext.replace(".", "").upper()
            if file_ext == ".zip":
                password = plugin_config.asmr_zip_password
                success_msg = f"压缩包 ({file_size_str}) 处理完成！密码: {password}"
            else:
                success_msg = f"文件 ({file_size_str}) [{file_type}] 处理完成！"
            
            return success_msg
            
    finally:
        # 清理临时文件
        temp_files_to_remove = [temp_file_path]
        if processed_file_path != original_file_path:
            temp_files_to_remove.append(processed_file_path)
        
        for temp_file in temp_files_to_remove:
            try:
                if os.path.exists(temp_file):
                    await async_file_operation(os.remove, temp_file)
            except OSError as e:
                logger.error(f"删除临时文件失败 {temp_file}: {str(e)}") 