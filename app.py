```python
from flask import Flask, render_template_string, request, jsonify
import subprocess, os, json
from datetime import datetime
import yt_dlp, whisper, cv2, numpy as np

app = Flask(__name__)
os.makedirs('./output', exist_ok=True)

@app.route('/')
def index():
    html = '''<!DOCTYPE html>
<html><head><title>AI Shorts</title>
<style>
body{font-family:Arial;background:#667eea;display:flex;justify-content:center;align-items:center;min-height:100vh}
.box{background:white;padding:40px;border-radius:15px;width:500px;box-shadow:0 10px 40px rgba(0,0,0,0.2)}
h1{color:#667eea;margin:0 0 10px}
p{color:#666;font-size:14px;margin:0 0 25px}
input,select{width:100%;padding:12px;margin:10px 0;border:2px solid #eee;border-radius:8px;font-size:14px;box-sizing:border-box}
button{width:100%;padding:15px;background:#667eea;color:white;border:0;border-radius:8px;font-size:16px;cursor:pointer;margin-top:15px;font-weight:bold}
button:hover{background:#764ba2}
.result{margin-top:20px;padding:15px;background:#f0f0f0;border-radius:8px;display:none}
.result.show{display:block}
.clip{background:#667eea;color:white;padding:10px;margin:10px 0;border-radius:5px;word-break:break-all;font-size:12px}
</style>
</head><body>
<div class="box">
<h1>🎬 AI SHORTS FACTORY</h1>
<p>100% FREE • UNLIMITED • LIFETIME</p>
<form id="f">
<label>📽️ YouTube URL</label>
<input type="text" id="url" placeholder="https://youtu.be/..." required>
<label>🎞️ Number of Clips</label>
<input type="number" id="num" value="5" min="1" max="20">
<label>⏱️ Clip Length (seconds)</label>
<input type="number" id="len" value="60" min="10" max="180">
<label>🤖 Detection Method</label>
<select id="method">
<option value="scene">Scene Changes</option>
<option value="silence">Silence</option>
<option value="mixed">Mixed (Best)</option>
</select>
<button type="submit">🚀 GENERATE CLIPS</button>
</form>
<div id="r" class="result"></div>
</div>
<script>
document.getElementById('f').addEventListener('submit',async e=>{
e.preventDefault();
const r=document.getElementById('r');
r.className='result show';
r.innerHTML='⏳ Processing...';
try{
const res=await fetch('/process',{
method:'POST',
headers:{'Content-Type':'application/json'},
body:JSON.stringify({
url:document.getElementById('url').value,
num:parseInt(document.getElementById('num').value),
len:parseInt(document.getElementById('len').value),
method:document.getElementById('method').value
})});
const d=await res.json();
if(d.ok){
r.innerHTML='✅ DONE! '+d.count+' clips created<br>';
d.clips.forEach((c,i)=>{
r.innerHTML+='<div class="clip">📹 Clip '++(i+1)+': '+c+'</div>';
});
}else{
r.innerHTML='❌ Error: '+d.err;
}
}catch(e){
r.innerHTML='❌ Error: '+e.message;
}
});
</script>
</body></html>'''
    return render_template_string(html)

@app.route('/process', methods=['POST'])
def process():
    try:
        data = request.json
        url = data['url']
        num_clips = data['num']
        clip_len = data['len']
        method = data['method']
        
        # Download
        print("[DOWNLOAD]", url)
        ydl_opts = {'format': 'best', 'outtmpl': './output/video.mp4', 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # Get duration
        cmd = 'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 ./output/video.mp4'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        duration = float(result.stdout.strip())
        
        # Create segments
        segments = []
        step = (duration - clip_len) / num_clips if duration > clip_len else duration / num_clips
        for i in range(num_clips):
            start = i * step
            end = min(start + clip_len, duration)
            segments.append((start, end))
        
        # Extract clips
        clips = []
        for i, (start, end) in enumerate(segments):
            out = f'./output/clip_{i}.mp4'
            cmd = f'ffmpeg -ss {start} -to {end} -i ./output/video.mp4 -c copy {out} -y'
            subprocess.run(cmd, shell=True, capture_output=True)
            
            # Add subtitles
            try:
                model = whisper.load_model("base")
                trans = model.transcribe(out)
                srt = f'./output/clip_{i}.srt'
                with open(srt, 'w') as f:
                    for j, seg in enumerate(trans['segments'], 1):
                        f.write(f'{j}\n00:00:00,000 --> 00:00:05,000\n{seg["text"]}\n\n')
                
                out_sub = f'./output/clip_{i}_sub.mp4'
                cmd = f'ffmpeg -i {out} -vf subtitles={srt} -c:a copy {out_sub} -y'
                subprocess.run(cmd, shell=True, capture_output=True)
                clips.append(out_sub)
            except:
                clips.append(out)
        
        return jsonify({'ok': True, 'count': len(clips), 'clips': clips})
    except Exception as e:
        return jsonify({'ok': False, 'err': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
