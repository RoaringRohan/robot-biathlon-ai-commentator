import cv2
import numpy as np
import urllib.request
import pygame

# ================= CONFIGURATION =================
URL = 'http://192.168.38.209:81/stream' 

# COLOR RANGES (HSV) - YOU MUST TUNE THESE!
# Open a color picker to find the HSV range for your Yellow Cube
lower_yellow = np.array([20, 100, 100]) # Hue ~30 is yellow
upper_yellow = np.array([40, 255, 255])

# Assuming the floor line is RED based on your diagram (Change to black if needed)
lower_line = np.array([0, 100, 100]) 
upper_line = np.array([10, 255, 255]) # Red wraps around 0-180 in OpenCV

# DASHBOARD CONFIG
pygame.init()
screen = pygame.display.set_mode((600, 800))
pygame.display.set_caption("Bot Telemetry")

def get_frame():
    try:
        stream = urllib.request.urlopen(URL)
        bytes_data = b''
        while True:
            bytes_data += stream.read(4096)
            a = bytes_data.find(b'\xff\xd8')
            b = bytes_data.find(b'\xff\xd9')
            if a != -1 and b != -1:
                jpg = bytes_data[a:b+2]
                return cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
    except:
        return None

def bird_eye_view(frame):
    """
    Warps the perspective to look like a top-down map.
    You need to tweak src_points to match your camera angle!
    """
    h, w = frame.shape[:2]
    
    # Area of the image we want to "flatten" (The floor in front of bot)
    # Shape: Trapezoid
    src_points = np.float32([
        [0, h],           # Bottom Left
        [w, h],           # Bottom Right
        [w//2 + 100, h//2], # Top Right (Horizon)
        [w//2 - 100, h//2]  # Top Left (Horizon)
    ])
    
    # Where we want it to go on the "Map" (Rectangle)
    dst_points = np.float32([
        [100, h],       
        [w-100, h],     
        [w-100, 0],     
        [100, 0]        
    ])
    
    M = cv2.getPerspectiveTransform(src_points, dst_points)
    warped = cv2.warpPerspective(frame, M, (w, h))
    return warped, M

# ================= MAIN LOOP =================
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False

    frame = get_frame()
    if frame is None: continue
    
    # 1. Convert to HSV for robust color detection
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    # 2. DETECT THE YELLOW CUBE
    mask_cube = cv2.inRange(hsv, lower_yellow, upper_yellow)
    contours_cube, _ = cv2.findContours(mask_cube, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    cube_positions = []
    for cnt in contours_cube:
        area = cv2.contourArea(cnt)
        if area > 500: # Filter small noise
            x, y, w, h = cv2.boundingRect(cnt)
            # Draw on camera feed
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 255), 2)
            cv2.putText(frame, "TARGET", (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
            
            # Save center point for dashboard
            cube_positions.append((x + w//2, y + h)) # Bottom center is best for distance

    # 3. DETECT THE LINE (THE "GPS PATH")
    mask_line = cv2.inRange(hsv, lower_line, upper_line)
    # Optional: Erode/Dilate to remove noise
    kernel = np.ones((5,5), np.uint8)
    mask_line = cv2.morphologyEx(mask_line, cv2.MORPH_OPEN, kernel)
    
    # 4. CREATE DASHBOARD
    screen.fill((30, 30, 30)) # Dark Tarmac Color
    
    # A. Draw the "GPS Path"
    # We cheat here: We take the actual camera threshold and just project it!
    # This looks EXACTLY like a GPS highlight.
    warped_line, _ = bird_eye_view(mask_line)
    
    # Convert opencv image to pygame surface
    warped_rgb = cv2.cvtColor(warped_line, cv2.COLOR_GRAY2RGB)
    warped_rgb = np.rot90(warped_rgb) # Pygame rotation fix
    surf = pygame.surfarray.make_surface(warped_rgb)
    surf.set_colorkey((0,0,0)) # Make black transparent
    surf.set_alpha(150) # Make it ghostly/holographic
    
    # Scale to fit dashboard
    surf = pygame.transform.scale(surf, (600, 800))
    screen.blit(surf, (0,0))
    
    # B. Draw the Cubes on the Map
    # (Simple linear projection for hackathon speed)
    for cx, cy in cube_positions:
        # Map Y (Distance): Higher in image (low Y) = Further away
        # Map X (Lateral): Center is center
        
        # Simple math to move it to dashboard coords
        # You would use the Perspective Matrix 'M' here for perfect accuracy
        # but this is usually "good enough" for visual flair
        dash_y = 800 - (cy / frame.shape[0]) * 800
        dash_x = (cx / frame.shape[1]) * 600
        
        # Draw Yellow Cube representation
        pygame.draw.rect(screen, (255, 255, 0), (dash_x-20, dash_y-20, 40, 40), 2)
        pygame.draw.circle(screen, (255, 255, 0), (int(dash_x), int(dash_y)), 5)

    # C. Draw "Ego" Robot
    pygame.draw.polygon(screen, (0, 255, 0), [(300, 750), (280, 780), (320, 780)])

    pygame.display.flip()
    cv2.imshow("Cam Debug", frame)
    
    if cv2.waitKey(1) == ord('q'): break

cv2.destroyAllWindows()
pygame.quit()