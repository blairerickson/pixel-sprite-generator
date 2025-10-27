"""Quick test of sprite generation"""
import requests
import time
import json

API_BASE = 'http://127.0.0.1:8000'

print("Testing Pixel Sprite Generator...")
print("=" * 60)

# Test health
print("\n[1] Checking backend health...")
try:
    health = requests.get(f'{API_BASE}/health').json()
    print(f"    Status: {health['status']}")
    print(f"    Backend: {health['backend']}")
except Exception as e:
    print(f"    ERROR: {e}")
    exit(1)

# Start generation
print("\n[2] Starting generation...")
try:
    response = requests.post(f'{API_BASE}/generate', json={
        'prompt': 'pixel art knight warrior, blue armor',
        'preset': 'character_sprite',
        'batch_size': 1,
        'remove_background': True,
        'process_sprites': True
    })
    job = response.json()
    print(f"    Job ID: {job['job_id']}")
    print(f"    Status: {job['status']}")
except Exception as e:
    print(f"    ERROR: {e}")
    print(f"    Response: {response.text if 'response' in locals() else 'No response'}")
    exit(1)

# Poll for completion
print("\n[3] Waiting for generation...")
job_id = job['job_id']
for i in range(120):  # 2 minutes max
    time.sleep(1)
    try:
        status = requests.get(f'{API_BASE}/jobs/{job_id}').json()
        progress = int(status.get('progress', 0) * 100)
        print(f"    Progress: {progress}% - {status['message']}")
        
        if status['status'] == 'completed':
            print("\n✅ SUCCESS!")
            print(f"\nResults:")
            result = status['result']
            for idx, img in enumerate(result['images']):
                print(f"  Image {idx+1}:")
                print(f"    Original: {img['original']}")
                if img.get('processed'):
                    print(f"    Processed: {img['processed']}")
                if img.get('sprites'):
                    print(f"    Extracted {len(img['sprites'])} sprites")
            print(f"\nSeed: {result.get('seed', 'N/A')}")
            print(f"\nOpen: http://127.0.0.1:8010/index.html")
            break
        elif status['status'] == 'failed':
            print(f"\n[FAILED] {status.get('error', 'Unknown error')}")
            break
    except Exception as e:
        print(f"    Polling error: {e}")
        time.sleep(2)
else:
    print("\n⏱️ Timeout waiting for generation")

print("\n" + "=" * 60)

