import cv2
import numpy as np
import urllib.request

url = 'http://192.168.38.209:81/stream' 

def nothing(x): pass

# Create a window with sliders
cv2.namedWindow('Calibration')
cv2.createTrackbar('Low H', 'Calibration', 0, 179, nothing)
cv2.createTrackbar('Low S', 'Calibration', 50, 255, nothing)
cv2.createTrackbar('Low V', 'Calibration', 50, 255, nothing)
cv2.createTrackbar('High H', 'Calibration', 179, 179, nothing)
cv2.createTrackbar('High S', 'Calibration', 255, 255, nothing)
cv2.createTrackbar('High V', 'Calibration', 255, 255, nothing)

print("Connecting to camera...")
stream = urllib.request.urlopen(url)
bytes_data = b''

while True:
    # 1. Read the stream manually 
    bytes_data += stream.read(4096)
    
    # 2. Find the START of the JPEG
    a = bytes_data.find(b'\xff\xd8')
    
    if a != -1:
        # 3. Find the END of the JPEG *after* the start index 'a'
        b = bytes_data.find(b'\xff\xd9', a)
        
        if b != -1:
            # We have a complete frame from a to b
            jpg = bytes_data[a:b+2]
            
            # Reset buffer to start AFTER this frame
            bytes_data = bytes_data[b+2:]
            
            # Decode
            if len(jpg) > 0:
                frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                
                if frame is not None:
                    # Resize for speed and to fit screen
                    frame = cv2.resize(frame, (400, 300))
                    
                    # Convert to HSV
                    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                    
                    # Get slider values
                    l_h = cv2.getTrackbarPos('Low H', 'Calibration')
                    l_s = cv2.getTrackbarPos('Low S', 'Calibration')
                    l_v = cv2.getTrackbarPos('Low V', 'Calibration')
                    h_h = cv2.getTrackbarPos('High H', 'Calibration')
                    h_s = cv2.getTrackbarPos('High S', 'Calibration')
                    h_v = cv2.getTrackbarPos('High V', 'Calibration')
                    
                    lower_bound = np.array([l_h, l_s, l_v])
                    upper_bound = np.array([h_h, h_s, h_v])
                    
                    # Create Mask
                    mask = cv2.inRange(hsv, lower_bound, upper_bound)
                    
                    # Show both
                    cv2.imshow('Original', frame)
                    cv2.imshow('Mask', mask)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print(f"Your Values:\nLower: {lower_bound}\nUpper: {upper_bound}")
                break
    else:
        # If we have a lot of data but no start marker, clear it to prevent memory overflow
        if len(bytes_data) > 100000:
            bytes_data = b''
            
cv2.destroyAllWindows()