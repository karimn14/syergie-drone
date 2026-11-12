# Test script for Roboflow API with enhanced error handling
from inference_sdk import InferenceHTTPClient
import logging
import traceback

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_roboflow_workflow():
    """Test Roboflow Workflow API with comprehensive error handling"""
    
    # Configuration
    API_KEY = "Pocq0zfIpMM4NSTIESk2"
    WORKSPACE = "palmset"
    WORKFLOW_ID = "detect-count-and-visualize-5"
    TEST_IMAGE = "test1.jpeg"
    
    print("🧪 Testing Roboflow Workflow API...")
    print("=" * 50)
    
    try:
        # 1. Validate inputs
        if not API_KEY or API_KEY == "YOUR_API_KEY_HERE":
            print("❌ Please set a valid API key")
            return False
            
        if not WORKSPACE or not WORKFLOW_ID:
            print("❌ Missing workspace or workflow ID")
            return False
        
        # 2. Initialize client
        print("🔧 Initializing InferenceHTTPClient...")
        client = InferenceHTTPClient(
            api_url="https://serverless.roboflow.com",
            api_key=API_KEY
        )
        
        print("✅ Client initialized successfully")
        
        # 3. Check if test image exists
        import os
        if not os.path.exists(TEST_IMAGE):
            print(f"⚠️ Test image '{TEST_IMAGE}' not found, using synthetic test...")
            # Create a simple test image
            create_test_image(TEST_IMAGE)
        
        # 4. Run workflow
        print("🚀 Sending request to Roboflow Workflow...")
        result = client.run_workflow(
            workspace_name=WORKSPACE,
            workflow_id=WORKFLOW_ID,
            images={
                "image": TEST_IMAGE
            },
            use_cache=True
        )
        
        print("✅ Workflow executed successfully!")
        
        # 5. Analyze result
        print("\n📊 Response Analysis:")
        print(f"   Result type: {type(result)}")
        
        if isinstance(result, dict):
            print(f"   Keys in result: {list(result.keys())}")
            
            # Look for predictions
            predictions_found = False
            if 'predictions' in result:
                predictions = result['predictions']
                print(f"   📍 Predictions found: {len(predictions)}")
                predictions_found = True
                
                # Show sample predictions
                if predictions:
                    print(f"   Sample prediction: {predictions[0]}")
            
            # Look for results in workflow steps
            if 'results' in result:
                print(f"   🔍 Workflow results structure: {type(result['results'])}")
                if isinstance(result['results'], dict):
                    for step, step_result in result['results'].items():
                        print(f"     Step '{step}': {type(step_result)}")
                        if isinstance(step_result, dict) and 'predictions' in step_result:
                            preds = step_result['predictions']
                            print(f"       Predictions in step: {len(preds)}")
                            predictions_found = True
            
            if not predictions_found:
                print("   ⚠️ No predictions found in expected formats")
                print("   Full result structure:")
                import json
                print(json.dumps(result, indent=2)[:500] + "..." if len(str(result)) > 500 else json.dumps(result, indent=2))
        
        elif isinstance(result, list):
            print(f"   📍 List result with {len(result)} items")
            if result:
                print(f"   First item: {result[0]}")
        
        else:
            print(f"   Unexpected result type: {type(result)}")
            print(f"   Result: {result}")
        
        print("\n🎉 Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        print("\n🔍 Debug information:")
        print(f"   Error type: {type(e).__name__}")
        print(f"   API Key length: {len(API_KEY) if API_KEY else 0}")
        print(f"   Workspace: {WORKSPACE}")
        print(f"   Workflow ID: {WORKFLOW_ID}")
        
        # Print full traceback for debugging
        traceback.print_exc()
        
        return False

def create_test_image(filename, size=(640, 640)):
    """Create a simple test image"""
    import cv2
    import numpy as np
    
    # Create a simple image with some shapes
    img = np.ones((size[1], size[0], 3), dtype=np.uint8) * 150
    
    # Add some colored rectangles
    cv2.rectangle(img, (100, 100), (200, 200), (0, 255, 0), -1)  # Green
    cv2.rectangle(img, (300, 150), (400, 250), (255, 0, 0), -1)  # Blue
    cv2.rectangle(img, (500, 200), (600, 300), (0, 0, 255), -1)  # Red
    
    # Add some circles
    cv2.circle(img, (150, 400), 30, (255, 255, 0), -1)  # Cyan
    cv2.circle(img, (350, 450), 40, (255, 0, 255), -1)  # Magenta
    cv2.circle(img, (550, 350), 35, (0, 255, 255), -1)  # Yellow
    
    # Save the image
    cv2.imwrite(filename, img)
    print(f"📁 Created test image: {filename}")

if __name__ == "__main__":
    success = test_roboflow_workflow()
    
    if success:
        print("\n🎊 All tests passed! The Roboflow API is working correctly.")
    else:
        print("\n💡 Troubleshooting tips:")
        print("   1. Check your API key is correct and active")
        print("   2. Verify the workspace and workflow ID exist")
        print("   3. Check your internet connection")
        print("   4. Ensure inference-sdk is installed: pip install inference-sdk")
        print("   5. Contact Roboflow support if issues persist")