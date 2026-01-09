import time
import json
import httpx

def test_slower_streaming():
    """Test with a prompt that takes longer to generate."""
    print("=" * 60)
    print("SLOW STREAMING TEST (longer prompt)")
    print("=" * 60)

    api_key = "59e293a0619b4844b1bd3e6d03291894.Hwq4vGCGaqcSVqVO"

    start_time = time.time()
    chunk_times = []

    with httpx.Client(timeout=60.0) as client:
        try:
            print("Starting request...")
            with client.stream(
                'POST',
                'https://api.z.ai/api/paas/v4/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': 'GLM-4.5-Air',
                    'messages': [{'role': 'user', 'content': 'Write a detailed 10-line poem about spring with deep metaphors about life and rebirth.'}],
                    'stream': True,
                    'max_tokens': 300
                }
            ) as response:
                print(f"Response started at: {(time.time() - start_time)*1000:.0f}ms")
                print("-" * 60)

                for line in response.iter_lines():
                    if line:
                        chunk_time = time.time() - start_time
                        chunk_times.append(chunk_time)

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
                                    # Show every few chunks to reduce output
                                    if len(chunk_times) % 3 == 0:
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
            print(f"Time between chunks:")
            print(f"  Min: {min(gaps)*1000:.0f}ms")
            print(f"  Max: {max(gaps)*1000:.0f}ms")
            print(f"  Avg: {sum(gaps)/len(gaps)*1000:.0f}ms")

        # Check spread
        time_spread = chunk_times[-1] - chunk_times[0]
        print(f"\nTime spread (first to last): {time_spread:.3f}s")

        print("\n" + "-" * 60)
        if time_spread < 0.5:
            print("BUFFERED - All chunks arrived within 500ms")
        elif time_spread < 2.0:
            print("PARTIAL - Chunks arrived within 2 seconds")
        else:
            print("STREAMING - Chunks spread over >2 seconds")
        print("-" * 60)

if __name__ == "__main__":
    test_slower_streaming()
