import time
import sys
import os

# Add app to path
sys.path.insert(0, '/app')

os.chdir('/app')

from app.core.glm import get_glm_client
from app.models.transcription import Transcription
from app.db.session import SessionLocal

def test_streaming_timing():
    """Test if streaming is actually progressive or buffered."""
    print("=" * 60)
    print("STREAMING TIMING DIAGNOSTIC TEST")
    print("=" * 60)

    # Get latest transcription with text
    db = SessionLocal()
    transcription = db.query(Transcription).filter(
        Transcription.storage_path.isnot(None)
    ).order_by(Transcription.created_at.desc()).first()

    if not transcription:
        print("ERROR: No transcription found with text!")
        return

    print(f"\nUsing transcription: {transcription.file_name}")
    print(f"Text length: {len(transcription.text)} characters")
    print(f"Created at: {transcription.created_at}")
    print("\n" + "-" * 60)
    print("Starting streaming test...")
    print("Question: \"什么是共修？\"")
    print("-" * 60 + "\n")

    # Test streaming
    glm_client = get_glm_client()
    chunks_with_times = []
    start_time = time.time()

    try:
        for chunk in glm_client.chat_stream(
            question="什么是共修？用简洁的语言回答。",
            transcription_context=transcription.text[:2000],  # Limit context for speed
            chat_history=[]
        ):
            chunk_time = time.time() - start_time
            chunks_with_times.append((chunk_time, chunk))

            # Parse content from SSE format
            if chunk.startswith("data: "):
                import json
                json_str = chunk[6:].strip()
                if json_str:
                    try:
                        data = json.loads(json_str)
                        if "content" in data and not data.get("done"):
                            content_preview = data["content"][:30].replace("\n", "\\n")
                            print(f"[{chunk_time:6.3f}s] Chunk #{len(chunks_with_times)}: {content_preview}...")
                    except:
                        pass

    except Exception as e:
        print(f"ERROR during streaming: {e}")
        import traceback
        traceback.print_exc()
        return

    # Analyze timing
    print("\n" + "=" * 60)
    print("TIMING ANALYSIS")
    print("=" * 60)

    if not chunks_with_times:
        print("ERROR: No chunks received!")
        return

    times = [t for t, _ in chunks_with_times]
    total_time = times[-1] if times else 0
    chunk_count = len(chunks_with_times)

    print(f"\nTotal chunks: {chunk_count}")
    print(f"Total time: {total_time:.3f}s ({total_time*1000:.0f}ms)")
    if total_time > 0:
        print(f"Average chunk rate: {chunk_count/total_time:.1f} chunks/second")

    if chunk_count > 1:
        gaps = [times[i] - times[i-1] for i in range(1, len(times))]
        min_gap = min(gaps) * 1000
        max_gap = max(gaps) * 1000
        avg_gap = sum(gaps) / len(gaps) * 1000

        print(f"\nTime between chunks:")
        print(f"  Minimum: {min_gap:.0f}ms")
        print(f"  Maximum: {max_gap:.0f}ms")
        print(f"  Average: {avg_gap:.0f}ms")

        # Determine if streaming is real or buffered
        print("\n" + "-" * 60)
        print("DIAGNOSIS:")
        print("-" * 60)

        # If 90% of gaps are under 100ms, it's buffered
        fast_gaps = [g for g in gaps if g < 0.1]
        if len(gaps) > 0:
            fast_ratio = len(fast_gaps) / len(gaps)
        else:
            fast_ratio = 0

        if fast_ratio > 0.9:
            print(f"BUFFERED STREAMING DETECTED!")
            print(f"   {fast_ratio*100:.0f}% of chunks arrived within 100ms of each other")
            print(f"   This suggests the response was buffered server-side")
            print(f"   and all chunks were sent at once, not progressively.")
        elif max_gap < 500:
            print(f"POSSIBLE BUFFERING")
            print(f"   All chunks arrived within {max_gap:.0f}ms")
            print(f"   This may indicate some buffering is occurring")
        else:
            print(f"TRUE STREAMING DETECTED!")
            print(f"   Chunks are spread over {total_time:.1f} seconds")
            print(f"   Average gap of {avg_gap:.0f}ms indicates progressive delivery")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_streaming_timing()
