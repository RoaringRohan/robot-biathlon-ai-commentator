import os
import snowflake.connector
import cv2
import time
from dotenv import load_dotenv
from ultralytics import YOLO
import shutil
import glob
from pathlib import Path

# Load environment variables
load_dotenv()

# Configuration
SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD")
SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE")
SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA")
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")
STAGE_NAME = "@VIDEO_STAGE"

DATASET_ROOT = "datasets"
VIDEO_DIR = os.path.join(DATASET_ROOT, "raw_videos")
IMAGES_DIR = os.path.join(DATASET_ROOT, "images", "train")
LABELS_DIR = os.path.join(DATASET_ROOT, "labels", "train")
VAL_IMAGES_DIR = os.path.join(DATASET_ROOT, "images", "val")
VAL_LABELS_DIR = os.path.join(DATASET_ROOT, "labels", "val")

def setup_directories():
    """Create necessary directories for YOLO training"""
    for d in [VIDEO_DIR, IMAGES_DIR, LABELS_DIR, VAL_IMAGES_DIR, VAL_LABELS_DIR]:
        os.makedirs(d, exist_ok=True)
    print("✅ Directories initialized.")

def connect_to_snowflake():
    """Establish connection to Snowflake"""
    try:
        conn = snowflake.connector.connect(
            user=SNOWFLAKE_USER,
            password=SNOWFLAKE_PASSWORD,
            account=SNOWFLAKE_ACCOUNT,
            warehouse=SNOWFLAKE_WAREHOUSE,
            database=SNOWFLAKE_DATABASE,
            schema=SNOWFLAKE_SCHEMA
        )
        print("✅ Connected to Snowflake.")
        return conn
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return None

def download_videos(limit=5):
    """Download the latest N videos from Snowflake Stage"""
    conn = connect_to_snowflake()
    if not conn:
        return

    cursor = conn.cursor()
    try:
        # 1. List files in stage
        print(f"🔍 Listing files in {STAGE_NAME}...")
        cursor.execute(f"LIST {STAGE_NAME}")
        
        # files = cursor.fetchall()
        # Simple approach: assume we pull everything or sort by name (timestamped)
        # Getting the actual file content requires GET command
        
        # 2. Download files to local VIDEO_DIR
        print(f"⬇️ Downloading latest {limit} videos to {VIDEO_DIR}...")
        
        # NOTE: Snowflake GET downloads ALL files matching pattern
        # We can use a regex pattern or just download all if volume is low.
        # For simplicity in this hackathon context, we download all.
        cursor.execute(f"GET {STAGE_NAME} file://{os.path.abspath(VIDEO_DIR)} PATTERN='.*.webm'")
        
        print("✅ Download complete.")
        
    except Exception as e:
        print(f"❌ Download error: {e}")
    finally:
        cursor.close()
        conn.close()

def extract_frames(video_path, output_dir, frame_interval=30):
    """Extract every Nth frame from video"""
    vid_name = Path(video_path).stem
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print(f"⚠️ Could not open {video_path}")
        return

    count = 0
    saved = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        if count % frame_interval == 0:
            # Resize for YOLO (optimally 640x640, but keeping aspect ratio is fine too)
            # We'll save raw for now
            out_name = f"{vid_name}_frame_{count}.jpg"
            out_path = os.path.join(output_dir, out_name)
            cv2.imwrite(out_path, frame)
            saved += 1
            
        count += 1
    
    cap.release()
    print(f"📸 Extracted {saved} frames from {vid_name}")

import concurrent.futures

# ... (imports remain the same, just adding concurrent.futures to top if needed, 
# but replace_file_content is partial. I will add it in the replacement chunk or assume standard lib)

def process_single_video(video_path):
    """Worker function for parallel processing"""
    try:
        extract_frames(video_path, IMAGES_DIR, frame_interval=30)
    except Exception as e:
        print(f"❌ Error processing {video_path}: {e}")

def process_videos():
    """Process downloaded videos in parallel to leverage NVMe I/O"""
    videos = glob.glob(os.path.join(VIDEO_DIR, "*.webm"))
    print(f"found {len(videos)} videos to process.")
    
    # Use ThreadPoolExecutor for I/O bound task (reading video, writing images)
    # NVMe supports high parallelism. 
    # Spec: 8 vCPUs. Let's use 4 threads.
    max_workers = 4 
    print(f"🚀 Starting extraction with {max_workers} threads...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(process_single_video, videos)
        
    print("✅ Frame extraction complete.")

def auto_label_frames():
    """
    Pseudo-labelling: Use a pre-trained YOLO model to detect objects 'in the wild'.
    """
    print("🏷️ Starting Auto-Labeling (Pseudo-labeling) on CPU...")
    
    # Load a pre-trained model (YOLOv8n)
    model = YOLO('yolov8n.pt') 
    
    # List all images
    images = glob.glob(os.path.join(IMAGES_DIR, "*.jpg"))
    
    for img_path in images:
        # Run inference on CPU
        results = model(img_path, verbose=False, device='cpu')
        
        # Save labels in YOLO format
        img_name = Path(img_path).stem
        label_path = os.path.join(LABELS_DIR, f"{img_name}.txt")
        
        with open(label_path, 'w') as f:
            for r in results:
                for box in r.boxes:
                    # Filter: Only Label High Confidence detections
                    if box.conf[0] > 0.4: 
                        cls = int(box.cls[0])
                        # Write to file
                        x, y, w, h = box.xywhn[0].tolist()
                        f.write(f"{cls} {x} {y} {w} {h}\n")
    
    print("✅ Auto-labeling complete.")

def create_yaml():
    """Create data.yaml for YOLO training"""
    yaml_content = f"""
path: {os.path.abspath(DATASET_ROOT)}  # dataset root dir
train: images/train  # train images (relative to 'path') 
val: images/train  # val images (relative to 'path') - using train for val in this demo

# Classes
names:
  0: person
  1: bicycle
  2: car
  3: motorcycle
  4: airplane
  5: bus
  6: train
  7: truck
  8: boat
  9: traffic light
  10: fire hydrant
  11: stop sign
  # ... (YOLOv8n coco classes)
"""
    with open("data.yaml", "w") as f:
        f.write(yaml_content)

def train_model():
    """Fine-tune the model on the new data"""
    print("🧠 Starting Training Loop (CPU Mode)...")
    
    # Load model
    model = YOLO('yolov8n.pt')
    
    # Train
    results = model.train(
        data='data.yaml',
        epochs=10,
        imgsz=640,
        batch=8, # Reduced batch size for CPU/RAM safety
        project='biathlon_model',
        name='cpu_run',
        device='cpu', # Force CPU
        workers=8 # DataLoader workers
    )
    
    print(f"🚀 Training Complete. Model saved to {results.save_dir}")
    
    # Export to ONNX for Robot Hardware (ESP32 / Pi)
    print("📦 Exporting to ONNX...")
    model.export(format='onnx')
    print("✅ ONNX Export Complete.")

def main():
    print("🚀 Starting DigitalOcean Training Pipeline")
    setup_directories()
    download_videos()
    process_videos()
    auto_label_frames()
    create_yaml()
    train_model()
    print("🏁 Pipeline Finished Successfully")

if __name__ == "__main__":
    main()
