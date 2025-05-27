<div align="center">
  <a href="https://v2.nonebot.dev/store"><img src="https://github.com/A-kirami/nonebot-plugin-template/blob/resources/nbp_logo.png" width="180" height="180" alt="NoneBotPluginLogo"></a>
  <br>
  <p><img src="https://github.com/A-kirami/nonebot-plugin-template/blob/resources/NoneBotPlugin.svg" width="240" alt="NoneBotPluginText"></p>
</div>

<div align="center">

# nonebot-plugin-asmr100

*✨ 能在QQ群里听音声，支持下载和分享ASMR音声文件 ✨*

<a href="./LICENSE">
    <img src="https://img.shields.io/github/license/ala4562/nonebot-plugin-asmr100.svg" alt="license">
</a>
<a href="https://pypi.python.org/pypi/nonebot-plugin-asmr100">
    <img src="https://img.shields.io/pypi/v/nonebot-plugin-asmr100.svg" alt="pypi">
</a>
<img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="python">

</a>

</div>

## 📖 介绍

nonebot-plugin-asmr100 是一个基于 [NoneBot2](https://github.com/nonebot/nonebot2) 的插件，用于在QQ群中搜索、下载和分享ASMR音声文件。该插件支持多种功能，包括关键词搜索、文件列表显示、单曲下载、整个文件夹下载以及批量下载并打包等。

### 功能特点

- 🔍 通过关键词或标签搜索音声
- 📂 查看音声的详细信息和轨道列表
- 🎵 下载并分享单个音频文件
- 📦 将多个音频文件打包成加密ZIP文件分享
- 🔄 支持格式转换，优化文件大小
- 🛡️ 文件反和谐处理，避免内容审查

## 💿 安装

<details open>
<summary>使用 nb-cli 安装</summary>
在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装

```bash
nb plugin install nonebot-plugin-asmr100
```
</details>

<details>
<summary>使用包管理器安装</summary>
在 nonebot2 项目的插件目录下, 打开命令行, 根据你使用的包管理器, 输入相应的安装命令

<details>
<summary>pip</summary>

```bash
pip install nonebot-plugin-asmr100
```
</details>

<details>
<summary>pdm</summary>

```bash
pdm add nonebot-plugin-asmr100
```
</details>

<details>
<summary>poetry</summary>

```bash
poetry add nonebot-plugin-asmr100
```
</details>

<details>
<summary>conda</summary>

```bash
conda install nonebot-plugin-asmr100
```
</details>

打开 nonebot2 项目根目录下的 `pyproject.toml` 文件, 在 `[tool.nonebot]` 部分追加写入

```toml
plugins = ["nonebot_plugin_asmr100"]
```
</details>

## ⚙️ 配置

### 基础配置

在 nonebot2 项目的 `.env` 文件中添加下表中的配置项：

| 配置项 | 必填 | 默认值 | 说明 |
|:-----:|:----:|:----:|:----:|
| `ASMR_ZIP_PASSWORD` | 否 | `afu3355` | ZIP文件加密密码 |
| `ASMR_MAX_ERROR_COUNT` | 否 | `3` | 用户最大错误尝试次数 |
| `ASMR_API_TIMEOUT` | 否 | `15` | API请求超时时间（秒） |
| `ASMR_API_BASE_URL` | 否 | `https://api.asmr-200.com/api` | API基础URL |

### 高级配置

如需自定义更多配置，可在 `.env` 文件中添加：

```env
# 基础配置
ASMR_ZIP_PASSWORD=your_password_here
ASMR_MAX_ERROR_COUNT=5
ASMR_API_TIMEOUT=30

# HTTP请求配置
ASMR_HTTP_HEADERS={"User-Agent": "Your Custom User Agent"}

# 支持的音频格式
ASMR_AUDIO_EXTENSIONS=[".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac"]
```

### 配置示例

完整的 `.env` 配置示例：

```env
# NoneBot基础配置
HOST=127.0.0.1
PORT=8080
SUPERUSERS=["123456789"]
NICKNAME=["小助手", "bot"]
COMMAND_START=["/", ""]

# ASMR100插件配置
ASMR_ZIP_PASSWORD=my_secure_password_123
ASMR_MAX_ERROR_COUNT=5
ASMR_API_TIMEOUT=20
```

## 🔧 前置要求

### 必需依赖

1. **Python 3.8+**：插件运行环境
2. **NoneBot2**：聊天机器人框架
3. **nonebot-plugin-htmlrender**：图片渲染支持
   ```bash
   pip install nonebot-plugin-htmlrender
   ```
4. **nonebot-plugin-localstore**：本地存储支持
   ```bash
   pip install nonebot-plugin-localstore
   ```

### 可选依赖

为了获得最佳体验，建议安装以下可选依赖：

#### 1. FFmpeg（音频转换）
- **用途**：音频格式转换，优化文件大小
- **安装方法**：
  - Windows: 下载 [FFmpeg](https://ffmpeg.org/download.html) 并添加到PATH
  - Linux: `sudo apt install ffmpeg` 或 `sudo yum install ffmpeg`
  - macOS: `brew install ffmpeg`

#### 2. 7-Zip（高强度加密）
- **用途**：创建高强度加密的ZIP文件
- **安装方法**：
  - Windows: 下载 [7-Zip](https://www.7-zip.org/) 并安装
  - Linux: `sudo apt install p7zip-full` 或 `sudo yum install p7zip`
  - macOS: `brew install p7zip`

#### 3. ZIP命令行工具（备用加密）
- **用途**：当7-Zip不可用时的备用加密方案
- **安装方法**：
  - Windows: 通常已内置
  - Linux: `sudo apt install zip` 或 `sudo yum install zip`
  - macOS: 通常已内置

### 依赖检查

插件启动时会自动检查依赖状态：

```
[INFO] ASMR100 插件数据目录: /path/to/data
[INFO] ffmpeg已安装，支持音频格式转换
[INFO] [ASMR100] 7z 已安装，支持高强度加密
[INFO] [ASMR100] 插件初始化完成，所有核心功能可用
```

如果某些依赖缺失，插件仍可正常运行，但部分功能可能受限：
- 无FFmpeg：无法进行音频格式转换
- 无7z/zip：将使用Python内置的ZIP加密（安全性较低）

## 🎉 使用

### 指令表

| 指令 | 权限 | 需要@ | 范围 | 说明 |
|:-----:|:----:|:----:|:----:|:----:|
| `搜音声 [关键词] [页数]` | 所有人 | 否 | 群聊/私聊 | 搜索音声，关键词可用空格或"/"分割不同tag |
| `搜索下一页` | 所有人 | 否 | 群聊/私聊 | 显示搜索结果的下一页 |
| `听音声 [RJ号] [选项]` | 所有人 | 否 | 群聊/私聊 | 下载并分享音声文件 |

### 详细使用说明

#### 1. 搜索音声

**基础搜索**：
```
搜音声 纯爱
搜音声 催眠
搜音声 双声道
```

**多标签搜索**：
```
搜音声 纯爱 治愈        # 空格分割
搜音声 催眠/双声道      # 斜杠分割
搜音声 JK 学生 治愈 1   # 指定页数
```

**翻页**：
```
搜音声 纯爱 2          # 直接搜索第2页
搜索下一页             # 查看下一页结果
```

#### 2. 下载音声

**查看文件列表**：
```
听音声 RJ123456        # 显示该音声的文件结构
```

**下载单个文件**：
```
听音声 RJ123456 1      # 下载第1个音频文件
听音声 RJ123456 5      # 下载第5个音频文件
```

**下载文件夹**：
```
听音声 RJ123456 A      # 下载A文件夹（打包为ZIP）
听音声 RJ123456 B      # 下载B文件夹（打包为ZIP）
```

**批量下载**：
```
听音声 RJ123456 all    # 下载所有文件（打包为ZIP）
听音声 RJ123456 全部   # 同上，中文命令
```

**强制ZIP格式**：
```
听音声 RJ123456 1 zip  # 将单个文件也打包为ZIP
听音声 RJ123456 2 zip  # 适用于大文件或需要密码保护
```

### 选项说明

| 选项类型 | 格式 | 说明 | 示例 |
|:-----:|:----:|:----:|:----:|
| **数字序号** | `1`, `2`, `3`... | 下载对应序号的单个音频文件 | `听音声 RJ123456 1` |
| **字母序号** | `A`, `B`, `C`... | 下载对应字母的文件夹（ZIP） | `听音声 RJ123456 A` |
| **全部下载** | `all`, `全部` | 下载所有文件（ZIP） | `听音声 RJ123456 all` |
| **强制ZIP** | `数字 zip` | 单个文件也打包为ZIP | `听音声 RJ123456 1 zip` |

### 使用技巧

1. **搜索技巧**：
   - 使用具体的标签词汇，如"治愈"、"催眠"、"双声道"等
   - 多个关键词可以缩小搜索范围
   - 支持中文和日文关键词

2. **下载技巧**：
   - 大文件建议使用ZIP格式，压缩后更容易传输
   - ZIP文件有密码保护，默认密码为配置中的 `ASMR_ZIP_PASSWORD`
   - 单个小文件可以直接下载，无需打包

3. **文件结构**：
   - 数字序号对应音频文件（按顺序排列）
   - 字母序号对应文件夹（如果存在多级目录）
   - 插件会自动识别音频格式：MP3、WAV、OGG、FLAC、M4A等

### 示例对话

```
用户: 搜音声 纯爱 治愈
Bot: [显示搜索结果图片，包含多个音声作品]

用户: 听音声 RJ123456
Bot: [显示该音声的文件列表和结构]

用户: 听音声 RJ123456 1
Bot: [发送第1个音频文件]

用户: 听音声 RJ123456 A
Bot: [发送A文件夹的ZIP压缩包]
     密码: afu3355

用户: 听音声 RJ123456 all
Bot: [发送包含所有文件的ZIP压缩包]
     密码: afu3355
```

### 效果图

![搜索结果示例](https://img.cynicis.link/1743180320606.png)
![音声内容列表示例](https://img.cynicis.link/1743180438097.png)

## 📝 注意事项

### 使用限制

- **文件大小**：受QQ群文件上传限制，过大的文件可能无法上传
- **网络环境**：需要稳定的网络连接，建议在网络良好时使用
- **频率限制**：避免频繁请求，以免触发API限制

### 安全提醒

- **密码保护**：ZIP文件使用密码加密，默认密码为 `afu3355`
- **文件安全**：下载的文件会临时存储在本地，使用后会自动清理
- **隐私保护**：插件不会收集用户个人信息

### 法律声明

- **仅供学习**：本插件仅供学习交流使用，请勿用于商业用途
- **版权尊重**：请遵守相关法律法规，尊重原作者版权
- **免责声明**：使用本插件产生的任何问题，开发者不承担责任

### 技术说明

- **格式支持**：支持 MP3、WAV、OGG、FLAC、M4A 等主流音频格式
- **压缩算法**：优先使用7z高强度加密，备用zip加密
- **反和谐**：内置文件反和谐处理，提高传输成功率

### 致谢

- 感谢 [asmr-100.com](https://asmr-100.com) 提供数据源
- 感谢所有为开源社区贡献的开发者
## 🔄 更新日志

### v0.3.1 - Bug修复版本
**🐛 Bug修复**
- 修复多级文件夹最后嵌套的图片显示不对的问题   
- 修复文件位置不对应的问题  
- 修复输入单个数字下载某个文件夹而不是对应序号文件的问题  

**🔧 代码优化**
- 重构函数名和功能，提高代码可读性
- 优化错误处理机制
- 改进文件路径处理逻辑

### v0.3.0  - 稳定性提升
**🐛 Bug修复**
- 修复线程阻塞问题，提升响应速度
- 修复错误判断和抛出机制
- 优化异步处理流程

**⚡ 性能优化**
- 改进下载队列管理
- 优化内存使用

### v0.2.3 - 依赖检查优化
**🐛 Bug修复**
- 修复ffmpeg和7z依赖检查问题
- 改进系统命令检测逻辑
- 优化错误提示信息

### v0.2.0 - 功能增强
**✨ 新功能**
- 添加状态管理系统
- 支持用户搜索历史
- 增加错误重试机制

### v0.1.0  - 初始版本
**🎉 核心功能**
- 实现基本的搜索和下载功能
- 支持文件夹结构和文件列表显示
- 支持文件转换和压缩
- 基础的用户交互界面

**🔧 技术特性**
- 基于NoneBot2框架
- 支持多种音频格式
- 集成HTML渲染功能
- 本地存储支持

## 🔧 故障排除

### 常见问题

#### 1. 插件无法启动
**问题**：插件加载失败或启动报错
**解决方案**：
```bash
# 检查依赖是否安装
pip install nonebot-plugin-htmlrender nonebot-plugin-localstore

# 检查NoneBot2版本
pip install --upgrade nonebot2

# 查看详细错误日志
```

#### 2. 搜索无结果
**问题**：搜索音声时返回空结果
**解决方案**：
- 检查网络连接是否正常
- 尝试更换关键词
- 检查API配置是否正确
- 查看控制台是否有错误信息

#### 3. 下载失败
**问题**：音声下载失败或文件损坏
**解决方案**：
- 检查网络稳定性
- 尝试重新下载
- 检查磁盘空间是否充足
- 查看是否触发了频率限制

#### 4. ZIP文件无法解压
**问题**：下载的ZIP文件提示密码错误
**解决方案**：
- 确认使用正确的密码（默认：`afu3355`）
- 检查配置文件中的 `ASMR_ZIP_PASSWORD` 设置
- 确保ZIP文件下载完整

#### 5. 依赖检查失败
**问题**：FFmpeg或7z检查失败
**解决方案**：
```bash
# Windows安装FFmpeg
# 下载并添加到PATH环境变量

# Linux安装FFmpeg
sudo apt install ffmpeg

# 安装7z
sudo apt install p7zip-full
```

### 调试模式

启用详细日志以便调试：

```python
# 在bot.py中添加
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 获取帮助

如果遇到问题，可以：

1. **查看日志**：检查NoneBot2的运行日志
2. **提交Issue**：在GitHub上提交详细的问题报告
3. **社区求助**：在NoneBot2社区寻求帮助

## 🧑‍💻 贡献

欢迎各种形式的贡献，包括但不限于：

- 🐛 **Bug报告**：发现问题请及时反馈
- 💡 **功能建议**：提出新功能想法
- 📝 **文档改进**：完善使用说明和注释
- 🔧 **代码贡献**：提交Pull Request
- 🌐 **翻译工作**：支持多语言版本

### 贡献流程

1. Fork本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建Pull Request

## 📄 开源协议

本项目采用 [MIT](./LICENSE) 许可证。

## 🙏 致谢

- [NoneBot2](https://github.com/nonebot/nonebot2)：优秀的聊天机器人框架
- [nonebot-plugin-htmlrender](https://github.com/kexue-z/nonebot-plugin-htmlrender)：提供HTML渲染支持
- [nonebot-plugin-asmr](https://github.com/CCYellowStar2/nonebot-plugin-asmr)：提供灵感

## 👨‍💻 作者

- 阿福 (主要开发者)

---

*本项目仅供技术研究使用，请勿用于任何违法违规用途*