# backend/utils/image_utils.py
import cv2
import numpy as np
from typing import Tuple
from pathlib import Path


def load_image(path: str):
    img = cv2.imread(str(path))
    if img is None:
        raise FileNotFoundError(f"Image not found or not readable: {path}")
    return img


def find_largest_quad_contour(gray):
    # returns 4-point approximated contour or None
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
    # pts: (4,2)
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
    Finds sheet corners and warps to out_size (w,h). Returns warped BGR image.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    quad = find_largest_quad_contour(gray)
    if quad is None:
        # fallback: resize & return as-is
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
    bbox coords assumed to be integers and within image bounds.
    """
    h_img, w_img = warped_bgr.shape[:2]
    # clamp coordinates
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
    # morphological open to remove speckle
    kernel = np.ones((3, 3), np.uint8)
    th = cv2.morphologyEx(th, cv2.MORPH_OPEN, kernel)
    filled = cv2.countNonZero(th)
    total = th.size
    ratio = filled / float(total)
    return float(ratio)


def draw_overlay(warped_bgr, template: dict, answers: dict):
    """
    Draw bounding boxes and detected answers on a copy of warped image and return it.
    """
    overlay = warped_bgr.copy()
    for qmeta in template["questions"]:
        qid = str(qmeta["q"])
        for opt in qmeta["options"]:
            x, y, w, h = opt["bbox"]
            x1, y1, x2, y2 = int(x), int(y), int(x + w), int(y + h)
            cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 255, 0), 1)
            # mark selected option
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
