from flask import Flask, render_template, request, jsonify, send_file
import requests
import os
import time
import threading
import queue
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()
ASSEMBLYAI_API_KEY = os.getenv('ASSEMBLYAI_API_KEY')
GOOGLE_GEMINI_API_KEY = os.getenv('GOOGLE_GEMINI_API_KEY')

if not ASSEMBLYAI_API_KEY:
    raise ValueError("ASSEMBLYAI_API_KEY not found in .env file")

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['OUTPUT_FOLDER'] = os.path.join(os.path.dirname(__file__), 'outputs')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# AssemblyAI API endpoints
BASE_URL = "https://api.assemblyai.com"
UPLOAD_ENDPOINT = f"{BASE_URL}/v2/upload"
TRANSCRIPT_ENDPOINT = f"{BASE_URL}/v2/transcript"

headers = {
    "authorization": ASSEMBLYAI_API_KEY
}

# Global variables
log_queue = queue.Queue()
processing_status = {
    "running": False,
    "current": 0,
    "total": 0,
    "elapsed_time": 0,
    "start_time": None
}

def proofread_text_with_gemini(text):
    """
    Sử dụng Google Gemini để soát lỗi chính tả và ngữ pháp:
    - Sửa chính tả
    - Sửa ngữ pháp
    - Cải thiện câu văn
    """
    try:
        if not GOOGLE_GEMINI_API_KEY:
            log_queue.put("Gemini API key không tìm thấy, return text gốc")
            return text
        
        genai.configure(api_key=GOOGLE_GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Prompt để sửa chính tả và ngữ pháp
        prompt = f"""Hãy sửa chính tả, ngữ pháp và cải thiện câu văn cho đoạn text dưới đây. 
QUAN TRỌNG: Giữ nguyên định dạng, dòng trống và xuống dòng.
Chỉ trả về văn bản đã được sửa, không giải thích thêm:

{text}"""
        
        response = model.generate_content(prompt)
        improved_text = response.text.strip()
        return improved_text
        
    except Exception as e:
        log_queue.put(f"Gemini API lỗi: {str(e)}, dùng text gốc")
        return text

def upload_audio_file(file_path):
    """Upload audio file to AssemblyAI"""
    try:
        log_queue.put(f"Uploading: {os.path.basename(file_path)}")
        with open(file_path, "rb") as f:
            response = requests.post(UPLOAD_ENDPOINT, headers=headers, data=f)
        
        if response.status_code == 200:
            upload_url = response.json()["upload_url"]
            log_queue.put(f"Upload thành công")
            return upload_url
        else:
            log_queue.put(f"Upload lỗi: {response.text}")
            return None
    except Exception as e:
        log_queue.put(f"Upload exception: {str(e)}")
        return None

def transcribe_audio(audio_url, language="vi"):
    """Submit transcription request to AssemblyAI"""
    try:
        log_queue.put(f"Gửi transcription request...")
        
        language_code = {
            "vi": "vi",
            "en": "en",
            "ja": "ja",
            "th": "th",
            "auto": None
        }.get(language, None)
        
        data = {
            "audio_url": audio_url,
            "language_code": language_code,
            "speech_model": "best"  # Best quality
        }
        
        response = requests.post(TRANSCRIPT_ENDPOINT, json=data, headers=headers)
        
        if response.status_code == 200:
            transcript_id = response.json()['id']
            log_queue.put(f"Request submitted (ID: {transcript_id[:8]}...)")
            return transcript_id
        else:
            log_queue.put(f"Request lỗi: {response.text}")
            return None
    except Exception as e:
        log_queue.put(f"Transcription exception: {str(e)}")
        return None

def poll_transcription(transcript_id, timeout=600):
    """Poll for transcription result"""
    polling_endpoint = f"{TRANSCRIPT_ENDPOINT}/{transcript_id}"
    start_time = time.time()
    
    while True:
        try:
            response = requests.get(polling_endpoint, headers=headers)
            result = response.json()
            status = result.get('status')
            
            elapsed = time.time() - start_time
            
            if status == 'completed':
                text = result.get('text', '')
                log_queue.put(f"Transcription xong!")
                return text
            
            elif status == 'error':
                log_queue.put(f"Transcription error: {result.get('error')}")
                return None
            
            elif elapsed > timeout:
                log_queue.put(f"Timeout sau {timeout}s")
                return None
            
            else:
                time.sleep(2)
        
        except Exception as e:
            log_queue.put(f"Poll exception: {str(e)}")
            return None

def process_files(files, language, output_name):
    """
    OPTIMIZED BATCH PIPELINE:
    PHASE 1: Transcribe tất cả files, gộp text vào list
    PHASE 2: Chia batch nhỏ (5 files/batch), gọi Gemini từng batch (tiết kiệm token)
    PHASE 3: Lưu kết quả gộp
    """
    global processing_status
    processing_status["running"] = True
    processing_status["total"] = len(files)
    processing_status["start_time"] = time.time()
    
    log_queue.put(f"Files selected: {len(files)}")
    log_queue.put(f"Language: {language}")
    log_queue.put(f"Số file: {len(files)}")
    log_queue.put("Bắt đầu transcribe...")
    
    all_texts = []  # Gộp text từ tất cả files
    
    # PHASE 1: Transcribe tất cả files
    for idx, file_path in enumerate(files, 1):
        processing_status["current"] = idx
        filename = os.path.basename(file_path)
        log_queue.put(f"[{idx}/{len(files)}]  {filename}")
        
        # Upload file
        audio_url = upload_audio_file(file_path)
        if not audio_url:
            log_queue.put(f"Bỏ qua file này")
            continue
        
        # Transcribe
        transcript_id = transcribe_audio(audio_url, language)
        if not transcript_id:
            log_queue.put(f"Bỏ qua file này")
            continue
        
        # Poll for result
        text = poll_transcription(transcript_id)
        if text:
            all_texts.append(f"[{filename}]\n{text}\n")
            log_queue.put(f"Hoàn thành: {filename}")
        else:
            log_queue.put(f"Không nhận được kết quả")
    
    # PHASE 2: Chia batch 5 files/lần, gọi Gemini từng batch (tiết kiệm token)
    if all_texts:
        log_queue.put("\nProofing lỗi bằng Gemini (batch processing)...")
        batch_size = 5
        all_proofread = []
        
        for i in range(0, len(all_texts), batch_size):
            batch = all_texts[i:i+batch_size]
            batch_text = "\n".join(batch)
            log_queue.put(f"Batch {i//batch_size + 1}: {len(batch)} files")
            
            proofread_batch = proofread_text_with_gemini(batch_text)
            all_proofread.append(proofread_batch)
        
        # PHASE 3: Lưu kết quả gộp
        if not output_name.endswith('.txt'):
            output_name = output_name + '.txt'
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_name)
        with open(output_path, "w", encoding="utf-8") as out:
            out.write("\n".join(all_proofread).rstrip())
        
        log_queue.put(f"Đã xử lý {len(all_texts)} files trong {(len(all_texts)-1)//batch_size + 1} batch")
    else:
        log_queue.put("Không có file nào được xử lý thành công")
    
    elapsed_time = time.time() - processing_status["start_time"]
    processing_status["elapsed_time"] = elapsed_time
    minutes, seconds = divmod(int(elapsed_time), 60)
    log_queue.put(f"\nDONE - Thời gian hoàn thành: {minutes}m {seconds}s")
    processing_status["running"] = False
    
    # Xóa files upload để tiết kiệm dung lượng
    for file_path in files:
        try:
            os.remove(file_path)
        except Exception as e:
            log_queue.put(f"Không thể xóa {os.path.basename(file_path)}: {str(e)}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files' not in request.files:
        return jsonify({"error": "No files"}), 400
    
    files = request.files.getlist('files')
    language = request.form.get('language', 'vi')
    output_name = request.form.get('output_name', 'output.txt')
    
    saved_files = []
    for file in files:
        if file.filename:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            saved_files.append(filepath)
    
    # Start processing in background
    thread = threading.Thread(target=process_files, args=(saved_files, language, output_name))
    thread.start()
    
    return jsonify({"message": "Processing started", "files": len(saved_files)})

@app.route('/logs')
def get_logs():
    logs = []
    while not log_queue.empty():
        logs.append(log_queue.get())
    return jsonify({"logs": logs, "status": processing_status})

@app.route('/download/<filename>')
def download(filename):
    # Thêm .txt extension nếu chưa có
    if not filename.endswith('.txt'):
        filename = filename + '.txt'
    file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    return send_file(file_path, as_attachment=True, download_name=filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
