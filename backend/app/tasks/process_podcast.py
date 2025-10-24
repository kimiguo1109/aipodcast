"""
播客后台处理任务
提取文本 → 生成音频 → 上传到 S3
"""
import io
import threading
import struct
from PyPDF2 import PdfReader
from docx import Document

from app.services.data_service import data_service
from app.services.ai_service import ai_service
from app.utils.s3_storage import s3_storage


def get_mp3_duration(audio_data: bytes) -> int:
    """
    从 MP3 字节数据中提取音频时长（秒）
    使用简单的比特率估算方法
    
    Args:
        audio_data: MP3 音频字节数据
    
    Returns:
        音频时长（秒）
    """
    try:
        # ElevenLabs 通常生成 128kbps 的 MP3
        # 比特率 = 128000 bits/s = 16000 bytes/s
        bitrate = 16000  # bytes per second
        duration = len(audio_data) / bitrate
        return int(duration)
    except Exception as e:
        print(f"   ⚠️  时长计算失败: {e}，使用默认估算")
        return int(len(audio_data) / 4000)


def extract_text_from_file(file_content: bytes, filename: str) -> str:
    """
    从文件中提取文本
    
    Args:
        file_content: 文件内容（字节）
        filename: 文件名（用于判断类型）
    
    Returns:
        提取的文本
    """
    file_ext = filename.lower().split('.')[-1]
    
    try:
        if file_ext == 'txt':
            # 文本文件
            return file_content.decode('utf-8', errors='ignore')
        
        elif file_ext == 'pdf':
            # PDF 文件
            pdf_file = io.BytesIO(file_content)
            reader = PdfReader(pdf_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        
        elif file_ext in ['doc', 'docx']:
            # Word 文件
            doc_file = io.BytesIO(file_content)
            doc = Document(doc_file)
            text = ""
            for para in doc.paragraphs:
                text += para.text + "\n"
            return text.strip()
        
        elif file_ext in ['mp3', 'wav', 'mp4', 'mov']:
            # 音频/视频文件 - 使用 ElevenLabs 转录
            print(f"🎤 检测到音频文件，使用 ElevenLabs 进行转录...")
            try:
                transcript = ai_service.transcribe_audio(file_content, filename)
                return transcript
            except Exception as e:
                print(f"❌ 音频转录失败: {e}")
                return f"音频转录失败: {str(e)}"
        
        else:
            return f"不支持的文件类型: {file_ext}"
    
    except Exception as e:
        print(f"❌ 文本提取失败: {e}")
        return f"文本提取失败: {str(e)}"


def process_podcast_background(podcast_id: str, job_id: str, s3_key: str):
    """
    后台处理播客生成
    
    Args:
        podcast_id: 播客ID
        job_id: 任务ID
        s3_key: S3 文件键
    """
    print(f"\n{'='*60}")
    print(f"🚀 开始处理播客")
    print(f"   Podcast ID: {podcast_id}")
    print(f"   Job ID: {job_id}")
    print(f"   S3 Key: {s3_key}")
    print(f"{'='*60}\n")
    
    try:
        # 更新任务状态为 processing
        data_service.update_job(job_id, {
            "status": "processing",
            "progress": 10
        })
        
        # 1. 从 S3 下载文件
        print("📥 步骤 1/5: 从 S3 下载文件...")
        file_content = s3_storage.download_file(s3_key)
        
        if not file_content:
            raise Exception("无法从 S3 下载文件")
        
        data_service.update_job(job_id, {
            "progress": 20,
            "status_message": "📥 文件下载完成"
        })
        
        # 2. 提取文本/转录音频
        print("\n📝 步骤 2/5: 提取文本/转录音频...")
        data_service.update_job(job_id, {
            "progress": 25,
            "status_message": "📝 提取文本内容..."
        })
        podcast = data_service.get_podcast(podcast_id)
        filename = podcast.get('original_filename', 'unknown.txt')
        file_ext = filename.lower().split('.')[-1]
        
        # 判断是否为音频文件
        is_audio_file = file_ext in ['mp3', 'wav', 'mp4', 'mov']
        
        text = extract_text_from_file(file_content, filename)
        print(f"   提取文本长度: {len(text)} 字符")
        print(f"   前100字符: {text[:100]}...")
        
        if not text or len(text) < 10:
            raise Exception("提取的文本太短或为空")
        
        data_service.update_job(job_id, {
            "progress": 40,
            "status_message": f"✅ 提取完成 ({len(text)} 字符)"
        })
        
        # 3. 处理音频
        if is_audio_file:
            # 对于音频文件：直接使用上传的文件，不需要重新生成
            print("\n🎵 步骤 3/5: 使用原始音频文件...")
            print(f"   音频文件已在 S3: {s3_key}")
            
            # 使用原始上传的音频
            audio_s3_key = s3_key
            uploaded_key = s3_key
            
            data_service.update_job(job_id, {
                "progress": 70,
                "status_message": "🎵 使用原始音频文件"
            })
        else:
            # 对于文本文件：生成音频（支持多声音对话）
            print("\n🎙️  步骤 3/5: 生成音频...")
            
            # 检测语言（简单判断：如果有中文字符则为中文，否则为英文）
            import re
            has_chinese = bool(re.search(r'[\u4e00-\u9fff]', text))
            detected_language = "zh" if has_chinese else "en"
            print(f"   🌐 检测到语言: {detected_language}")
            
            data_service.update_job(job_id, {
                "progress": 45,
                "status_message": f"🎭 生成多声道对话音频 (需要3-5分钟)..."
            })
            
            # 如果文本太长，智能截取适当长度（ElevenLabs 有字符限制）
            max_chars = 3000
            if len(text) > max_chars:
                print(f"   ⚠️  文本过长({len(text)}字符)，智能截取...")
                data_service.update_job(job_id, {
                    "progress": 47,
                    "status_message": "✂️ 优化文本长度..."
                })
                
                # 智能截断：在句子结束处截断
                truncated = text[:max_chars]
                
                # 尝试在句号、问号、感叹号处截断（优先级从高到低）
                for delimiter in ['. ', '。', '! ', '！', '? ', '？', '\n\n', '\n']:
                    last_delimiter_pos = truncated.rfind(delimiter)
                    if last_delimiter_pos > max_chars * 0.8:  # 至少保留80%的内容
                        text = truncated[:last_delimiter_pos + len(delimiter)].strip()
                        print(f"   ✂️  在合适的位置截断，最终长度: {len(text)} 字符")
                        break
                else:
                    # 如果找不到合适的分隔符，在最后一个空格处截断
                    last_space_pos = truncated.rfind(' ')
                    if last_space_pos > max_chars * 0.9:
                        text = truncated[:last_space_pos].strip()
                    else:
                        text = truncated.strip()
                    print(f"   ✂️  在空格处截断，最终长度: {len(text)} 字符")
            
            # 使用多声音对话API（自动检测是否为对话，如果不是对话则回退到单声音）
            audio_data = ai_service.generate_dialogue_audio(text, detected_language)
            
            if not audio_data:
                raise Exception("音频生成失败")
            
            data_service.update_job(job_id, {
                "progress": 60,
                "status_message": "✅ 音频生成完成！"
            })
            
            # 4. 上传生成的音频到 S3
            print("\n📤 步骤 4/5: 上传音频到 S3...")
            data_service.update_job(job_id, {
                "progress": 65,
                "status_message": "📤 上传音频到云端..."
            })
            audio_file = io.BytesIO(audio_data)
            audio_s3_key = f"podcasts/{podcast_id}.mp3"
            
            uploaded_key = s3_storage.upload_file(
                file_obj=audio_file,
                original_filename=f"{podcast_id}.mp3",
                prefix="podcasts",
                content_type="audio/mpeg"
            )
            
            if not uploaded_key:
                raise Exception("音频上传到 S3 失败")
            
            data_service.update_job(job_id, {
                "progress": 70,
                "status_message": "✅ 上传完成！"
            })
        
        # 生成音频 URL (使用流式播放URL)
        audio_url = f"/api/v1/podcasts/{podcast_id}/stream"
        
        data_service.update_job(job_id, {
            "progress": 90,
            "status_message": "💾 保存播客信息..."
        })
        
        # 5. 更新播客状态
        print("\n✅ 步骤 5/5: 更新播客状态...")
        
        update_data = {
            "audio_url": audio_url,
            "audio_s3_key": uploaded_key,
            "transcript": text,
            "extracted_text": text,  # 同时保存到 extracted_text 字段
            "status": "completed"
        }
        
        # 如果是新生成的音频，计算时长
        if not is_audio_file and 'audio_data' in locals():
            duration_seconds = get_mp3_duration(audio_data)
            update_data["duration_seconds"] = duration_seconds
            print(f"   ⏱️  音频时长: {duration_seconds} 秒")
        
        data_service.update_podcast(podcast_id, update_data)
        
        data_service.update_job(job_id, {
            "status": "completed",
            "progress": 100,
            "status_message": "🎉 处理完成！"
        })
        
        print(f"\n{'='*60}")
        print(f"🎉 播客处理完成！")
        print(f"   音频 URL: {audio_url}")
        print(f"   文本长度: {len(text)} 字符")
        if not is_audio_file and 'audio_data' in locals():
            print(f"   音频大小: {len(audio_data)} bytes")
        print(f"{'='*60}\n")
    
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"❌ 播客处理失败: {e}")
        print(f"{'='*60}\n")
        
        # 更新为失败状态
        data_service.update_podcast(podcast_id, {
            "status": "failed"
        })
        
        data_service.update_job(job_id, {
            "status": "failed",
            "error_message": str(e)
        })


def generate_podcast_background(podcast_id: str, job_id: str):
    """
    后台 AI 生成播客
    
    Args:
        podcast_id: 播客ID
        job_id: 任务ID
    """
    print(f"\n{'='*60}")
    print(f"🤖 开始 AI 生成播客")
    print(f"   Podcast ID: {podcast_id}")
    print(f"   Job ID: {job_id}")
    print(f"{'='*60}\n")
    
    try:
        # 获取任务信息
        job = data_service.get_job(job_id)
        if not job:
            raise Exception("任务不存在")
        
        inputs = job.get("inputs", {})
        topic = inputs.get("topic", "")
        style = inputs.get("style", "Solo Talk Show")
        duration_minutes = inputs.get("duration_minutes", 5)
        language = inputs.get("language", "en")
        
        if not topic:
            raise Exception("缺少主题参数")
        
        print(f"📋 生成参数: 主题={topic}, 风格={style}, 时长={duration_minutes}分钟, 语言={language}")
        
        # 更新任务状态为 processing
        data_service.update_job(job_id, {
            "status": "processing",
            "progress": 10,
            "status_message": "🤖 AI 正在创作播客脚本..."
        })
        
        # 1. 使用 Gemini 生成播客稿件
        print("🤖 步骤 1/4: 使用 Gemini AI 生成播客稿件...")
        script = ai_service.generate_script_from_topic(
            topic=topic,
            style=style,
            duration_minutes=duration_minutes,
            language=language
        )
        
        if not script or len(script) < 50:
            raise Exception("生成的稿件太短或为空")
        
        print(f"✅ 稿件生成完成！长度: {len(script)} 字符")
        data_service.update_job(job_id, {
            "progress": 40,
            "status_message": f"📝 脚本创作完成 ({len(script)} 字符)"
        })
        
        # 2. 使用 ElevenLabs 生成音频（支持多声音对话）
        print("\n🎙️  步骤 2/4: 使用 ElevenLabs 生成音频...")
        data_service.update_job(job_id, {
            "progress": 45,
            "status_message": "🎭 生成多声道对话音频 (需要3-5分钟)..."
        })
        
        # 如果稿件太长，智能截取适当长度（ElevenLabs 有字符限制）
        max_chars = 3000
        if len(script) > max_chars:
            print(f"   ⚠️  稿件过长({len(script)}字符)，智能截取...")
            data_service.update_job(job_id, {
                "progress": 47,
                "status_message": "✂️ 优化脚本长度..."
            })
            
            # 智能截断：在句子结束处截断
            truncated = script[:max_chars]
            
            # 尝试在句号、问号、感叹号处截断（优先级从高到低）
            for delimiter in ['. ', '。', '! ', '！', '? ', '？', '\n\n', '\n']:
                last_delimiter_pos = truncated.rfind(delimiter)
                if last_delimiter_pos > max_chars * 0.8:  # 至少保留80%的内容
                    script = truncated[:last_delimiter_pos + len(delimiter)].strip()
                    print(f"   ✂️  在合适的位置截断，最终长度: {len(script)} 字符")
                    break
            else:
                # 如果找不到合适的分隔符，在最后一个空格处截断
                last_space_pos = truncated.rfind(' ')
                if last_space_pos > max_chars * 0.9:
                    script = truncated[:last_space_pos].strip()
                else:
                    script = truncated.strip()
                print(f"   ✂️  在空格处截断，最终长度: {len(script)} 字符")
        
        # 使用多声音对话API（自动检测是否为对话，如果不是对话则回退到单声音）
        audio_data = ai_service.generate_dialogue_audio(script, language)
        
        if not audio_data:
            raise Exception("音频生成失败")
        
        print(f"✅ 音频生成完成！大小: {len(audio_data)} bytes")
        data_service.update_job(job_id, {
            "progress": 70,
            "status_message": "✅ 音频生成完成！"
        })
        
        # 3. 上传音频到 S3
        print("\n📤 步骤 3/4: 上传音频到 S3...")
        data_service.update_job(job_id, {
            "progress": 75,
            "status_message": "📤 上传音频到云端..."
        })
        audio_file = io.BytesIO(audio_data)
        
        uploaded_key = s3_storage.upload_file(
            file_obj=audio_file,
            original_filename=f"{podcast_id}.mp3",
            prefix="podcasts",
            content_type="audio/mpeg"
        )
        
        if not uploaded_key:
            raise Exception("音频上传到 S3 失败")
        
        print(f"✅ 音频上传成功: {uploaded_key}")
        data_service.update_job(job_id, {
            "progress": 85,
            "status_message": "✅ 上传完成！正在保存..."
        })
        
        # 4. 更新播客状态
        print("\n✅ 步骤 4/4: 更新播客状态...")
        data_service.update_job(job_id, {
            "progress": 90,
            "status_message": "💾 保存播客信息..."
        })
        
        audio_url = f"/api/v1/podcasts/{podcast_id}/stream"
        
        # 计算音频时长
        duration_seconds = get_mp3_duration(audio_data)
        print(f"   ⏱️  音频时长: {duration_seconds} 秒")
        
        data_service.update_podcast(podcast_id, {
            "audio_url": audio_url,
            "audio_s3_key": uploaded_key,
            "transcript": script,
            "extracted_text": script,
            "duration_seconds": duration_seconds,
            "status": "completed"
        })
        
        data_service.update_job(job_id, {
            "status": "completed",
            "progress": 100
        })
        
        print(f"\n{'='*60}")
        print(f"🎉 AI 播客生成完成！")
        print(f"   音频 URL: {audio_url}")
        print(f"   稿件长度: {len(script)} 字符")
        print(f"   音频大小: {len(audio_data)} bytes")
        print(f"   预计时长: {duration_seconds} 秒")
        print(f"{'='*60}\n")
    
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"❌ AI 播客生成失败: {e}")
        print(f"{'='*60}\n")
        
        # 更新为失败状态
        data_service.update_podcast(podcast_id, {
            "status": "failed"
        })
        
        data_service.update_job(job_id, {
            "status": "failed",
            "error_message": str(e)
        })


def start_processing_task(podcast_id: str, job_id: str, s3_key: str):
    """
    启动后台处理任务（在新线程中）
    根据任务类型路由到不同的处理函数
    
    Args:
        podcast_id: 播客ID
        job_id: 任务ID
        s3_key: S3 文件键（AI 生成时为 None）
    """
    # 获取任务信息以确定类型
    job = data_service.get_job(job_id)
    if not job:
        print(f"❌ 任务不存在: {job_id}")
        return
    
    job_type = job.get("type", "upload")
    
    # 根据任务类型选择处理函数
    if job_type == "generate":
        # AI 生成播客
        print(f"🤖 启动 AI 生成任务...")
        thread = threading.Thread(
            target=generate_podcast_background,
            args=(podcast_id, job_id)
        )
    else:
        # 文件上传处理
        print(f"📁 启动文件处理任务...")
        thread = threading.Thread(
            target=process_podcast_background,
            args=(podcast_id, job_id, s3_key)
        )
    
    thread.daemon = True
    thread.start()
    
    print(f"✅ 后台任务已启动 (Thread ID: {thread.ident}, Type: {job_type})")

