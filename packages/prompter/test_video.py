# test_video.py - Test the image-to-video workflow

import sys
sys.path.insert(0, "C:/comfyui-prompter")

from workflow_manager import WorkflowManager
from comfyui_agent_sdk.client import ComfyUIClient

def test_video_workflow():
    # Initialize
    wm = WorkflowManager()
    api = ComfyUIClient()

    # Check connection
    if not api.is_available():
        print("ERROR: ComfyUI is not running!")
        return

    print("ComfyUI is running!")

    # Get object info to help with conversion
    print("Fetching object info from ComfyUI...")
    object_info = api.get_object_info()
    if object_info:
        wm.set_object_info(object_info)
        print(f"Got info for {len(object_info)} node types")

    # Load the image-to-video workflow
    workflow_file = "Wan+2.1+Image+to+Video+14B+480p+Q4_K_S+GGUF.json"
    print(f"\nLoading workflow: {workflow_file}")
    workflow = wm.load_workflow(workflow_file)

    if not workflow:
        print("ERROR: Could not load workflow!")
        return

    print(f"Workflow loaded with {len(workflow.get('nodes', []))} nodes")

    # Modify the prompt for the video motion
    test_prompt = "gentle waves, smooth motion, cinematic"
    workflow = wm.modify_prompt(workflow, test_prompt, "blurry, low quality, distorted")
    print(f"Set prompt to: {test_prompt}")

    # Set a test input image
    test_image = "ComfyUI_00035_.png"
    workflow = wm.modify_image_input(workflow, test_image)
    print(f"Set input image to: {test_image}")

    # Convert to API format
    print("\nConverting to API format...")
    api_workflow = wm.convert_to_api_format(workflow)

    if not api_workflow:
        print("ERROR: Could not convert workflow!")
        return

    print(f"Converted workflow has {len(api_workflow)} nodes")

    # Show the nodes
    print("\nNodes in API workflow:")
    for node_id, node_data in api_workflow.items():
        print(f"  {node_id}: {node_data['class_type']}")

    # Queue it
    print("\nQueueing workflow...")
    result = api.queue_prompt(api_workflow)

    if result:
        prompt_id = result.get('prompt_id')
        print(f"\nWorkflow queued! Prompt ID: {prompt_id}")
        print("Check ComfyUI to see the progress...")
        print(f"\nMonitoring job for 5 minutes...")

        # Wait and check status
        import time
        for i in range(100):  # Check for up to 5 minutes
            time.sleep(3)
            status = api.get_job_status(prompt_id)
            print(f"Status: {status['status']} - Progress: {status['progress']}%")
            if status['status'] == 'completed':
                print(f"\n=== COMPLETED! ===")
                print(f"Outputs: {status['outputs']}")
                break
            elif status['status'] == 'error':
                print(f"\n=== ERROR ===")
                print(f"Error: {status['error']}")
                break
    else:
        print("ERROR: Failed to queue workflow!")

if __name__ == "__main__":
    test_video_workflow()
