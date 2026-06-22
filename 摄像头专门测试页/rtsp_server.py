"""
RTSP → HLS relay. Each camera gets HLS segments served via HTTP.
Open http://127.0.0.1:8088/cam_test.html in browser.
"""
import subprocess, sys, os, shutil, time
from http.server import HTTPServer, SimpleHTTPRequestHandler

FFMPEG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg.exe')
HLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hls_output')
PORT = 8088

CAMERAS = [
    ('摄像头1', 'rtsp://admin:Admin123@192.168.2.14:554'),
    ('摄像头2', 'rtsp://admin:Admin123@192.168.2.13:554'),
    ('摄像头3', 'rtsp://admin:Admin123@192.168.2.12:554'),
    ('摄像头4', 'rtsp://admin:Admin123@192.168.2.11:554'),
]

processes = []

def start_camera(name, rtsp_url, index):
    """Run ffmpeg to convert RTSP → HLS segments."""
    cam_dir = os.path.join(HLS_DIR, f'cam{index}')
    os.makedirs(cam_dir, exist_ok=True)
    # Clean old segments
    for f in os.listdir(cam_dir):
        os.remove(os.path.join(cam_dir, f))

    m3u8_path = os.path.join(cam_dir, 'index.m3u8')

    cmd = [
        FFMPEG,
        '-rtsp_transport', 'tcp',
        '-i', rtsp_url,
        '-c:v', 'copy',           # Copy H.264 without re-encoding
        '-an',                      # No audio
        '-hls_time', '2',           # 2-second segments
        '-hls_list_size', '5',      # Keep 5 segments in playlist
        '-hls_flags', 'delete_segments+append_list',
        '-hls_segment_filename', os.path.join(cam_dir, 'seg_%03d.ts'),
        m3u8_path,
    ]

    print(f'[{name}] Starting HLS: {rtsp_url}')
    while True:
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            processes.append(proc)
            proc.wait()
            print(f'[{name}] ffmpeg stopped (code={proc.returncode}), restarting in 2s...')
            time.sleep(2)
        except Exception as e:
            print(f'[{name}] Error: {e}')
            time.sleep(2)

class CORSHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.dirname(os.path.abspath(__file__)), **kwargs)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    def log_message(self, format, *args):
        # Quieter logging
        if '/hls_output/' in str(args):
            return
        super().log_message(format, *args)

if __name__ == '__main__':
    print('=== RTSP → HLS Relay ===')
    print(f'ffmpeg: {FFMPEG} (OK: {os.path.exists(FFMPEG)})')
    print(f'HLS dir: {HLS_DIR}')

    # Clean and create HLS dirs
    if os.path.exists(HLS_DIR):
        shutil.rmtree(HLS_DIR)
    os.makedirs(HLS_DIR)

    # Start ffmpeg for each camera
    import threading
    for i, (name, url) in enumerate(CAMERAS):
        t = threading.Thread(target=start_camera, args=(name, url, i+1), daemon=True)
        t.start()

    # Wait for ffmpeg to create first segments
    print('\nWaiting for HLS segments (ffmpeg starting)...')
    time.sleep(5)

    # Check what was created
    for i in range(1, 5):
        cam_dir = os.path.join(HLS_DIR, f'cam{i}')
        files = os.listdir(cam_dir) if os.path.exists(cam_dir) else []
        print(f'  cam{i}: {len(files)} files - {files}')

    # Start HTTP server
    print(f'\n=== HTTP server at http://127.0.0.1:{PORT} ===')
    print(f'Open: http://127.0.0.1:{PORT}/cam_test.html\n')

    server = HTTPServer(('127.0.0.1', PORT), CORSHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nShutting down...')
        for p in processes:
            p.terminate()
        server.shutdown()
