"""
Whisper.cpp 音声処理サービス
FastAPIベースのHTTPサーバーで音声ファイルを受け取り、Whisper.cppで文字起こしを実行
"""

import os
import subprocess
import json
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(title="Whisper.cpp Audio Processing Service")

# 環境変数
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "ggml-large-v3-turbo.bin")
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "ja")
WHISPER_THREADS = os.getenv("WHISPER_THREADS", "4")
MODEL_PATH = f"/app/models/{WHISPER_MODEL}"
DATA_DIR = Path("/app/data")
OUTPUT_DIR = Path("/app/output")

DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    model_exists = os.path.exists(MODEL_PATH)
    return {
        "status": "healthy" if model_exists else "unhealthy",
        "model": WHISPER_MODEL,
        "model_exists": model_exists,
        "language": WHISPER_LANGUAGE,
        "threads": WHISPER_THREADS
    }


@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    音声ファイルを文字起こし
    
    Args:
        file: 音声ファイル (m4a, mp3, wav, aac, flac, ogg)
    
    Returns:
        transcription: タイムスタンプ付き文字起こし結果
    """
    # ファイルを保存
    file_path = DATA_DIR / file.filename
    output_prefix = OUTPUT_DIR / file.filename.rsplit(".", 1)[0]
    
    try:
        # 音声ファイルを保存
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # モノラル・16kHzに変換 (Whisperの要件)
        wav_path = file_path.with_suffix(".wav")
        ffmpeg_cmd = [
            "ffmpeg",
            "-i", str(file_path),
            "-ar", "16000",  # 16kHz
            "-ac", "1",      # モノラル
            "-c:a", "pcm_s16le",  # 16-bit PCM
            "-y",
            str(wav_path)
        ]
        
        result = subprocess.run(
            ffmpeg_cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"音声変換エラー: {result.stderr}"
            )
        
        # Whisper.cppで文字起こし実行
        whisper_cmd = [
            "/app/whisper-main",
            "-m", MODEL_PATH,
            "-f", str(wav_path),
            "-l", WHISPER_LANGUAGE,
            "-t", WHISPER_THREADS,
            "-of", str(output_prefix),  # 出力ファイルプレフィックス
            "-otxt",  # テキスト形式で出力
            "-osrt",  # SRT形式で出力 (タイムスタンプ付き)
        ]
        
        result = subprocess.run(
            whisper_cmd,
            capture_output=True,
            text=True,
            timeout=600
        )
        
        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Whisper.cpp実行エラー: {result.stderr}"
            )
        
        # 結果ファイルを読み込み
        txt_file = Path(f"{output_prefix}.txt")
        srt_file = Path(f"{output_prefix}.srt")
        
        transcription_text = ""
        timestamps = []
        
        if txt_file.exists():
            with open(txt_file, "r", encoding="utf-8") as f:
                transcription_text = f.read()
        
        if srt_file.exists():
            timestamps = parse_srt(srt_file)
        
        # 一時ファイルをクリーンアップ
        file_path.unlink(missing_ok=True)
        wav_path.unlink(missing_ok=True)
        
        return JSONResponse({
            "status": "success",
            "filename": file.filename,
            "transcription": transcription_text,
            "timestamps": timestamps,
            "language": WHISPER_LANGUAGE,
            "model": WHISPER_MODEL
        })
    
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=504,
            detail="処理がタイムアウトしました"
        )
    except Exception as e:
        # エラー時はファイルをクリーンアップ
        file_path.unlink(missing_ok=True)
        if 'wav_path' in locals():
            wav_path.unlink(missing_ok=True)
        
        raise HTTPException(
            status_code=500,
            detail=f"処理エラー: {str(e)}"
        )


def parse_srt(srt_path: Path) -> list:
    """
    SRTファイルを解析してタイムスタンプ付きテキストを抽出
    
    Returns:
        [{"start": "00:00:00,000", "end": "00:00:05,000", "text": "..."}]
    """
    timestamps = []
    
    with open(srt_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    i = 0
    while i < len(lines):
        # インデックス行をスキップ
        if lines[i].strip().isdigit():
            i += 1
            # タイムスタンプ行
            if i < len(lines) and "-->" in lines[i]:
                time_parts = lines[i].strip().split(" --> ")
                start_time = time_parts[0]
                end_time = time_parts[1]
                i += 1
                
                # テキスト行
                text_lines = []
                while i < len(lines) and lines[i].strip():
                    text_lines.append(lines[i].strip())
                    i += 1
                
                timestamps.append({
                    "start": start_time,
                    "end": end_time,
                    "text": " ".join(text_lines)
                })
        i += 1
    
    return timestamps


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    )
