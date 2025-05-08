import streamlit as st
import os
import time
import tempfile
import yt_dlp
from pathlib import Path # pathlib을 사용하는 것이 좋습니다.

def main():
    st.set_page_config(
        page_title="유튜브 다운로더",
        page_icon="🎬",
        layout="centered"
    )
    
    st.title("🎬 유튜브 다운로더")
    st.write("유튜브 영상을 MP4 파일로 다운로드하세요!")
    
    # 유튜브 URL 입력
    url = st.text_input("유튜브 URL을 입력하세요:")
    
    # 화질 선택 옵션
    resolutions = ["1080p", "720p", "480p", "360p"] # 고정된 해상도 목록
    selected_resolution = st.selectbox("화질을 선택하세요:", resolutions)
    
    # 임시 디렉토리 설정
    temp_dir = tempfile.gettempdir()
    
    if url:
        try:
            # 비디오 정보 가져오기
            with st.spinner("영상 정보를 가져오는 중..."):
                video_info = get_video_info(url)
            
            if video_info:
                # 영상 정보 표시
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.image(video_info.get('thumbnail'), width=200, caption="썸네일")
                
                with col2:
                    st.subheader(video_info.get('title', '제목 없음'))
                    st.write(f"**채널:** {video_info.get('uploader', '알 수 없음')}")
                    st.write(f"**길이:** {format_duration(video_info.get('duration', 0))}")
                    if 'view_count' in video_info:
                        st.write(f"**조회수:** {format_views(video_info.get('view_count', 0))}")
                
                # 사용 가능한 형식 표시
                show_available_formats(video_info)
                
                # 다운로드 버튼
                if st.button("다운로드 시작"):
                    # video_info에서 제목을 가져오되, 없을 경우 기본값 사용
                    video_title = video_info.get('title', 'youtube_video')
                    download_path_str = download_video(url, selected_resolution, temp_dir, video_title)
                    
                    if download_path_str:
                        download_path = Path(download_path_str) # 문자열을 Path 객체로 변환
                        if download_path.exists():
                            with open(download_path, "rb") as file:
                                st.download_button(
                                    label="MP4 파일 다운로드",
                                    data=file,
                                    file_name=f"{download_path.name}", # Path 객체에서 파일 이름 사용
                                    mime="video/mp4",
                                )
                            st.success(f"'{download_path.name}' 다운로드 준비 완료! 위 버튼을 클릭하여 다운로드하세요.")
                        else:
                            st.error("다운로드된 파일을 찾을 수 없습니다. 다시 시도해 주세요.")
                    else:
                        st.error("선택한 화질로 다운로드할 수 없습니다. 다른 화질을 선택하거나 URL을 확인해 주세요.")
            else:
                # get_video_info에서 이미 오류 메시지를 표시했을 수 있음
                st.warning("영상 정보를 가져오지 못했습니다. URL을 확인하거나 잠시 후 다시 시도해 주세요.")
        
        except Exception as e:
            st.error(f"알 수 없는 오류가 발생했습니다: {str(e)}")
            # 개발/디버깅 목적으로 콘솔에 전체 오류 로깅
            print(f"Main function error: {e}", exc_info=True)

def get_video_info(url):
    """yt-dlp를 사용하여 비디오 정보를 가져옵니다"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'noplaylist': True, # 단일 영상 다운로드를 위해 플레이리스트 처리 방지
        # 'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', # 정보 추출 시에는 특정 포맷을 지정하지 않는 것이 좋음
                                                                            # 모든 사용 가능한 포맷 정보를 가져오도록 함
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
    except yt_dlp.utils.DownloadError as e:
        # yt-dlp 관련 오류 (네트워크, 영상 접근 불가 등)
        st.error(f"영상 정보 로딩 중 오류 발생 (yt-dlp): {str(e)}. URL이 정확한지, 영상이 공개 상태인지 확인해주세요.")
        print(f"yt-dlp DownloadError in get_video_info: {e}") # 서버 로그용
        return None
    except Exception as e:
        # 기타 예외
        st.error(f"영상 정보 로딩 중 알 수 없는 오류 발생: {str(e)}")
        print(f"Unexpected error in get_video_info: {e}") # 서버 로그용
        return None

def show_available_formats(video_info):
    """사용 가능한 MP4 형식을 표시합니다 (비디오+오디오 결합)"""
    if 'formats' in video_info:
        st.write("---")
        st.write("#### 사용 가능한 MP4 스트림 (비디오+오디오)")
        
        # 비디오+오디오가 함께 있는 MP4 형식만 필터링
        # 'height'가 있고, 'acodec'과 'vcodec'이 'none'이 아닌 경우
        mp4_formats = [
            f for f in video_info['formats'] 
            if f.get('ext') == 'mp4' and 
               f.get('vcodec') != 'none' and 
               f.get('acodec') != 'none' and
               f.get('height') is not None # 높이 정보가 있는 것만
        ]
        
        if mp4_formats:
            # 높이 기준으로 내림차순 정렬
            for fmt in sorted(mp4_formats, key=lambda x: x.get('height', 0), reverse=True):
                resolution = f"{fmt.get('height')}p"
                filesize = fmt.get('filesize') or fmt.get('filesize_approx') # filesize_approx도 고려
                
                format_note = fmt.get('format_note', '')
                fps = f", {fmt.get('fps')}fps" if fmt.get('fps') else ""
                
                display_text = f"• {resolution} ({format_note}{fps})"
                if filesize:
                    filesize_str = format_size(filesize)
                    display_text += f", 예상 크기: {filesize_str}"
                st.write(display_text)
        else:
            st.write("결합된 MP4 형식으로 다운로드할 수 있는 스트림을 찾을 수 없습니다. (영상 또는 오디오만 있는 스트림은 제외됩니다)")
        
        st.write("---")

def download_video(url, resolution, temp_dir, title):
    """yt-dlp를 사용하여 유튜브 영상을 다운로드합니다"""
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    resolution_num = resolution.replace('p', '')
    # format_str: 선택한 해상도 이하의 MP4 비디오와 M4A 오디오를 결합하거나, 이미 결합된 MP4를 찾음
    # ffmpeg이 필요할 수 있음에 유의
    format_str = (
        f'bestvideo[height<={resolution_num}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={resolution_num}][ext=mp4]'
        f'/best[height<={resolution_num}][ext=mp4]'
        f'/best[ext=mp4]' # 해상도 무관 MP4
        f'/best' # 최후의 수단
    )
    
    # 안전한 파일명 생성 (Pathlib 사용 권장)
    safe_title = "".join([c if c.isalnum() or c in [' ', '_', '-'] else "_" for c in title])
    safe_title = safe_title.replace(' ', '_') # 공백을 밑줄로 변경
    output_filename = f"{safe_title}_{resolution}.mp4"
    output_path = Path(temp_dir) / output_filename # pathlib 사용

    # 이전 다운로드 파일이 있다면 삭제 (선택 사항)
    if output_path.exists():
        try:
            output_path.unlink()
        except OSError as e:
            status_text.warning(f"기존 파일 삭제 실패: {e}. 덮어쓸 수 있습니다.")

    class ProgressHook:
        def __init__(self):
            self.start_time = time.time()
            
        def __call__(self, d):
            if d['status'] == 'downloading':
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                downloaded_bytes = d.get('downloaded_bytes', 0)
                
                if total_bytes > 0:
                    percentage = downloaded_bytes / total_bytes
                    progress_bar.progress(percentage)
                    
                    elapsed = time.time() - self.start_time
                    speed = downloaded_bytes / elapsed if elapsed > 0 else 0
                    
                    status_text.text(
                        f"{percentage:.1%} 다운로드 중... "
                        f"({format_size(downloaded_bytes)}/{format_size(total_bytes)}, "
                        f"{format_size(speed)}/s)"
                    )
            elif d['status'] == 'finished':
                status_text.text(f"다운로드 완료! 파일명: {d.get('filename', output_path.name)}. 후처리 중일 수 있습니다...")
                progress_bar.progress(1.0) # Ensure progress bar is full
            elif d['status'] == 'error':
                status_text.error(f"다운로드 중 오류 발생 (yt-dlp hook): {d.get('error', '알 수 없는 오류')}")
                print(f"yt-dlp hook error: {d}") # 서버 로그용

    progress_hook = ProgressHook()
    
    ydl_opts = {
        'format': format_str,
        'outtmpl': str(output_path), # yt-dlp는 문자열 경로를 기대
        'progress_hooks': [progress_hook],
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'ffmpeg_location': '/usr/bin/ffmpeg', # 시스템에 ffmpeg이 설치된 경로 명시 (선택 사항, 환경에 따라 다름)
                                           # 또는 PATH에 ffmpeg이 있어야 함
        'postprocessors': [{ # MP4로 확실히 변환하기 위한 설정
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
        # 'verbose': True, # 디버깅 시 상세 로그 출력
    }
    
    try:
        status_text.text(f"{resolution} 화질로 다운로드를 시도합니다...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # 다운로드가 성공적으로 완료되었는지 확인
        if output_path.exists() and output_path.stat().st_size > 0:
            status_text.success(f"'{output_path.name}' 다운로드 및 처리 완료!")
            return str(output_path)
        else:
            # 이 경우는 yt-dlp가 오류를 발생시키지 않았지만 파일이 생성되지 않은 경우
            status_text.error("다운로드 후 파일이 생성되지 않았거나 파일 크기가 0입니다. 다른 화질을 시도하거나 로그를 확인하세요.")
            if not output_path.exists():
                 print(f"Download finished but output file {output_path} does not exist.")
            elif output_path.stat().st_size == 0:
                 print(f"Download finished but output file {output_path} is empty.")
            return None

    except yt_dlp.utils.DownloadError as e:
        error_message = str(e)
        status_text.error(f"다운로드 실패 (yt-dlp): {error_message}")
        if "ffmpeg" in error_message.lower() or "postprocessing" in error_message.lower():
            st.info("이 오류는 ffmpeg이 설치되지 않았거나 경로가 올바르지 않을 때 발생할 수 있습니다. "
                    "MP4 변환 및 일부 고화질 다운로드에는 ffmpeg이 필요합니다.")
        print(f"yt-dlp DownloadError in download_video: {e}") # 서버 로그용
        return None
    except Exception as e:
        status_text.error(f"다운로드 중 알 수 없는 오류 발생: {str(e)}")
        print(f"Unexpected error in download_video: {e}", exc_info=True) # 서버 로그용
        return None

def format_duration(seconds_total):
    """초를 시:분:초 형식으로 변환"""
    if not isinstance(seconds_total, (int, float)) or seconds_total < 0:
        return "알 수 없음"
    seconds_total = int(seconds_total)
    hours = seconds_total // 3600
    minutes = (seconds_total % 3600) // 60
    seconds = seconds_total % 60
    
    if hours > 0:
        return f"{hours}시간 {minutes}분 {seconds}초"
    elif minutes > 0:
        return f"{minutes}분 {seconds}초"
    else:
        return f"{seconds}초"

def format_views(views):
    """조회수를 읽기 쉬운 형식으로 변환"""
    if not isinstance(views, (int, float)) or views < 0:
        return "알 수 없음"
    views = int(views)
    if views >= 1_000_000_000: # 10억
        return f"{views / 1_000_000_000:.1f}B" # Billion
    if views >= 1_000_000: # 100만
        return f"{views / 1_000_000:.1f}M" # Million
    elif views >= 1_000: # 1천
        return f"{views / 1_000:.1f}K" # Kilo
    else:
        return str(views)

def format_size(size_bytes):
    """바이트를 읽기 쉬운 형식으로 변환"""
    if not isinstance(size_bytes, (int, float)) or size_bytes < 0:
        return "0 B"
    if size_bytes == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    i = 0
    while size_bytes >= 1024 and i < len(units) - 1:
        size_bytes /= 1024
        i += 1
    return f"{size_bytes:.2f} {units[i]}"

if __name__ == "__main__":
    # Streamlit 앱을 실행하려면 터미널에서 `streamlit run your_script_name.py` 명령을 사용하세요.
    # 이 부분은 직접 실행 시에는 동작하지 않으며, Streamlit이 main()을 호출합니다.
    main()
