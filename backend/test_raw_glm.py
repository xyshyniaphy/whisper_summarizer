import time
import json
import httpx
import sys

sys.path.insert(0, '/app')

from app.models.transcription import Transcription
from app.db.session import SessionLocal

def test_raw_streaming_with_transcription():
    """Test raw HTTP streaming with actual transcription context."""
    print("=" * 60)
    print("RAW HTTP STREAMING WITH TRANSCRIPTION CONTEXT")
    print("=" * 60)

    api_key = "59e293a0619b4844b1bd3e6d03291894.Hwq4vGCGaqcSVqVO"

    # Get transcription
    db = SessionLocal()
    transcription = db.query(Transcription).filter(
        Transcription.storage_path.isnot(None)
    ).order_by(Transcription.created_at.desc()).first()

    if not transcription:
        print("ERROR: No transcription found")
        return

    print(f"\nTranscription: {transcription.file_name}")
    print(f"Question: \"什么是共修？\"")
    print("-" * 60)

    start_time = time.time()
    chunk_times = []

    # Build messages
    messages = [
        {"role": "system", "content": "你是一个专业的问答助手，专门基于转录文本内容回答用户的问题。\n\n重要规则：\n1. 只能根据提供的转录文本回答问题，绝对不要添加任何外部信息\n2. 如果转录文本中没有相关信息，必须明确告知用户\"转录文本中没有提到这个内容\"\n3. 使用简洁明了的中文回答\n4. 保持回答的准确性和客观性"},
        {"role": "user", "content": f"请根据以下转录文本内容回答问题：\n\n---\n转录内容:\n{transcription.text[:3000]}\n---\n\n问题: 什么是共修？"}
    ]

    try:
        with httpx.Client(timeout=60.0) as client:
            with client.stream(
                'POST',
                'https://api.z.ai/api/paas/v4/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': 'GLM-4.5-Air',
                    'messages': messages,
                    'stream': True,
                    'max_tokens': 500
                }
            ) as response:
                print(f"Response started at: {(time.time() - start_time)*1000:.0f}ms")
                print("-" * 60)

                for line in response.iter_lines():
                    if line:
                        chunk_time = time.time() - start_time
                        line_str = line.decode() if isinstance(line, bytes) else line

                        if line_str.startswith('data: '):
                            data = line_str[6:]
                            if data == '[DONE]':
                                print(f"[{chunk_time:6.3f}s] [DONE]")
                                break

                            try:
                                parsed = json.loads(data)
                                content = parsed.get('choices', [{}])[0].get('delta', {}).get('content', '')
                                if content:
                                    chunk_times.append(chunk_time)
                                    # Show every 5th chunk
                                    if len(chunk_times) % 5 == 0:
                                        preview = content[:20].replace('\n', '\\n')
                                        print(f"[{chunk_time:6.3f}s] Chunk #{len(chunk_times)}: {repr(preview)}...")
                            except:
                                pass

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return

    # Analysis
    print("\n" + "=" * 60)
    print("TIMING ANALYSIS")
    print("=" * 60)

    if len(chunk_times) > 1:
        gaps = [chunk_times[i] - chunk_times[i-1] for i in range(1, len(chunk_times))]
        print(f"Total chunks: {len(chunk_times)}")
        print(f"Total time: {chunk_times[-1]:.3f}s")
        print(f"First chunk at: {chunk_times[0]:.3f}s")
        print(f"Last chunk at: {chunk_times[-1]:.3f}s")

        if gaps:
            print(f"\nTime between chunks:")
            print(f"  Min: {min(gaps)*1000:.0f}ms")
            print(f"  Max: {max(gaps)*1000:.0f}ms")
            print(f"  Avg: {sum(gaps)/len(gaps)*1000:.0f}ms")

        time_spread = chunk_times[-1] - chunk_times[0]
        print(f"\nTime spread (first to last): {time_spread:.3f}s ({time_spread*1000:.0f}ms)")

        print("\n" + "-" * 60)
        if time_spread < 0.5:
            print("BUFFERED (<500ms spread)")
        elif time_spread < 1.0:
            print("MINIMAL STREAMING (<1s spread)")
        elif time_spread < 2.0:
            print("MODERATE STREAMING (<2s spread)")
        else:
            print("GOOD STREAMING (>2s spread)")
        print("-" * 60)

if __name__ == "__main__":
    test_raw_streaming_with_transcription()
