diff --git a/README.md b/README.md
index 54e6f406757fa12649095cca7c5516489e24ce4a..cb1bad827c5d57dbf130dc83ab85837c543522ee 100644
--- a/README.md
+++ b/README.md
@@ -319,55 +319,59 @@ Bot: [发送包含所有文件的ZIP压缩包]
 
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
 
+### v0.3.2 - 文档调整
+**📝 文档更新**
+- 清理发布说明，移除 PyPI 发布教程和命令示例
+
 ### v0.3.1 - Bug修复版本
 **🐛 Bug修复**
-- 修复多级文件夹最后嵌套的图片显示不对的问题   
-- 修复文件位置不对应的问题  
-- 修复输入单个数字下载某个文件夹而不是对应序号文件的问题  
+- 修复多级文件夹最后嵌套的图片显示不对的问题
+- 修复文件位置不对应的问题
+- 修复输入单个数字下载某个文件夹而不是对应序号文件的问题
 
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
@@ -471,26 +475,26 @@ logging.basicConfig(level=logging.DEBUG)
 
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
 
-*本项目仅供技术研究使用，请勿用于任何违法违规用途*
\ No newline at end of file
+*本项目仅供技术研究使用，请勿用于任何违法违规用途*
