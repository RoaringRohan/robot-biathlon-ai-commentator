import os
import snowflake.connector
from dotenv import load_dotenv
from ultralytics import YOLO
import glob

# Load environment variables
load_dotenv()

SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD")
SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE")
SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA")
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")
STAGE_NAME = "@VIDEO_STAGE"

TEST_DIR = "datasets/test"
os.makedirs(TEST_DIR, exist_ok=True)

def connect_to_snowflake():
    try:
        conn = snowflake.connector.connect(
            user=SNOWFLAKE_USER,
            password=SNOWFLAKE_PASSWORD,
            account=SNOWFLAKE_ACCOUNT,
            warehouse=SNOWFLAKE_WAREHOUSE,
            database=SNOWFLAKE_DATABASE,
            schema=SNOWFLAKE_SCHEMA
        )
        return conn
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return None

def download_latest_video():
    """Download ONE video for testing"""
    conn = connect_to_snowflake()
    if not conn: return None
    
    cursor = conn.cursor()
    try:
        print("⬇️ Downloading ONE test video...")
        # Just grab the latest one
        cursor.execute(f"GET {STAGE_NAME} file://{os.path.abspath(TEST_DIR)}")
        print("✅ Download complete.")
    finally:
        cursor.close()
        conn.close()

def run_inference():
    """Run model on the downloaded video"""
    # Find the trained model
    # Usually in runs/detect/cpu_run/weights/best.pt
    model_path = "biathlon_model/cpu_run/weights/best.pt"
    
    if not os.path.exists(model_path):
        print(f"⚠️ Model not found at {model_path}. Using 'yolov8n.pt' for demo.")
        model_path = "yolov8n.pt"

    print(f"🧠 Loading Model: {model_path}")
    model = YOLO(model_path)

    # Find video
    videos = glob.glob(os.path.join(TEST_DIR, "*.webm"))
    if not videos:
        print("❌ No videos found in datasets/test")
        return

    target_video = videos[0] # Pick first
    print(f"🎥 Running Inference on: {target_video} (Stream Mode)")

    # Predict and Save with Stream to save RAM
    # device='cpu' for Droplet compatibility
    results_generator = model.predict(source=target_video, save=True, project="inference_demo", name="demo_run", device='cpu', exist_ok=True, stream=True)
    
    # Iterate through generator to process frames
    for result in results_generator:
        pass # The loop triggers the processing and saving
    
    print(f"✨ Inference Complete! Video processed.")

def main():
    print("🚀 Starting Proof of Intelligence Demo")
    download_latest_video()
    run_inference()

if __name__ == "__main__":
    main()
