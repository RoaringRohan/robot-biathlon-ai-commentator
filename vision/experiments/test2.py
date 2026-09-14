import cv2
import numpy as np
import urllib.request
import math
import pygame
from ultralytics import YOLO

# ================= CONFIGURATION =================
URL = 'http://192.168.38.209:81/stream' 
# Load a lightweight pre-trained model (nano version is fastest)
model = YOLO("yolov8n.pt") 

# Real-world width of the visible floor at the bottom of the camera frame (in cm)
frame_width_cm = 50 
# Real-world distance from camera to the furthest visible point (in cm)
max_distance_cm = 200 

# ================= PYGAME SETUP (The Dashboard) =================
pygame.init()
screen_width, screen_height = 600, 600
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Tesla-Style Radar Dashboard")
font = pygame.font.SysFont("Arial", 18)
# Robot is always at bottom center
robot_pos = (screen_width // 2, screen_height - 50) 

def get_frame_from_stream(url):
    try:
        stream = urllib.request.urlopen(url)
        bytes_data = b''
        while True:
            bytes_data += stream.read(4096)
            a = bytes_data.find(b'\xff\xd8')
            b = bytes_data.find(b'\xff\xd9')
            if a != -1 and b != -1:
                jpg = bytes_data[a:b+2]
                frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                return frame
    except Exception:
        return None

def estimate_distance(bbox_bottom_y, image_height):
    """
    Simple geometric estimation. 
    The lower the object is in the image (higher Y value), the closer it is.
    """
    # Normalize y to 0.0 (top) to 1.0 (bottom)
    norm_y = bbox_bottom_y / image_height
    
    # Invert so 0.0 is bottom (close) and 1.0 is top (far)
    # This is a linear approximation; real cameras need Homography for perfect accuracy
    # But for a hackathon, this often "looks" good enough.
    distance_factor = (1.0 - norm_y) 
    
    # Map to real world cm
    distance_cm = distance_factor * max_distance_cm
    return distance_cm

def estimate_lateral_pos(bbox_center_x, image_width):
    """
    Estimate if object is left or right of center.
    """
    norm_x = (bbox_center_x - (image_width / 2)) / (image_width / 2)
    # Returns -1.0 (left) to 1.0 (right)
    return norm_x * (frame_width_cm / 2)

# ================= MAIN LOOP =================
running = True
while running:
    # 1. Handle Pygame Events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # 2. Get Frame
    frame = get_frame_from_stream(URL)
    if frame is None:
        continue

    h, w, _ = frame.shape

    # 3. Run YOLO Inference (Obstacle Detection)
    results = model(frame, verbose=False)
    
    # 4. Prepare Dashboard
    screen.fill((20, 20, 30)) # Dark Tesla-like background
    
    # Draw Robot (Ego vehicle)
    pygame.draw.circle(screen, (0, 255, 255), robot_pos, 15) # Cyan dot
    pygame.draw.line(screen, (50, 50, 50), (robot_pos[0], 0), robot_pos, 2) # Center line

    # 5. Process Detections
    for result in results:
        boxes = result.boxes
        for box in boxes:
            # Get box coordinates
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            cls = int(box.cls[0])
            label = model.names[cls]
            
            # Filter: Only care about "standard" obstacles 
            # (In hackathon, you might care about 'bottle', 'cup', 'person', etc)
            # YOLO classes: 0=person, 39=bottle, 41=cup, etc.
            
            # --- VISION CALCULATION ---
            # We use the BOTTOM center of the box for distance (where object hits floor)
            center_x = int((x1 + x2) / 2)
            bottom_y = int(y2)
            
            dist_cm = estimate_distance(bottom_y, h)
            lat_cm = estimate_lateral_pos(center_x, w)

            # --- DRAW ON VIDEO FRAME ---
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
            cv2.putText(frame, f"{dist_cm:.0f}cm", (int(x1), int(y1)-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # --- MAP TO DASHBOARD ---
            # Scale dist_cm to screen pixels
            # 200cm real world = 500 pixels on screen
            map_y = robot_pos[1] - (dist_cm * (500 / max_distance_cm))
            map_x = robot_pos[0] + (lat_cm * (500 / frame_width_cm))
            
            # Draw Obstacle on Dashboard
            pygame.draw.rect(screen, (255, 50, 50), (map_x-10, map_y-10, 20, 20))
            text_surf = font.render(f"{dist_cm:.0f}cm", True, (200, 200, 200))
            screen.blit(text_surf, (map_x+15, map_y))

    # 6. Update Displays
    cv2.imshow("Robot Camera View", frame) # The "Eye"
    pygame.display.flip()                  # The "Brain/Dashboard"

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()
pygame.quit()