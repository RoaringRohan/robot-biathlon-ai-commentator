import cv2
import numpy as np
import urllib.request

# REPLACE with the IP address printed in your Arduino Serial Monitor
# Note the ":81/stream" endpoint. This is standard for the ESP32-CAM example.
url = 'http://192.168.38.209:81/stream' 

# Create a VideoCapture object
# OpenCV can often read directly from the URL if the stream is MJPEG
cap = cv2.VideoCapture(url)

if not cap.isOpened():
    print("Cannot open stream. Trying alternative method...")

while True:
    # Method 1: Try reading directly (Most efficient if supported)
    ret, frame = cap.read()
    
    # Method 2: Fallback manual stream parsing (If Method 1 fails)
    # Sometimes OpenCV struggles with network streams directly. 
    # If cap.read() returns False, we can use urllib to fetch bytes manually.
    if not ret:
        try:
            stream = urllib.request.urlopen(url)
            bytes_data = b''
            while True:
                bytes_data += stream.read(1024)
                a = bytes_data.find(b'\xff\xd8') # JPEG Start
                b = bytes_data.find(b'\xff\xd9') # JPEG End
                if a != -1 and b != -1:
                    jpg = bytes_data[a:b+2]
                    bytes_data = bytes_data[b+2:]
                    frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                    break
        except Exception as e:
            print(f"Error reading stream: {e}")
            break

    # =================================================
    # VISION MODELLING & ANALYTICS GO HERE
    # =================================================
    
    # Example: Simple converting to Grayscale (Pre-processing)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Example: Access pixel data for analytics
    avg_brightness = np.mean(gray)
    
    # Display the resulting frame
    cv2.putText(frame, f"Brightness: {avg_brightness:.2f}", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    
    cv2.imshow('ESP32-CAM Live Feed', frame)

    # Press 'q' to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()