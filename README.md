# Translator

一个简洁的桌面翻译工具，支持中英文互译，提供拼音显示和英文词典信息。

## 功能特性

- **多翻译引擎支持**
  - DeepL API（优先用于短文本）
  - MyMemory API（优先用于长文本）
  - 自动切换翻译服务

- **中文拼音显示**
  - 自动为中文文本生成带声调的拼音
  - 长文本（3句及以上）自动跳过拼音显示
  - 需要安装 `pypinyin` 库

- **英文词典信息**
  - 显示英文单词的音标
  - 显示词性（名词、动词等）
  - 支持多个释义显示

- **快捷键操作**
  - 全局热键 `Ctrl+Alt+P` 快速呼出/隐藏窗口
  - 丰富的键盘快捷键支持
  - 支持窗口位置快速调整

- **系统托盘集成**
  - 最小化到系统托盘
  - 托盘图标双击呼出窗口
  - 右键菜单提供退出选项

- **界面特性**
  - 简洁的半透明界面
  - Windows 11 亚克力毛玻璃效果
  - 可拖动窗口位置

## 快捷键说明

### 标准模式
- `回车` - 进入输入模式
- `h` - 显示帮助信息
- `x` - 复制译文并清空
- `v` - 复制译文
- `p` - 粘贴剪贴板内容到输入框
- `y` - 复制输入内容
- `u` - 循环翻译（用译文再译）
- `e+a` - 输入模式（追加）
- `e+g` - 输入模式（开头编辑）
- `e+e` - 清空并输入
- `1-8` - 移动窗口至屏幕边缘
- `9` - 移动窗口至屏幕中心
- `0` - 切换鼠标拖动（可拖动/锁定）
- `Esc` - 关闭窗口

### 输入模式
- `回车` - 翻译并返回标准模式
- `Shift+回车` - 换行
- `Esc` - 返回标准模式（不翻译）

## 依赖库

### 必需库
- **PyQt5** - GUI 框架，用于构建用户界面
- **requests** - HTTP 请求库，用于调用翻译和词典 API

### 可选库
- **keyboard** - 全局热键库，用于实现全局快捷键功能
  - 未安装时可通过托盘图标操作
- **pypinyin** - 中文拼音转换库，用于生成中文拼音
  - 未安装时不显示拼音功能

## 安装

### 安装依赖
```bash
pip install -r requirements.txt
```

### 手动安装依赖
```bash
pip install PyQt5 requests
pip install keyboard  # 可选，用于全局热键
pip install pypinyin  # 可选，用于中文拼音
```

## 配置

### DeepL API（可选）
如需使用 DeepL 翻译服务，需要设置环境变量：

**Windows:**
```cmd
set DEEPL_API_KEY=your_api_key_here
```

**Linux/Mac:**
```bash
export DEEPL_API_KEY=your_api_key_here
```

未设置 API Key 时，程序将仅使用 MyMemory 免费翻译服务。

### 自定义 DeepL API 端点（可选）
```cmd
set DEEPL_API_URL=https://api-free.deepl.com/v2/translate
```

## 使用方法

### 图形界面模式
直接运行程序：
```bash
python main.py
```

### 命令行模式
支持命令行翻译：
```bash
python main.py "要翻译的文本"
```

## 编译方法

### windows
需要使用nuitka（也可以用别的，具体参考对应工具官方文档）

安装nuitka
```bash
pip install nuitka
pip install pip install "Nuitka[onefile]"
```

打包
```bash
#多文件
python -m nuitka --standalone --enable-plugin=pyqt5 --include-package-data=pypinyin main.py
#打包完成后可执行文件位于main.dist目录中
```
```bash
#单文件
python -m nuitka --onefile --enable-plugin=pyqt5 --include-package-data=pypinyin main.py
```
可以加上
```bash
--windows-disable-console
```
参数以不显示终端窗口

## 注意事项

- 翻译功能需要网络连接
- 英文词典信息来自 dictionaryapi.dev，可能偶尔不可用
- 中文拼音功能需要安装 pypinyin 库
- 全局热键功能需要安装 keyboard 库
- Windows 11 亚克力效果仅在 Windows 11 上生效
- 自动获取焦点的功能需要先手动获取一次，后续再次呼出即可获取到焦点

## 许可证

本项目仅供个人学习使用。
