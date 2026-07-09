import cv2
import numpy as np
from PIL import Image
import io

def enhance_image_contrast(raw_bytes):
    # Load image from bytes
    image = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
    img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    # Denoise the image to remove unnecessary noise
    img_cv = cv2.fastNlMeansDenoisingColored(img_cv, None, 10, 10, 7, 21)

    # Convert to LAB color space and apply CLAHE to enhance contrast
    lab = cv2.cvtColor(img_cv, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    enhanced_lab = cv2.merge((cl, a, b))
    contrast_enhanced = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

    # Convert to grayscale for thresholding
    gray = cv2.cvtColor(contrast_enhanced, cv2.COLOR_BGR2GRAY)

    # Sharpening filter (helps OCR)
    kernel = np.array([[0, -1, 0],
                       [-1, 5, -1], 
                       [0, -1, 0]])
    sharpened = cv2.filter2D(gray, -1, kernel)

    # Adaptive thresholding for binarization
    final = cv2.adaptiveThreshold(
        sharpened, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11, 2
    )

    return final
