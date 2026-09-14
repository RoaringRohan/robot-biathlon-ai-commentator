import cv2
import numpy as np
import urllib.request

# ================= USER CONFIGURATION =================
URL = 'http://192.168.38.209:81/stream'
# ======================================================

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
                        # Resize to reduce lag (320x240 is standard QVGA, good balance of speed/quality)
                        if frame is not None:
                            frame = cv2.resize(frame, (320, 240))
                        return frame
        except Exception:
            return None

def detect_rectangle_strip(frame):
    # 1. Pre-processing
    # Blur to reduce high-frequency noise
    blurred = cv2.GaussianBlur(frame, (5, 5), 0)
    # Convert to HSV
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

    # 2. Define a "Colorful" range (Detects any color that isn't white/gray/black)
    # Hue: 0-180 (All colors)
    # Saturation: 60-255 (Must have some color magnitude)
    # Value: 50-255 (Must be somewhat bright, ignores dark shadows)
    lower_color = np.array([0, 60, 50])
    upper_color = np.array([180, 255, 255])

    mask = cv2.inRange(hsv, lower_color, upper_color)
    
    # Morphological Operations to clean up the mask
    # Open: Removes small noise (erosion followed by dilation)
    # Close: Closes small holes inside the object (dilation followed by erosion)
    kernel = np.ones((5,5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    # Show the mask for debugging (Values usually show up as white)
    cv2.imshow("Color Mask", mask)

    # 3. Find Contours
    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    for cnt in contours:
        area = cv2.contourArea(cnt)
        
        # Filter out small noise (Adjusted for smaller resolution)
        if area > 300: 
            
            # Robust Rectangle Detection using MinAreaRect (handles rotation)
            rect = cv2.minAreaRect(cnt)
            (center, (w, h), angle) = rect
            
            # Organize w and h so aspect ratio is consistent
            # Longest side / Shortest side
            if w < h:
                w, h = h, w
                
            aspect_ratio = float(w) / h if h > 0 else 0
            
            # Calculate Solidity to ensure it's rectangular-ish (not a C shape or blob)
            box = cv2.boxPoints(rect)
            box = np.int32(box)
            box_area = cv2.contourArea(box)
            solidity = area / box_area if box_area > 0 else 0
            
            # Criteria for a "Strip":
            # 1. High Aspect Ratio (e.g., > 2.0) OR just "not square" (> 1.5)
            # 2. High Solidity (> 0.7) means it fills its bounding box well
            
            if aspect_ratio > 1.5 and solidity > 0.7:
                # Draw the rotated rectangle
                cv2.drawContours(frame, [box], 0, (0, 255, 0), 2)
                
                label = f"Strip | AR:{aspect_ratio:.1f}"
                cv2.putText(frame, label, (int(center[0]), int(center[1])), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    return frame

# To test with ESP32 Camera:
print(f"Connecting to {URL}...")
try:
    stream = urllib.request.urlopen(URL)
except Exception as e:
    print(f"Failed to connect to stream: {e}")
    exit()

while True:
    img = get_frame(stream)
    if img is None:
        continue
    
    result = detect_rectangle_strip(img)
    cv2.imshow("Detection", result)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()