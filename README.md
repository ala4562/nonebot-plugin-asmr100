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
- 🔒 支持文件加密保护隐私
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

在 nonebot2 项目的`.env`文件中添加下表中的配置项：

| 配置项 | 必填 | 默认值 | 说明 |
|:-----:|:----:|:----:|:----:|
| ASMR_DATA_DIR | 否 | data/asmr100 | 数据保存目录 |
| ASMR_ZIP_PASSWORD | 否 | afu3355 | ZIP文件密码 |
| ASMR_MAX_ERROR_COUNT | 否 | 3 | 最大错误尝试次数 |

## 🔧 前置要求

1. 需要安装 [nonebot-plugin-htmlrender](https://github.com/nonebot/plugin-htmlrender) 以支持图片渲染
2. 可选：安装 `ffmpeg` 以支持音频格式转换
3. 可选：安装 `7z` 或 `zip` 命令行工具以支持高强度加密

## 🎉 使用

### 指令表

| 指令 | 权限 | 需要@ | 范围 | 说明 |
|:-----:|:----:|:----:|:----:|:----:|
| 搜音声 [关键词] [页数] | 所有人 | 否 | 群聊/私聊 | 搜索音声，关键词可用空格或"/"分割不同tag |
| 搜索下一页 | 所有人 | 否 | 群聊/私聊 | 显示搜索结果的下一页 |
| 听音声 [RJ号] [选项] | 所有人 | 否 | 群聊/私聊 | 下载并分享音声文件 |

### 选项说明

- **数字序号**：下载并发送对应序号的单个音频文件
- **数字+zip**：下载对应序号的音频文件并创建加密ZIP
- **"全部"/"all"**：下载所有音频文件并创建加密ZIP
- **字母序号**：下载对应字母序号的文件夹并创建加密ZIP

### 示例

```
搜音声 纯爱 NTR 1
搜索下一页
听音声 RJ123456
听音声 RJ123456 2
听音声 RJ123456 2 zip
听音声 RJ123456 all
听音声 RJ123456 A
```

### 效果图

![搜索结果示例](https://img.cynicis.link/1743180320606.png)
![音声内容列表示例](https://img.cynicis.link/1743180438097.png)

## 📝 注意事项

- 文件大小上传限制，过大的文件可能无法上传
- 为提高成功率，建议使用压缩方式发送文件
- 密码保护的ZIP文件需要使用密码解压
- 本插件仅供学习交流使用，请勿用于非法用途
- 请遵守相关法律法规，尊重版权
- 感谢asmr-100.com
## 🔄 更新日志

### 0.1.4 (初始版本)

- 实现基本的搜索和下载功能
- 支持文件夹结构和文件列表显示
- 支持文件转换和压缩

## 🧑‍💻 贡献

欢迎各种形式的贡献，包括但不限于：功能改进、文档完善、问题报告等。

## 📄 开源协议

本项目采用 [MIT](./LICENSE) 许可证。

## 🙏 致谢

- [NoneBot2](https://github.com/nonebot/nonebot2)：优秀的聊天机器人框架
- [nonebot-plugin-htmlrender](https://github.com/nonebot/plugin-htmlrender)：提供HTML渲染支持

## 👨‍💻 作者

- 阿福 (主要开发者)

---

*本项目仅供技术研究使用，请勿用于任何违法违规用途*