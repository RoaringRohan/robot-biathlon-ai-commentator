import cv2
import numpy as np

# Load your image
image_path = 'test_image.jpg'
frame = cv2.imread(image_path)

if frame is None:
    print(f"Error: Could not find {image_path}. Make sure the file name matches!")
    exit()

# Resize for easier viewing on screen
frame = cv2.resize(frame, (800, 600))

# Pre-processing: Blur slightly to blend the table speckles
blurred = cv2.GaussianBlur(frame, (5, 5), 0)
hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

# ========================================================
# ESTIMATED COLORS BASED ON YOUR PHOTO
# ========================================================

# 1. BLUE PAINTER'S TAPE
# Standard Blue is Hue 100-130. 
# We set Saturation/Value min to 80 to avoid the grey table.
lower_blue = np.array([90, 80, 50])
upper_blue = np.array([130, 255, 255])

# 2. RED STRIP
# Red is tricky because it's at the start (0) AND end (180) of the color wheel.
# We combine two ranges to catch "Dark Red" and "Bright Red".
lower_red1 = np.array([0, 100, 100])
upper_red1 = np.array([10, 255, 255])
lower_red2 = np.array([160, 100, 100])
upper_red2 = np.array([180, 255, 255])

# 3. GREEN SQUARE
# Bright "Kelly Green" usually sits around Hue 40-80.
lower_green = np.array([40, 50, 50])
upper_green = np.array([90, 255, 255])

# ========================================================
# CREATE MASKS
# ========================================================

# Create Blue Mask
mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)

# Create Red Mask (Combine the two red ranges)
mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)
mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
mask_red = mask_red1 + mask_red2

# Create Green Mask
mask_green = cv2.inRange(hsv, lower_green, upper_green)

# ========================================================
# THE "SPECKLE ERASER" (Morphology)
# ========================================================
# This step removes the grey noise from your table texture.
kernel = np.ones((5,5), np.uint8)

mask_blue = cv2.morphologyEx(mask_blue, cv2.MORPH_OPEN, kernel)
mask_red = cv2.morphologyEx(mask_red, cv2.MORPH_OPEN, kernel)
mask_green = cv2.morphologyEx(mask_green, cv2.MORPH_OPEN, kernel)

# ========================================================
# VISUALIZATION
# ========================================================

# Draw outlines on the original image to show what we found
contours_blue, _ = cv2.findContours(mask_blue, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
cv2.drawContours(frame, contours_blue, -1, (255, 0, 0), 3) # Blue Outline

contours_red, _ = cv2.findContours(mask_red, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
cv2.drawContours(frame, contours_red, -1, (0, 0, 255), 3) # Red Outline

contours_green, _ = cv2.findContours(mask_green, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
cv2.drawContours(frame, contours_green, -1, (0, 255, 0), 3) # Green Outline

# Show results
cv2.imshow("Detected Colors (Press 'q' to quit)", frame)

# Optional: Show the Black & White masks to see how clean they are
combined_masks = cv2.resize(np.hstack([mask_blue, mask_red, mask_green]), (1200, 400))
cv2.imshow("Debug Masks (Blue | Red | Green)", combined_masks)

cv2.waitKey(0)
cv2.destroyAllWindows()