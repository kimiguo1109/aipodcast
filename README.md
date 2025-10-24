# EchoCast - AI播客平台

一个基于 AI 的智能播客生成和管理平台，可以将文本、文档等内容转换为高质量的播客音频。

## 功能特性

- 📝 多格式文件上传支持（文本、PDF、音频、视频等）
- 🤖 AI 驱动的内容分析和播客脚本生成
- 🎙️ 高质量语音合成（使用 ElevenLabs）
- 📚 播客库管理和播放
- 🔍 智能搜索和过滤
- 💾 云端存储（AWS S3）

## 技术栈

### 后端
- **框架**: FastAPI
- **AI 服务**: Google Gemini API
- **语音合成**: ElevenLabs API
- **存储**: AWS S3
- **语言**: Python 3.9+

### 前端
- **框架**: React
- **构建工具**: Vite
- **样式**: Tailwind CSS
- **路由**: React Router

## 快速开始

### 环境配置

1. 克隆仓库
```bash
git clone https://github.com/kimiguo1109/aipodcast.git
cd aipodcast
```

2. 配置环境变量

在项目根目录创建 `.env` 文件，参考以下配置：

```env
# AWS S3 配置
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
AWS_S3_BUCKET=your_s3_bucket_name
AWS_REGION=us-east-1

# ElevenLabs API 配置
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# Gemini API 配置
GEMINI_API_KEY=your_gemini_api_key_here
```

### 后端设置

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 前端设置

```bash
cd frontend
npm install
npm run dev
```

前端将在 `http://localhost:5173` 运行，后端 API 在 `http://localhost:8000`

## 项目结构

```
aipodcast/
├── backend/              # FastAPI 后端
│   ├── app/
│   │   ├── api/         # API 路由
│   │   ├── services/    # 业务逻辑
│   │   ├── tasks/       # 异步任务
│   │   └── utils/       # 工具函数
│   └── tests/           # 测试文件
├── frontend/            # React 前端
│   ├── src/
│   │   ├── components/  # React 组件
│   │   ├── pages/       # 页面组件
│   │   └── services/    # API 服务
│   └── public/          # 静态资源
└── stitch_echocast_landing_page/  # 着陆页设计

```

## API 文档

启动后端服务后，访问以下地址查看 API 文档：
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 安全说明

⚠️ **重要**: 
- 请勿将 API 密钥和敏感信息提交到代码仓库
- 使用 `.env` 文件管理环境变量
- `.env` 文件已在 `.gitignore` 中被忽略

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License

