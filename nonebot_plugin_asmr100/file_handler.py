"""文件处理模块"""

import os
import re
import shutil
import random
import string
import tempfile
import zipfile
import asyncio
from pathlib import Path
from typing import List, Tuple, Optional
from contextlib import asynccontextmanager

from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, GroupMessageEvent, MessageSegment

from .config import plugin_config
from .utils import sanitize_filename, get_file_size_str, async_file_operation

@asynccontextmanager
async def temp_file_manager(file_path: str):
    """临时文件管理"""
    try:
        yield file_path
    finally:
        try:
            if os.path.exists(file_path):
                await async_file_operation(os.remove, file_path)
        except Exception as e:
            logger.error(f"清理临时文件失败: {file_path}, 错误: {str(e)}")

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
                except:
                    pass
            return mp3_file_path
        else:
            return audio_file_path
    except Exception as e:
        logger.error(f"转换过程中出错: {str(e)}")
        return audio_file_path

async def create_secure_zip(file_paths: List[str], zip_path: str, password: Optional[str] = None) -> str:
    """创建加密的ZIP文件"""
    if password is None:
        password = plugin_config.asmr_zip_password
        
    try:
        temp_zip_path = zip_path + ".temp.zip"
        
        def create_zip():
            with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in file_paths:
                    original_filename = os.path.basename(file_path)
                    zipf.write(file_path, original_filename)
        
        await async_file_operation(create_zip)
        
        try:
            encrypted_temp_path = zip_path + ".enc.zip"
            
            process = await asyncio.create_subprocess_exec(
                "7z", "a", "-tzip", "-p" + password, "-mem=AES256", encrypted_temp_path, temp_zip_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                process = await asyncio.create_subprocess_exec(
                    "zip", "-j", "-P", password, encrypted_temp_path, temp_zip_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and os.path.exists(encrypted_temp_path):
                await async_file_operation(shutil.move, encrypted_temp_path, zip_path)
                await async_file_operation(os.remove, temp_zip_path)
            else:
                logger.warning("外部ZIP加密命令失败，使用Python内置加密")
                
                encrypted_zip_path = zip_path + ".enc.zip"
                
                def encrypt_zip():
                    with zipfile.ZipFile(temp_zip_path, 'r') as src_zip:
                        with zipfile.ZipFile(encrypted_zip_path, 'w', zipfile.ZIP_DEFLATED) as dst_zip:
                            dst_zip.setpassword(password.encode())
                            
                            for item in src_zip.infolist():
                                data = src_zip.read(item.filename)
                                item.flag_bits |= 0x1
                                dst_zip.writestr(item, data)
                
                await async_file_operation(encrypt_zip)
                
                await async_file_operation(os.rename, encrypted_zip_path, zip_path)
                await async_file_operation(os.remove, temp_zip_path)
                
        except Exception as e:
            logger.error(f"外部加密命令失败: {str(e)}")
            await async_file_operation(os.rename, temp_zip_path, zip_path)
        
        return zip_path
    except Exception as e:
        logger.error(f"创建ZIP文件失败: {str(e)}")
        for path in [temp_zip_path, zip_path + ".enc.zip"]:
            if os.path.exists(path):
                try:
                    await async_file_operation(os.remove, path)
                except:
                    pass
        raise e

async def obfuscate_audio(file_path: str) -> str:
    """对音频文件进行处理以避免内容识别"""
    try:
        original_ext = os.path.splitext(file_path)[1].lower()
        
        def read_file():
            with open(file_path, 'rb') as f:
                return bytearray(f.read())
        
        data = await async_file_operation(read_file)
        
        if len(data) > 1024:
            for _ in range(5):
                pos = random.randint(1024, min(len(data) - 100, 2048))
                data[pos] = random.randint(0, 255)
            
            rand_chars = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
            new_path = f"{os.path.splitext(file_path)[0]}_obfs_{rand_chars}{original_ext}"
            
            def write_file():
                with open(new_path, 'wb') as f:
                    f.write(data)
            
            await async_file_operation(write_file)
            
            return new_path
        return str(file_path)
    except Exception as e:
        logger.error(f"音频处理失败: {str(e)}")
        return str(file_path)

async def download_folder_files(folder_items: List[dict], folder_name: str, rj_dir: str, rj_id: str) -> Tuple[str, str]:
    """下载指定文件夹中的所有音频文件并创建ZIP"""
    downloaded_files = []
    converted_count = 0
    
    try:
        folder_path = Path(rj_dir) / sanitize_filename(folder_name)
        folder_path.mkdir(exist_ok=True)
        
        total_files = sum(1 for item in folder_items if item["type"] == "audio")
        
        # 递归处理文件和子文件夹
        async def process_items(items, current_path):
            nonlocal downloaded_files, converted_count
            
            for item in items:
                if item["type"] == "audio":
                    url = item["mediaDownloadUrl"]
                    title = item["title"]
                    
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
                    
                    safe_filename = sanitize_filename(title)
                    file_path = current_path / f"{safe_filename}{extension}"
                    
                    try:
                        from .data_source import download_file
                        await download_file(url, file_path)
                        
                        original_path = str(file_path)
                        if extension.lower() in [".wav", ".flac", ".ogg"]:
                            mp3_path = await convert_to_mp3(original_path)
                            if mp3_path != original_path:
                                file_path = Path(mp3_path)
                                converted_count += 1
                        
                        downloaded_files.append(str(file_path))
                    except Exception as e:
                        logger.error(f"下载文件失败: {str(e)}")
                
                elif item["type"] == "folder" and "children" in item:
                    sub_folder_name = sanitize_filename(item["title"])
                    sub_folder_path = current_path / sub_folder_name
                    sub_folder_path.mkdir(exist_ok=True)
                    
                    await process_items(item["children"], sub_folder_path)
        
        await process_items(folder_items, folder_path)
        
        if downloaded_files:
            safe_folder_name = sanitize_filename(folder_name)
            rj_number = re.sub(r'[^0-9]', '', rj_id)
            zip_filename = f"{rj_number}_{safe_folder_name}.zip"
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
    """下载单个音频文件并创建ZIP"""
    try:
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
        
        safe_filename = sanitize_filename(title)
        file_path = Path(rj_dir) / f"{safe_filename}{extension}"
        
        from .data_source import download_file
        await download_file(url, file_path)
        
        original_path = str(file_path)
        if extension.lower() in [".wav", ".flac", ".ogg"]:
            mp3_path = await convert_to_mp3(original_path)
            if mp3_path != original_path:
                file_path = Path(mp3_path)
        
        rj_number = re.sub(r'[^0-9]', '', rj_id)
        zip_filename = f"{rj_number}.zip"
        zip_path = os.path.join(rj_dir, zip_filename)
        
        await create_secure_zip([str(file_path)], zip_path)
        
        zip_size = os.path.getsize(zip_path)
        zip_size_str = get_file_size_str(zip_size)
        
        return zip_path, zip_size_str
    except Exception as e:
        logger.error(f"下载文件时出错: {str(e)}")
        raise e

async def download_all_files(urls: List[str], keywords: List[str], rj_dir: str, rj_id: str) -> Tuple[str, str]:
    """下载所有音频文件并创建ZIP"""
    downloaded_files = []
    converted_count = 0
    
    try:
        for index, (url, title) in enumerate(zip(urls, keywords)):            
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
            
            safe_filename = sanitize_filename(title)
            file_path = Path(rj_dir) / f"{safe_filename}{extension}"
            
            try:
                from .data_source import download_file
                await download_file(url, file_path)
                
                original_path = str(file_path)
                if extension.lower() in [".wav", ".flac", ".ogg"]:
                    mp3_path = await convert_to_mp3(original_path)
                    if mp3_path != original_path:
                        file_path = Path(mp3_path)
                        converted_count += 1
                
                downloaded_files.append(str(file_path))
            except Exception as e:
                logger.error(f"下载文件失败: {str(e)}")
        
        if downloaded_files:
            rj_number = re.sub(r'[^0-9]', '', rj_id)
            zip_filename = f"{rj_number}.zip"
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
    
    if any(original_file_path.lower().endswith(ext) for ext in ['.wav', '.flac', '.ogg']):
        try:
            mp3_path = await convert_to_mp3(original_file_path)
            if mp3_path != original_file_path:
                processed_file_path = mp3_path
        except Exception as e:
            logger.error(f"转换音频文件失败，继续使用原文件: {str(e)}")
    
    file_size = os.path.getsize(processed_file_path)
    file_size_str = get_file_size_str(file_size)
    
    original_ext = os.path.splitext(processed_file_path)[1].lower()
    if processed_file_path.lower().endswith('.mp3'):
        file_ext = ".mp3"
    elif processed_file_path.lower().endswith('.wav'):
        file_ext = ".wav"
    elif processed_file_path.lower().endswith('.flac'):
        file_ext = ".flac"
    elif processed_file_path.lower().endswith('.ogg'):
        file_ext = ".ogg"
    elif processed_file_path.lower().endswith('.m4a'):
        file_ext = ".m4a"
    elif processed_file_path.lower().endswith('.zip'):
        file_ext = ".zip"
    else:
        file_ext = ".mp3"
    
    if not file_ext.lower() == ".zip":
        obfuscated_file_path = await obfuscate_audio(processed_file_path)
    else:
        obfuscated_file_path = processed_file_path
    
    rj_number = re.sub(r'[^0-9]', '', rj_id)
    
    if file_ext.lower() == ".zip":
        upload_filename = os.path.basename(processed_file_path)
    else:
        original_filename = os.path.basename(processed_file_path)
        if not original_filename.startswith(rj_number):
            upload_filename = f"{rj_number}_{original_filename}"
        else:
            upload_filename = original_filename
    
    temp_dir = tempfile.gettempdir()
    temp_file_path = os.path.join(temp_dir, upload_filename)
    
    await async_file_operation(shutil.copy2, obfuscated_file_path, temp_file_path)
    logger.info(f"文件已复制到临时目录: {temp_file_path}")
    
    abs_path = os.path.abspath(temp_file_path)
    
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
        if file_ext.lower() == ".zip":
            from .config import plugin_config
            password = plugin_config.asmr_zip_password
            success_msg = f"压缩包 ({file_size_str}) 发送中，请稍等！密码: {password}"
        else:
            success_msg = f"文件 ({file_size_str}) [{file_type}] 发送中，请稍等！"
        
        return success_msg
        
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        
        file_type = file_ext.replace(".", "").upper()
        if file_ext.lower() == ".zip":
            from .config import plugin_config
            password = plugin_config.asmr_zip_password
            success_msg = f"压缩包 ({file_size_str}) 处理完成！密码: {password}"
        else:
            success_msg = f"文件 ({file_size_str}) [{file_type}] 处理完成！"
        
        return success_msg
        
    finally:
        try:
            await async_file_operation(os.remove, temp_file_path)
            if obfuscated_file_path != processed_file_path and obfuscated_file_path != original_file_path:
                await async_file_operation(os.remove, obfuscated_file_path)
        except Exception as e:
            logger.error(f"删除临时文件失败: {str(e)}")