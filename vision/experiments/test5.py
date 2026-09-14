import cv2
import numpy as np
import urllib.request
import pygame

# ================= USER CONFIGURATION =================
URL = 'http://192.168.38.209:81/stream' 

# --- STANDARD HSV COLOR RANGES ---
# These are "Safe Defaults" for bright colors.
# Note: Red wraps around in HSV (0-10 AND 170-180)

# 1. RED (Danger/Obstacles)
LOWER_RED1 = np.array([0, 120, 70])
UPPER_RED1 = np.array([10, 255, 255])
LOWER_RED2 = np.array([170, 120, 70])
UPPER_RED2 = np.array([180, 255, 255])

# 2. GREEN (The Track/Safe Zone)
LOWER_GREEN = np.array([40, 70, 70]) 
UPPER_GREEN = np.array([80, 255, 255])

# 3. BLUE (Objectives/Boxes)
LOWER_BLUE = np.array([90, 70, 70])
UPPER_BLUE = np.array([130, 255, 255])

# 4. WHITE (If you still need the road lines)
# White is unique: Low Saturation (0-50), High Value (200-255)
LOWER_WHITE = np.array([0, 0, 200])
UPPER_WHITE = np.array([180, 50, 255])

# --- DASHBOARD GEOMETRY ---
# Tweak these to make the red box in "Camera Tuning" match the floor
TOP_WIDTH = 100   
HORIZON = 120     

# ======================================================

pygame.init()
screen = pygame.display.set_mode((400, 600))
pygame.display.set_caption("RGB Tesla Dashboard")
font = pygame.font.SysFont("Arial", 16)

def get_frame(stream):
    bytes_data = b''
    while True:
        try:
            bytes_data += stream.read(4096)
            a = bytes_data.find(b'\xff\xd8')
            if a != -1:
                b = bytes_data.find(b'\xff\xd9', a)
                if b != -1:
                    jpg = bytes_data[a:b+2]
                    frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                    return cv2.resize(frame, (400, 300))
        except Exception:
            return None

def get_bird_eye_matrix(w, h):
    src = np.float32([
        [0, h], [w, h], 
        [w//2 + TOP_WIDTH, h//2 + HORIZON], 
        [w//2 - TOP_WIDTH, h//2 + HORIZON]
    ])
    dst = np.float32([[100, h*2], [300, h*2], [300, 0], [100, 0]])
    return cv2.getPerspectiveTransform(src, dst)

def process_color(frame, lower, upper, M, color_name, draw_color, surface):
    """
    Finds a specific color, maps it to 3D, and draws it on the dashboard.
    """
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lower, upper)
    
    # Clean up noise
    kernel = np.ones((5,5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    
    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    for cnt in contours:
        if cv2.contourArea(cnt) > 300: # Filter small specks
            x, y, w, h = cv2.boundingRect(cnt)
            
            # 1. Draw Bounding Box on Camera Feed (for debug)
            cv2.rectangle(frame, (x, y), (x+w, y+h), draw_color, 2)
            cv2.putText(frame, color_name, (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, draw_color, 1)

            # 2. Map to Dashboard
            # We map the "footprint" of the object (bottom center)
            center_x = x + w/2
            bottom_y = y + h
            
            pt = np.array([[[center_x, bottom_y]]], dtype='float32')
            warped_pt = cv2.perspectiveTransform(pt, M)
            
            map_x = int(warped_pt[0][0][0])
            map_y = int(warped_pt[0][0][1])
            
            # Draw on Pygame Surface
            # Flip Y coordinate because Pygame 0,0 is top-left
            # We want the robot at the bottom.
            # (In this setup, map_y comes out large for close objects, small for far objects)
            
            # Draw Circle
            pygame.draw.circle(surface, draw_color, (map_x, map_y), 10)
            
            # Draw Text Label
            dist_text = font.render(f"{color_name}", True, (200, 200, 200))
            surface.blit(dist_text, (map_x + 12, map_y - 5))

# Initialize
print(f"Connecting to {URL}...")
stream = urllib.request.urlopen(URL)

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False

    frame = get_frame(stream)
    if frame is None: continue
    
    h, w = frame.shape[:2]
    M = get_bird_eye_matrix(w, h)

    # Refresh Dashboard Background
    screen.fill((20, 20, 30)) 

    # --- PROCESS COLORS ---
    
    # 1. PROCESS RED (Combine two ranges for better Red detection)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask1 = cv2.inRange(hsv, LOWER_RED1, UPPER_RED1)
    mask2 = cv2.inRange(hsv, LOWER_RED2, UPPER_RED2)
    full_red_mask = mask1 + mask2
    
    # We manually handle Red here because of the combined mask
    contours, _ = cv2.findContours(full_red_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        if cv2.contourArea(cnt) > 300:
            x, y, bw, bh = cv2.boundingRect(cnt)
            cv2.rectangle(frame, (x, y), (x+bw, y+bh), (0, 0, 255), 2)
            
            pt = np.array([[[x + bw/2, y + bh]]], dtype='float32')
            warped_pt = cv2.perspectiveTransform(pt, M)
            pygame.draw.rect(screen, (255, 50, 50), (warped_pt[0][0][0]-10, warped_pt[0][0][1]-10, 20, 20))

    # 2. PROCESS GREEN
    process_color(frame, LOWER_GREEN, UPPER_GREEN, M, "SAFE", (0, 255, 0), screen)

    # 3. PROCESS BLUE
    process_color(frame, LOWER_BLUE, UPPER_BLUE, M, "BOX", (255, 200, 0), screen) 
    # Note: I used Yellow color for drawing Blue objects just so it pops on dark background, 
    # change (255, 200, 0) to (0, 0, 255) for blue.

    # 4. PROCESS WHITE (Road Lines)
    # We treat White differently: We draw the whole warped shape as the "Lane"
    mask_white = cv2.inRange(hsv, LOWER_WHITE, UPPER_WHITE)
    warped_white = cv2.warpPerspective(mask_white, M, (400, 600))
    white_surf = pygame.surfarray.make_surface(np.rot90(warped_white))
    white_surf.set_colorkey((0,0,0))
    white_surf.set_alpha(80) # Very faint
    white_surf = pygame.transform.scale(white_surf, (400, 600))
    screen.blit(white_surf, (0,0))

    # Draw Robot
    pygame.draw.polygon(screen, (0, 255, 255), [(200, 550), (180, 590), (220, 590)])

    # Update Displays
    pygame.display.flip()
    
    # Draw Calibration Box on Camera Feed
    pts = np.array([[0, h], [w, h], [w//2 + TOP_WIDTH, h//2 + HORIZON], [w//2 - TOP_WIDTH, h//2 + HORIZON]], np.int32)
    cv2.polylines(frame, [pts], True, (0,0,255), 2)
    cv2.imshow("Camera Feed", frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cv2.destroyAllWindows()
pygame.quit()