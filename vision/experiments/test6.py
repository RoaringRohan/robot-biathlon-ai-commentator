import cv2
import numpy as np
import urllib.request
import pygame

# ================= USER CONFIGURATION =================
URL = 'http://192.168.38.209:81/stream' 

# COLOR RANGE (Currently set for Blue Tape)
LOWER_COLOR = np.array([90, 50, 50])   
UPPER_COLOR = np.array([130, 255, 255])

# WARP GEOMETRY
TOP_WIDTH = 120   
HORIZON = 100     
# ======================================================

pygame.init()
screen = pygame.display.set_mode((400, 600))
pygame.display.set_caption("Lane Detection & Curve Fitting")

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
                    if len(jpg) > 0:
                        frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                        if frame is not None:
                            return cv2.resize(frame, (400, 300))
        except Exception:
            return None

def get_bird_eye_matrix(w, h):
    src = np.float32([[0, h], [w, h], [w//2 + TOP_WIDTH, h//2 + HORIZON], [w//2 - TOP_WIDTH, h//2 + HORIZON]])
    dst = np.float32([[100, h*2], [300, h*2], [300, 0], [100, 0]])
    return cv2.getPerspectiveTransform(src, dst)

def find_lane_curvature(warped_binary):
    """
    detects lane pixels and fits a polynomial curve.
    Returns the polynomial coefficients and visual image.
    """
    # 1. Find the starting point (Histogram)
    histogram = np.sum(warped_binary[warped_binary.shape[0]//2:, :], axis=0)
    start_x = np.argmax(histogram) # Column with most white pixels
    
    # 2. Sliding Windows Config
    nwindows = 9
    window_height = int(warped_binary.shape[0] / nwindows)
    margin = 50 
    minpix = 50 
    
    nonzero = warped_binary.nonzero()
    nonzeroy = np.array(nonzero[0])
    nonzerox = np.array(nonzero[1])
    
    current_x = start_x
    lane_inds = []
    
    # Create an output image to draw on and visualize the result
    out_img = np.dstack((warped_binary, warped_binary, warped_binary)) * 255

    # 3. Step through windows
    for window in range(nwindows):
        win_y_low = warped_binary.shape[0] - (window + 1) * window_height
        win_y_high = warped_binary.shape[0] - window * window_height
        win_x_low = current_x - margin
        win_x_high = current_x + margin
        
        # Draw the windows on the visualization image
        cv2.rectangle(out_img, (win_x_low, win_y_low), (win_x_high, win_y_high), (0, 255, 0), 2) 
        
        good_inds = ((nonzeroy >= win_y_low) & (nonzeroy < win_y_high) & 
                     (nonzerox >= win_x_low) & (nonzerox < win_x_high)).nonzero()[0]
        
        lane_inds.append(good_inds)
        
        if len(good_inds) > minpix:
            current_x = int(np.mean(nonzerox[good_inds]))

    # 4. Fit Polynomial
    lane_inds = np.concatenate(lane_inds)
    if len(lane_inds) > 0:
        x = nonzerox[lane_inds]
        y = nonzeroy[lane_inds]
        
        # Fit a second order polynomial to each
        try:
            poly_fit = np.polyfit(y, x, 2)
            
            # Generate x values for plotting
            ploty = np.linspace(0, warped_binary.shape[0]-1, warped_binary.shape[0])
            fit_x = poly_fit[0]*ploty**2 + poly_fit[1]*ploty + poly_fit[2]
            
            # Draw the smooth line
            pts = np.array([np.transpose(np.vstack([fit_x, ploty]))])
            cv2.polylines(out_img, np.int32([pts]), False, (0, 0, 255), 5)
            
            return out_img, fit_x
        except:
            return out_img, None
            
    return out_img, None

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
    
    # 1. Color Threshold
    blurred = cv2.GaussianBlur(frame, (5, 5), 0)
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, LOWER_COLOR, UPPER_COLOR)
    
    # 2. Warp to Bird's Eye View
    warped = cv2.warpPerspective(mask, M, (400, 600))
    
    # 3. Find Curve
    lane_viz, curve_x = find_lane_curvature(warped)
    
    # 4. Pygame Display
    screen.fill((20, 20, 30))
    
    if curve_x is not None:
        # Draw the lane visualization
        surf = pygame.surfarray.make_surface(np.rot90(lane_viz))
        surf = pygame.transform.scale(surf, (400, 600))
        screen.blit(surf, (0,0))
    
    pygame.display.flip()
    cv2.imshow("Robot Eye", frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cv2.destroyAllWindows()
pygame.quit()