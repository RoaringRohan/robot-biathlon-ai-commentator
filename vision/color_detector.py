import cv2
import numpy as np
import urllib.request
import time
import pygame

# ==========================================
# CONFIGURATION
# ==========================================
STREAM_URL = 'http://192.168.38.209:81/stream'
MIN_AREA = 1000 

# Dashboard Geometry (Tweak these to calibrate the "Floor" view)
TOP_WIDTH = 100   
HORIZON = 120     

COLORS = {
    "Red": [
        (np.array([0, 100, 100]), np.array([10, 255, 255])),
        (np.array([160, 100, 100]), np.array([180, 255, 255]))
    ],
    "Blue": [
        (np.array([90, 100, 100]), np.array([130, 255, 255]))
    ],
    "Green": [
        (np.array([40, 50, 50]), np.array([90, 255, 255]))
    ],
    "Yellow": [
        (np.array([20, 100, 100]), np.array([30, 255, 255]))
    ]
}

# 4. LANE LINES (White/Bright floor markings)
# Low saturation, high brightness
LOWER_WHITE = np.array([0, 0, 200])
UPPER_WHITE = np.array([180, 50, 255])

# Drawing Colors for Dashboard (RGB)
DASH_COLORS = {
    "Red": (255, 50, 50),
    "Blue": (50, 100, 255),
    "Green": (50, 255, 50),
    "Yellow": (255, 255, 0)
}

def get_bird_eye_matrix(w, h):
    # Mapping a Trapezoid (Camera View) to a Rectangle (Top-Down View)
    src = np.float32([
        [0, h],                           # Bottom-Left
        [w, h],                           # Bottom-Right
        [w//2 + TOP_WIDTH, h//2 + HORIZON], # Top-Right (Horizon)
        [w//2 - TOP_WIDTH, h//2 + HORIZON]  # Top-Left (Horizon)
    ])
    # Destination is a flat rectangle matching the screen size (roughly)
    dst = np.float32([[100, h*2], [300, h*2], [300, 0], [100, 0]])
    return cv2.getPerspectiveTransform(src, dst)

# ==========================================
# STREAM PARSING
# ==========================================
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

# ... (Previous imports and config)

def draw_car(screen, center_x, center_y):
    """
    Draws a minimalist 'Tesla-style' car avatar.
    """
    # Car Body (Silver/White)
    car_w, car_h = 40, 70
    x = center_x - car_w // 2
    y = center_y - car_h // 2
    
    # Shadow
    pygame.draw.rect(screen, (10, 10, 10), (x+5, y+5, car_w, car_h), border_radius=10)
    
    # Chassis
    pygame.draw.rect(screen, (200, 200, 220), (x, y, car_w, car_h), border_radius=10)
    
    # Windshield / Roof (Darker)
    roof_w, roof_h = 34, 40
    rx = center_x - roof_w // 2
    ry = center_y - 10
    pygame.draw.rect(screen, (40, 40, 50), (rx, ry, roof_w, roof_h), border_radius=5)
    
    # Headlights
    pygame.draw.rect(screen, (255, 255, 200), (x+2, y+2, 8, 10), border_radius=3)
    pygame.draw.rect(screen, (255, 255, 200), (x+car_w-10, y+2, 8, 10), border_radius=3)
    
    # Tail lights
    pygame.draw.rect(screen, (200, 50, 50), (x+2, y+car_h-6, 8, 6), border_radius=2)
    pygame.draw.rect(screen, (200, 50, 50), (x+car_w-10, y+car_h-6, 8, 6), border_radius=2)

def draw_navigation_path(screen, color, angle, center_x):
    """
    Draws a smooth curved path based on angle deviation from vertical (90 deg).
    """
    # Vertical is roughly 90 degrees in our normalized logic.
    # Deviation < 0 = Left Turn
    # Deviation > 0 = Right Turn
    # Angle is typically 0-180.
    
    deviation = angle - 90
    turn_intensity = deviation * 6.0 # Sensitivity multiplier
    
    start_y = 500
    end_y = 100
    steps = 15
    
    points_l = []
    points_r = []
    
    for i in range(steps + 1):
        t = i / float(steps) # 0.0 to 1.0
        
        # Perspective Z (Depth)
        # Non-linear Y mapping to simulate depth
        current_y = start_y - (start_y - end_y) * (t ** 0.8)
        
        # Curve X offset
        # Quadratic curve: x_offset = turn_intensity * t^2
        x_offset = turn_intensity * (t * t)
        
        # Perspective Width
        road_width = 120 * (1.0 - (0.6 * t)) # Narrows at distance
        
        center_road = center_x + x_offset
        
        points_l.append((center_road - road_width/2, current_y))
        points_r.append((center_road + road_width/2, current_y))
        
    # Draw Road Body (Polygon)
    road_poly = points_l + points_r[::-1]
    
    # Ghost effect for the road
    surf = pygame.Surface((400, 600), pygame.SRCALPHA)
    pygame.draw.polygon(surf, (*color, 100), road_poly) # 100 alpha
    screen.blit(surf, (0,0))
    
    # Draw Lane Edges
    pygame.draw.lines(screen, color, False, points_l, 3)
    pygame.draw.lines(screen, color, False, points_r, 3)

def detect_objects_with_angle(frame):
    output_frame = frame.copy()
    detections = []
    
    blur = cv2.GaussianBlur(frame, (5, 5), 0)
    hsv = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)
    
    for color_name, ranges in COLORS.items():
        mask = np.zeros(hsv.shape[:2], dtype="uint8")
        for (lower, upper) in ranges:
            mask = cv2.bitwise_or(mask, cv2.inRange(hsv, lower, upper))
            
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for cnt in contours:
            if cv2.contourArea(cnt) < MIN_AREA: continue
            
            # Use MinAreaRect to get Angle
            rect = cv2.minAreaRect(cnt)
            (center, (w, h), angle) = rect
            box = cv2.boxPoints(rect)
            box = np.int0(box)
            
            # Draw Rotated Rect
            cv2.drawContours(output_frame, [box], 0, (0, 255, 0), 2)
            cv2.putText(output_frame, f"{color_name} {int(angle)}deg", (box[0][0], box[0][1]), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # Normalize Angle logic (OpenCV returns -90 to 0 usually)
            # Make sure W > H to define "Orientation"
            if w < h:
                angle = angle + 90
                
            detections.append({'color': color_name, 'angle': angle, 'center': center})
                
    return output_frame, detections

def main():
    pygame.init()
    screen = pygame.display.set_mode((400, 600))
    pygame.display.set_caption("WinterOps Navigation HUD")
    font = pygame.font.SysFont("Arial", 20)
    
    print(f"Connecting to ESP32 Camera at: {STREAM_URL}")
    try:
        stream = urllib.request.urlopen(STREAM_URL)
    except Exception as e:
        print(f"Error connecting to stream: {e}")
        return

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            
        frame = get_frame(stream)
        if frame is None: continue
        
        # Vision
        vis_frame, objects = detect_objects_with_angle(frame)
        
        # Dashboard
        screen.fill((10, 10, 20)) # Deep Space Grey
        
        # Default Road (Grey)
        nav_color = (60, 60, 60)
        nav_text = "SEARCHING..."
        nav_angle = 0
        
        # Logic: Find the LARGEST object to follow
        if objects:
            # Pick first object for now (you can add logic to pick largest)
            target = objects[0]
            nav_angle = target['angle']
            
            col_name = target['color']
            if col_name in DASH_COLORS:
                nav_color = DASH_COLORS[col_name] # Glow Road with that color
                
            nav_text = f"TRACKING: {col_name.upper()} ({int(nav_angle)} deg)"
            
        # Draw Dynamic Road
        draw_navigation_path(screen, nav_color, nav_angle, 200)
        
        # Draw Robot overlay
        draw_car(screen, 200, 550)
        
        # HUD Text
        text_surf = font.render(nav_text, True, (255, 255, 255))
        screen.blit(text_surf, (20, 20))

        # Show feeds
        cv2.imshow("Camera Feed", vis_frame)
        pygame.display.flip()
        
        if cv2.waitKey(1) & 0xFF == ord('q'): break
            
    cv2.destroyAllWindows()
    pygame.quit()

if __name__ == "__main__":
    main()
