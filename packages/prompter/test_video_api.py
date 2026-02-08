# test_video_api.py - Test video workflow using correct API format

import json
import copy
import time
import sys
sys.path.insert(0, "C:/comfyui-prompter")

from comfyui_agent_sdk.client import ComfyUIClient

def test_video_api():
    api = ComfyUIClient()

    if not api.is_available():
        print("ERROR: ComfyUI is not running!")
        return

    print("ComfyUI is running!")

    # Load the correct API format workflow
    with open("C:/comfyui-prompter/wan_i2v_api_format.json", "r") as f:
        workflow = json.load(f)

    print(f"Loaded API format workflow with {len(workflow)} nodes")

    # Modify the workflow
    workflow_copy = copy.deepcopy(workflow)

    # Change the positive prompt (node 3)
    new_prompt = "a cat slowly walking, smooth motion, cinematic"
    workflow_copy["3"]["inputs"]["text"] = new_prompt
    print(f"Set positive prompt to: {new_prompt}")

    # Change the input image (node 16)
    new_image = "ComfyUI_00035_.png"
    workflow_copy["16"]["inputs"]["image"] = new_image
    print(f"Set input image to: {new_image}")

    # Randomize seed (node 7)
    import random
    new_seed = random.randint(1, 999999999999999)
    workflow_copy["7"]["inputs"]["seed"] = new_seed
    print(f"Set seed to: {new_seed}")

    # Queue it
    print("\nQueueing workflow...")
    result = api.queue_prompt(workflow_copy)

    if result:
        prompt_id = result.get('prompt_id')
        print(f"\n=== Workflow queued! ===")
        print(f"Prompt ID: {prompt_id}")
        print("Check ComfyUI to see the progress...")
        print("\nMonitoring job (this will take ~10 minutes)...")

        # Monitor for up to 15 minutes
        for i in range(300):
            time.sleep(3)
            status = api.get_job_status(prompt_id)

            if i % 10 == 0:  # Print every 30 seconds
                print(f"[{i*3}s] Status: {status['status']}")

            if status['status'] == 'completed':
                print(f"\n=== COMPLETED! ===")
                print(f"Outputs: {status['outputs']}")
                return True
            elif status['status'] == 'error':
                print(f"\n=== ERROR ===")
                print(f"Error: {status['error']}")
                return False
    else:
        print("ERROR: Failed to queue workflow!")
        return False

if __name__ == "__main__":
    test_video_api()
