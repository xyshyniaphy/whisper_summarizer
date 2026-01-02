import time
import json
import sys

# Test raw HTTP streaming without OpenAI SDK
import httpx

def test_raw_http_streaming():
    """Test streaming with raw HTTP to see actual timing."""
    print("=" * 60)
    print("RAW HTTP STREAMING TEST (httpx)")
    print("=" * 60)

    api_key = "59e293a0619b4844b1bd3e6d03291894.Hwq4vGCGaqcSVqVO"

    start_time = time.time()
    chunk_times = []

    # Use httpx with streaming enabled
    with httpx.Client(timeout=30.0) as client:
        try:
            with client.stream(
                'POST',
                'https://api.z.ai/api/paas/v4/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': 'GLM-4.5-Air',
                    'messages': [{'role': 'user', 'content': 'Say "Hello streaming"'}],
                    'stream': True,
                    'max_tokens': 50
                }
            ) as response:
                print(f"\nResponse started at: {(time.time() - start_time)*1000:.0f}ms")
                print("-" * 60)

                for line in response.iter_lines():
                    if line:
                        chunk_time = time.time() - start_time
                        chunk_times.append(chunk_time)

                        line_str = line.decode() if isinstance(line, bytes) else line
                        if line_str.startswith('data: '):
                            data = line_str[6:]
                            if data == '[DONE]':
                                print(f"[{chunk_time:6.3f}s] Stream DONE")
                                break

                            try:
                                parsed = json.loads(data)
                                content = parsed.get('choices', [{}])[0].get('delta', {}).get('content', '')
                                if content:
                                    print(f"[{chunk_time:6.3f}s] {repr(content)}")
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
        print(f"Time between chunks:")
        print(f"  Min: {min(gaps)*1000:.0f}ms")
        print(f"  Max: {max(gaps)*1000:.0f}ms")
        print(f"  Avg: {sum(gaps)/len(gaps)*1000:.0f}ms")

        # Diagnosis
        fast_gaps = [g for g in gaps if g < 0.1]
        fast_ratio = len(fast_gaps) / len(gaps) if gaps else 0

        print("\n" + "-" * 60)
        if fast_ratio > 0.9:
            print("BUFFERED - All chunks arrived within 100ms of each other")
        else:
            print("STREAMING - Chunks are spread over time")
        print("-" * 60)

if __name__ == "__main__":
    test_raw_http_streaming()
