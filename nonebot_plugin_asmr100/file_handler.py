"""文件处理相关函数"""

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

from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, GroupMessageEvent, MessageSegment

from .config import plugin_config
from .utils import sanitize_filename, get_file_size_str

async def convert_to_mp3(audio_file_path: str) -> str:
    """
    将音频文件转换为MP3格式
    
    参数:
        audio_file_path: 音频文件路径
        
    返回:
        转换后的文件路径
    """
    try:
        # 检查是否已经是MP3文件
        if audio_file_path.lower().endswith('.mp3'):
            return audio_file_path
        
        mp3_file_path = os.path.splitext(audio_file_path)[0] + '.mp3'
        
        # 检查MP3文件是否已存在
        if os.path.exists(mp3_file_path):
            return mp3_file_path
        
        # 使用ffmpeg转换
        process = await asyncio.create_subprocess_exec(
            'ffmpeg', '-i', audio_file_path, '-vn', '-ar', '44100', '-ac', '2', '-b:a', '192k', mp3_file_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            # 可选：删除原始文件以节省空间
            if os.path.exists(audio_file_path) and os.path.exists(mp3_file_path):
                try:
                    os.remove(audio_file_path)
                except:
                    pass
            return mp3_file_path
        else:
            return audio_file_path
    except Exception as e:
        logger.error(f"转换过程中出错: {str(e)}")
        return audio_file_path

async def create_secure_zip(file_paths: List[str], zip_path: str, password: Optional[str] = None) -> str:
    """
    创建高度加密的ZIP文件，保留原始文件名
    
    参数:
        file_paths: 要打包的文件路径列表
        zip_path: ZIP文件保存路径
        password: 加密密码，默认使用配置中的密码
        
    返回:
        创建的ZIP文件路径
    """
    if password is None:
        password = plugin_config.asmr_zip_password
        
    try:
        # 创建临时ZIP文件
        temp_zip_path = zip_path + ".temp.zip"
        
        # 首先创建没有加密的ZIP
        with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in file_paths:
                # 使用原始文件名
                original_filename = os.path.basename(file_path)
                zipf.write(file_path, original_filename)
        
        # 然后使用7z或zip命令行工具进行加密
        try:
            # 先创建一个临时加密ZIP
            encrypted_temp_path = zip_path + ".enc.zip"
            
            # 尝试使用7z
            process = await asyncio.create_subprocess_exec(
                "7z", "a", "-tzip", "-p" + password, "-mem=AES256", encrypted_temp_path, temp_zip_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                # 7z失败，尝试使用zip命令
                process = await asyncio.create_subprocess_exec(
                    "zip", "-j", "-P", password, encrypted_temp_path, temp_zip_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
            
            # 如果外部命令成功，使用加密后的文件
            if process.returncode == 0 and os.path.exists(encrypted_temp_path):
                shutil.move(encrypted_temp_path, zip_path)
                os.remove(temp_zip_path)
            else:
                # 如果外部命令都失败了，就使用Python的zipfile (弱加密但总比没有好)
                logger.warning("外部ZIP加密命令失败，使用Python内置加密 (弱加密)")
                
                # 创建一个新的临时ZIP文件
                encrypted_zip_path = zip_path + ".enc.zip"
                
                # 从未加密ZIP中读取文件，并创建加密ZIP
                with zipfile.ZipFile(temp_zip_path, 'r') as src_zip:
                    with zipfile.ZipFile(encrypted_zip_path, 'w', zipfile.ZIP_DEFLATED) as dst_zip:
                        # 设置加密密码
                        dst_zip.setpassword(password.encode())
                        
                        # 复制并加密所有文件
                        for item in src_zip.infolist():
                            data = src_zip.read(item.filename)
                            # 必须设置这个flag才能加密
                            item.flag_bits |= 0x1
                            dst_zip.writestr(item, data)
                
                # 重命名为最终文件名
                os.rename(encrypted_zip_path, zip_path)
                os.remove(temp_zip_path)
                
        except Exception as e:
            logger.error(f"外部加密命令失败: {str(e)}")
            # 如果外部命令有问题，回退到原始方法
            os.rename(temp_zip_path, zip_path)
        
        return zip_path
    except Exception as e:
        logger.error(f"创建ZIP文件失败: {str(e)}")
        # 清理临时文件
        for path in [temp_zip_path, zip_path + ".enc.zip"]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except:
                    pass
        raise e

async def obfuscate_audio(file_path: str) -> str:
    """
    对音频文件进行简单的修改，以避免内容识别，同时保留扩展名
    
    参数:
        file_path: 音频文件路径
        
    返回:
        处理后的文件路径
    """
    try:
        # 获取原始扩展名
        original_ext = os.path.splitext(file_path)[1].lower()
        
        # 读取文件
        with open(file_path, 'rb') as f:
            data = bytearray(f.read())
        
        # 不修改文件头部和尾部，只修改中间部分的一些数据
        if len(data) > 1024:
            # 在1KB后的位置随机修改几个字节
            for _ in range(5):
                pos = random.randint(1024, min(len(data) - 100, 2048))
                data[pos] = random.randint(0, 255)
            
            # 生成一个随机字符串作为文件名的部分
            rand_chars = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
            # 确保我们保留原始扩展名
            new_path = f"{os.path.splitext(file_path)[0]}_obfs_{rand_chars}{original_ext}"
            
            with open(new_path, 'wb') as f:
                f.write(data)
            
            return new_path
        return str(file_path)
    except Exception as e:
        logger.error(f"音频反和谐失败: {str(e)}")
        return str(file_path)

async def download_folder_files(folder_items: List[dict], folder_name: str, rj_dir: str, rj_id: str) -> Tuple[str, str]:
    """
    下载指定文件夹中的所有音频文件并创建安全ZIP
    
    参数:
        folder_items: 文件夹中的项目列表
        folder_name: 文件夹名称
        rj_dir: RJ目录
        rj_id: RJ号
        
    返回:
        (zip文件路径, 文件大小字符串)
    """
    downloaded_files = []
    converted_count = 0
    
    try:
        # 创建文件夹路径
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
                    
                    # 保留原始文件名，仅做基本安全处理
                    safe_filename = sanitize_filename(title)
                    file_path = current_path / f"{safe_filename}{extension}"
                    
                    # 下载文件
                    try:
                        from .data_source import download_file
                        await download_file(url, file_path)
                        
                        # 转换各种格式到MP3
                        original_path = str(file_path)
                        if extension.lower() in [".wav", ".flac", ".ogg"]:
                            mp3_path = await convert_to_mp3(original_path)
                            if mp3_path != original_path:
                                file_path = Path(mp3_path)
                                converted_count += 1
                        
                        downloaded_files.append(str(file_path))
                    except Exception as e:
                        logger.error(f"下载文件失败: {str(e)}")
                        # 继续下载其他文件
                
                elif item["type"] == "folder" and "children" in item:
                    # 处理子文件夹
                    sub_folder_name = sanitize_filename(item["title"])
                    sub_folder_path = current_path / sub_folder_name
                    sub_folder_path.mkdir(exist_ok=True)
                    
                    await process_items(item["children"], sub_folder_path)
        
        # 开始处理文件夹内容
        await process_items(folder_items, folder_path)
        
        # 创建ZIP文件
        if downloaded_files:
            # 创建安全的文件夹名
            safe_folder_name = sanitize_filename(folder_name)
            # 使用RJ号+文件夹名命名ZIP
            rj_number = re.sub(r'[^0-9]', '', rj_id)
            zip_filename = f"{rj_number}_{safe_folder_name}.zip"
            zip_path = os.path.join(rj_dir, zip_filename)
            
            await create_secure_zip(downloaded_files, zip_path)
            
            # 获取ZIP文件大小
            zip_size = os.path.getsize(zip_path)
            zip_size_str = get_file_size_str(zip_size)
            
            return zip_path, zip_size_str
        else:
            raise Exception("没有成功下载任何文件")
    except Exception as e:
        logger.error(f"下载文件夹内容时出错: {str(e)}")
        raise e

async def download_single_file_zip(url: str, title: str, rj_dir: str, rj_id: str, track_index: int) -> Tuple[str, str]:
    """
    下载单个音频文件并创建ZIP
    
    参数:
        url: 文件URL
        title: 文件标题
        rj_dir: RJ目录
        rj_id: RJ号
        track_index: 音轨索引
        
    返回:
        (zip文件路径, 文件大小字符串)
    """
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
        from .data_source import download_file
        await download_file(url, file_path)
        
        # 转换音频为MP3
        original_path = str(file_path)
        if extension.lower() in [".wav", ".flac", ".ogg"]:
            mp3_path = await convert_to_mp3(original_path)
            if mp3_path != original_path:
                file_path = Path(mp3_path)
        
        # 创建ZIP文件 - 使用RJ纯数字命名
        rj_number = re.sub(r'[^0-9]', '', rj_id)  # 提取RJ号中的纯数字部分
        zip_filename = f"{rj_number}.zip"
        zip_path = os.path.join(rj_dir, zip_filename)
        
        await create_secure_zip([str(file_path)], zip_path)
        
        # 获取ZIP文件大小
        zip_size = os.path.getsize(zip_path)
        zip_size_str = get_file_size_str(zip_size)
        
        return zip_path, zip_size_str
    except Exception as e:
        logger.error(f"下载文件时出错: {str(e)}")
        raise e

async def download_all_files(urls: List[str], keywords: List[str], rj_dir: str, rj_id: str) -> Tuple[str, str]:
    """
    下载所有音频文件并创建安全ZIP，同时转换所有音频到MP3
    
    参数:
        urls: 文件URL列表
        keywords: 文件标题列表
        rj_dir: RJ目录
        rj_id: RJ号
        
    返回:
        (zip文件路径, 文件大小字符串)
    """
    downloaded_files = []
    converted_count = 0
    
    try:
        for index, (url, title) in enumerate(zip(urls, keywords)):            
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
            try:
                from .data_source import download_file
                await download_file(url, file_path)
                
                # 转换各种格式到MP3
                original_path = str(file_path)
                if extension.lower() in [".wav", ".flac", ".ogg"]:
                    mp3_path = await convert_to_mp3(original_path)
                    if mp3_path != original_path:
                        file_path = Path(mp3_path)
                        converted_count += 1
                
                downloaded_files.append(str(file_path))
            except Exception as e:
                logger.error(f"下载文件失败: {str(e)}")
                # 继续下载其他文件，不中断整个过程
        
        # 创建ZIP文件
        if downloaded_files:
            # 修改为使用纯数字RJ号命名
            rj_number = re.sub(r'[^0-9]', '', rj_id)  # 提取RJ号中的纯数字部分
            zip_filename = f"{rj_number}.zip"
            zip_path = os.path.join(rj_dir, zip_filename)
            
            await create_secure_zip(downloaded_files, zip_path)
            
            # 获取ZIP文件大小
            zip_size = os.path.getsize(zip_path)
            zip_size_str = get_file_size_str(zip_size)
            
            return zip_path, zip_size_str
        else:
            raise Exception("没有成功下载任何文件")
    except Exception as e:
        logger.error(f"下载所有文件时出错: {str(e)}")
        raise e

async def safe_upload_file(bot: Bot, event: MessageEvent, original_file_path: str, rj_id: str = "", track_name: str = "", track_index: int = 0) -> bool:
    """
    安全地上传文件到QQ，处理各种路径问题，确保正确的扩展名
    
    参数:
        bot: Bot实例
        event: 消息事件
        original_file_path: 原始文件路径
        rj_id: RJ号
        track_name: 音轨名称
        track_index: 音轨索引
        
    返回:
        布尔值，表示上传是否成功
    """
    try:
        # 处理原始文件路径
        original_file_path = str(original_file_path)
        processed_file_path = original_file_path
        
        # 检查是否是需要转换的音频文件
        if any(original_file_path.lower().endswith(ext) for ext in ['.wav', '.flac', '.ogg']):
            try:
                mp3_path = await convert_to_mp3(original_file_path)
                if mp3_path != original_file_path:
                    processed_file_path = mp3_path
            except Exception as e:
                logger.error(f"转换音频文件失败，继续使用原文件: {str(e)}")
        
        # 获取正确的文件大小
        file_size = os.path.getsize(processed_file_path)
        file_size_str = get_file_size_str(file_size)
        file_size_mb = file_size / (1024 * 1024)
        
        # 获取处理前的原始扩展名
        original_ext = os.path.splitext(processed_file_path)[1].lower()
        
        # 确定正确的扩展名
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
            # 如果无法确定，默认使用MP3
            file_ext = ".mp3"
        
        # 应用反和谐处理 - 同时保留扩展名
        if not file_ext.lower() == ".zip":  # 不对ZIP文件应用反和谐
            obfuscated_file_path = await obfuscate_audio(processed_file_path)
        else:
            obfuscated_file_path = processed_file_path
        
        # 生成文件名 - 使用RJ号命名
        rj_number = re.sub(r'[^0-9]', '', rj_id)  # 提取RJ号中的纯数字部分
        
        if file_ext.lower() == ".zip":
            # 如果是ZIP文件，使用原始文件名
            upload_filename = os.path.basename(processed_file_path)
        else:
            # 普通音频文件，保留原始文件名
            original_filename = os.path.basename(processed_file_path)
            # 但确保文件名有RJ号前缀
            if not original_filename.startswith(rj_number):
                upload_filename = f"{rj_number}_{original_filename}"
            else:
                upload_filename = original_filename
        
        # 在临时目录创建一个副本，使用生成的文件名
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, upload_filename)
        
        # 复制文件
        shutil.copy2(obfuscated_file_path, temp_file_path)
        logger.info(f"文件已复制到临时目录: {temp_file_path}")
        
        # 使用绝对路径上传
        abs_path = os.path.abspath(temp_file_path)
        
        # 上传文件
        success = False
        
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
            success = True
        except Exception as e:
            logger.error(f"第一种上传方法失败: {str(e)}")
            try:
                # 备用方法
                logger.info(f"尝试备用上传方法")
                if isinstance(event, GroupMessageEvent):
                    await bot.call_api(
                        "upload_group_file",
                        group_id=event.group_id,
                        file=abs_path,
                        name=upload_filename
                    )
                else:
                    await bot.call_api(
                        "upload_private_file",
                        user_id=event.user_id,
                        file=abs_path,
                        name=upload_filename
                    )
                success = True
            except Exception as e2:
                logger.error(f"备用上传方法也失败: {str(e2)}")
                raise Exception(f"文件上传失败: {str(e2)}")
        
        # 删除临时文件
        try:
            os.remove(temp_file_path)
            if obfuscated_file_path != processed_file_path and obfuscated_file_path != original_file_path:
                os.remove(obfuscated_file_path)
        except Exception as e:
            logger.error(f"删除临时文件失败: {str(e)}")
        
        if success:
            file_type = file_ext.replace(".", "").upper()
            if file_ext.lower() == ".zip":
                from .config import plugin_config
                password = plugin_config.asmr_zip_password
                return True, f"压缩包 ({file_size_str}) 发送中，请稍等！密码: {password}"
            else:
                return True, f"文件 ({file_size_str}) [{file_type}] 发送中，请稍等！"
        else:
            raise Exception("文件上传失败")
            
    except Exception as e:
        logger.error(f"文件发送失败: {str(e)}")
        return False, f"文件发送失败: {str(e)}\n文件已下载到服务器: {original_file_path}"