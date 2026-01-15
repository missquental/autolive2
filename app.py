import streamlit as st
import gdown
import os
import subprocess
import threading
import queue
import time
from pathlib import Path

# ===============================
# KONFIGURASI
# ===============================
VIDEO_DIR = "videos"
BUMPER_NAME = "bumper.mp4"
Path(VIDEO_DIR).mkdir(exist_ok=True)

# ===============================
# GOOGLE DRIVE DOWNLOAD
# ===============================
def download_drive_folder(folder_url):
    gdown.download_folder(
        folder_url,
        output=VIDEO_DIR,
        quiet=False,
        use_cookies=False
    )

def download_bumper(bumper_url):
    gdown.download(
        url=bumper_url,
        output=os.path.join(VIDEO_DIR, BUMPER_NAME),
        fuzzy=True,
        quiet=False
    )

# ===============================
# STREAM LOOP
# ===============================
def stream_playlist(stream_key, is_shorts, log_q, stop_flag):
    rtmp = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
    scale = ["-vf", "scale=720:1280"] if is_shorts else []

    while not stop_flag.is_set():
        videos = sorted([
            f for f in os.listdir(VIDEO_DIR)
            if f.endswith(".mp4") and f != BUMPER_NAME
        ])

        if not videos:
            log_q.put("❌ Tidak ada video")
            time.sleep(5)
            continue

        for vid in videos:
            if stop_flag.is_set():
                break

            bumper_path = os.path.join(VIDEO_DIR, BUMPER_NAME)
            if os.path.exists(bumper_path):
                log_q.put("🎬 Memutar bumper")
                subprocess.run([
                    "ffmpeg", "-re", "-i", bumper_path,
                    "-c:v", "libx264", "-preset", "veryfast",
                    "-b:v", "2500k", "-maxrate", "2500k",
                    "-bufsize", "5000k",
                    "-c:a", "aac", "-b:a", "128k",
                    *scale, "-f", "flv", rtmp
                ])

            video_path = os.path.join(VIDEO_DIR, vid)
            log_q.put(f"▶️ Memutar {vid}")
            subprocess.run([
                "ffmpeg", "-re", "-i", video_path,
                "-c:v", "libx264", "-preset", "veryfast",
                "-b:v", "2500k", "-maxrate", "2500k",
                "-bufsize", "5000k",
                "-c:a", "aac", "-b:a", "128k",
                *scale, "-f", "flv", rtmp
            ])

        log_q.put("🔁 Playlist ulang")

# ===============================
# STREAMLIT UI
# ===============================
st.set_page_config("Drive Folder → Live", "📡", layout="wide")
st.title("📡 Google Drive Folder → Live YouTube")

if "log_q" not in st.session_state:
    st.session_state.log_q = queue.Queue()
if "stop_flag" not in st.session_state:
    st.session_state.stop_flag = threading.Event()

# ===============================
# INPUT
# ===============================
st.subheader("🔗 Input Google Drive")

folder_url = st.text_input(
    "URL Folder Google Drive (video utama)",
    placeholder="https://drive.google.com/drive/folders/xxxx"
)

bumper_url = st.text_input(
    "URL Video Bumper Google Drive",
    placeholder="https://drive.google.com/file/d/xxxx/view"
)

# ===============================
# DOWNLOAD
# ===============================
if st.button("📥 Download dari Drive"):
    if not folder_url or not bumper_url:
        st.error("URL folder & bumper wajib diisi")
    else:
        with st.spinner("Download video utama..."):
            download_drive_folder(folder_url)
        with st.spinner("Download bumper..."):
            download_bumper(bumper_url)
        st.success("Semua video berhasil didownload")

# ===============================
# LIVE SETTING
# ===============================
st.subheader("🔴 Live Setting")
stream_key = st.text_input("Stream Key YouTube", type="password")
is_shorts = st.checkbox("Mode Shorts (9:16)")

# ===============================
# CONTROL
# ===============================
col1, col2 = st.columns(2)

with col1:
    if st.button("🚀 Mulai Live"):
        if not stream_key:
            st.error("Stream key wajib")
        else:
            st.session_state.stop_flag.clear()
            threading.Thread(
                target=stream_playlist,
                args=(stream_key, is_shorts, st.session_state.log_q, st.session_state.stop_flag),
                daemon=True
            ).start()
            st.success("Live dimulai")

with col2:
    if st.button("🛑 Stop Live"):
        st.session_state.stop_flag.set()
        os.system("pkill ffmpeg")
        st.warning("Live dihentikan")

# ===============================
# LOG
# ===============================
st.subheader("📜 Log")
logs = []
while not st.session_state.log_q.empty():
    logs.append(st.session_state.log_q.get())
st.text("\n".join(logs[-20:]))

# ===============================
# INFO
# ===============================
st.info("""
📌 **Model Input:**
- 1 URL folder Drive (video utama)
- 1 URL video Drive (bumper)

📌 **Urutan Live:**
bumper → video1 → bumper → video2 → loop
""")
