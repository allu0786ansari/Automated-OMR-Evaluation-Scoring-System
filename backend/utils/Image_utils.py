# backend/utils/image_utils.py
import cv2
import numpy as np
from typing import Tuple, Optional
from pathlib import Path
import pytesseract

# If tesseract binary is not in PATH, set pytesseract.pytesseract.tesseract_cmd to the full path:
# pytesseract.pytesseract.tesseract_cmd = r"/usr/bin/tesseract"  # adjust for your system

def load_image(path: str):
    img = cv2.imread(str(path))
    if img is None:
        raise FileNotFoundError(f"Image not found or not readable: {path}")
    return img


def find_largest_quad_contour(gray):
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, th = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4 and cv2.contourArea(approx) > 10000:
            return approx.reshape(4, 2)
    return None


def order_points_clockwise(pts):
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def rectify_perspective(img, out_size: Tuple[int, int] = (1240, 1754)):
    """
    Warp the sheet to canonical size. If no sheet boundary found, resize to out_size.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    quad = find_largest_quad_contour(gray)
    if quad is None:
        h, w = out_size[1], out_size[0]
        return cv2.resize(img, (w, h))
    rect = order_points_clockwise(quad)
    dst = np.array([[0, 0], [out_size[0] - 1, 0], [out_size[0] - 1, out_size[1] - 1], [0, out_size[1] - 1]], dtype="float32")
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(img, M, out_size)
    return warped


def compute_fill_ratio(warped_bgr, x: int, y: int, w: int, h: int) -> float:
    """
    Returns ratio of dark pixels inside the bbox after adaptive thresholding.
    """
    h_img, w_img = warped_bgr.shape[:2]
    x0 = max(0, int(x))
    y0 = max(0, int(y))
    x1 = min(w_img, int(x + w))
    y1 = min(h_img, int(y + h))
    roi = warped_bgr[y0:y1, x0:x1]
    if roi.size == 0:
        return 0.0
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    # adaptive threshold
    th = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY_INV, 11, 2)
    kernel = np.ones((3, 3), np.uint8)
    th = cv2.morphologyEx(th, cv2.MORPH_OPEN, kernel)
    filled = cv2.countNonZero(th)
    total = th.size
    ratio = filled / float(total) if total > 0 else 0.0
    return float(ratio)


def draw_overlay(warped_bgr, template: dict, answers: dict):
    overlay = warped_bgr.copy()
    for qmeta in template["questions"]:
        qid = str(qmeta["q"])
        for opt in qmeta["options"]:
            x, y, w, h = opt["bbox"]
            x1, y1, x2, y2 = int(x), int(y), int(x + w), int(y + h)
            cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 255, 0), 1)
            selected = answers.get(qid)
            if selected == opt["id"]:
                cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 0, 255), 2)
                cv2.putText(overlay, "X", (x1 + 3, y1 + h - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    return overlay


def save_overlay_image(warped_bgr, template, answers, out_path: str):
    overlay = draw_overlay(warped_bgr, template, answers)
    outp = Path(out_path)
    outp.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(outp), overlay)


# ------------------------
# Header detection helpers
# ------------------------
def crop_header_region(img_bgr, header_height_ratio: float = 0.20):
    """
    Crop top portion of the warped image where 'Set A' / 'Set B' is printed.
    header_height_ratio: fraction of image height to consider as header (0.10-0.25 typical)
    """
    h = img_bgr.shape[0]
    crop_h = int(h * header_height_ratio)
    return img_bgr[0:crop_h, :]


def detect_version_from_header_image(img_bgr) -> Optional[str]:
    """
    Try to detect the sheet version text from header using OCR.
    Returns 'A' or 'B' (or other detected token), or None if not found.
    """
    header = crop_header_region(img_bgr, header_height_ratio=0.18)  # tuned
    gray = cv2.cvtColor(header, cv2.COLOR_BGR2GRAY)
    # simple preprocessing to boost OCR
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # OCR: allow uppercase letters and -_, A B characters
    config = r'--psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789- '
    try:
        text = pytesseract.image_to_string(th, config=config)
    except Exception:
        text = ""
    if not text:
        return None
    text = text.upper().replace(" ", "").replace("SET", "SET").replace(":", "").replace(".", "")
    # common patterns: "SET-A", "SET A", "A", "SET-A.", "SET NO: A"
    # Search for 'SET' then look for following letter
    import re
    m = re.search(r"SET[-:]?([A-Z0-9])", text)
    if m:
        return m.group(1)
    # fallback: find single A/B token
    if "A" in text and "B" not in text:
        return "A"
    if "B" in text and "A" not in text:
        return "B"
    # last fallback: look for 'SETA' or 'SETB' substring
    if "SETA" in text:
        return "A"
    if "SETB" in text:
        return "B"
    return None
