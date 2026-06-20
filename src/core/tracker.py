import cv2
import numpy as np
import time
from PyQt6.QtCore import QThread, pyqtSignal

try:
    import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False
    print("Warning: 'mss' module not found. Live tracking will be disabled. Run 'pip install mss' to enable.")

class FeatureTracker(QThread):
    # Emits (dx, dy, d_angle) showing the delta from the original template position
    tracking_update = pyqtSignal(float, float, float)
    tracking_lost = pyqtSignal()

    def __init__(self, search_region: tuple, parent=None):
        super().__init__(parent)
        self.running = False

        # Region where the template was originally found (x, y, w, h)
        self.template_region = search_region

        # Define a larger search window around the template to look for it in subsequent frames
        # e.g., expand by 200 pixels in all directions
        padding = 100
        self.search_window = (
            max(0, search_region[0] - padding),
            max(0, search_region[1] - padding),
            search_region[2] + padding * 2,
            search_region[3] + padding * 2
        )

        # Initialize MSS for fast screen capture
        if MSS_AVAILABLE:
            self.sct = mss.mss()
        else:
            self.sct = None

        # OpenCV tracking setup using ORB features
        self.orb = cv2.ORB_create()
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

        self.template_keypoints = None
        self.template_descriptors = None
        self.template_center = None

        # Grab the initial template from the screen right now
        self._initialize_template()

    def _initialize_template(self):
        if not MSS_AVAILABLE:
            return

        monitor = {
            "top": self.template_region[1],
            "left": self.template_region[0],
            "width": self.template_region[2],
            "height": self.template_region[3]
        }
        # Grab screen
        sct_img = self.sct.grab(monitor)
        # Convert to numpy array (BGRA) and then to Grayscale
        img = np.array(sct_img)
        gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)

        # Compute ORB features for the template
        self.template_keypoints, self.template_descriptors = self.orb.detectAndCompute(gray, None)

        # Calculate center of the original template in absolute screen coordinates
        self.template_center = (
            self.template_region[0] + self.template_region[2] / 2.0,
            self.template_region[1] + self.template_region[3] / 2.0
        )

    def run(self):
        if not MSS_AVAILABLE:
            print("Cannot run tracker without 'mss' module.")
            self.tracking_lost.emit()
            return

        if self.template_descriptors is None or len(self.template_keypoints) < 10:
            print("Not enough features found in the template to track.")
            self.tracking_lost.emit()
            return

        self.running = True

        while self.running:
            start_time = time.time()

            # Capture the expanded search window
            monitor = {
                "top": int(self.search_window[1]),
                "left": int(self.search_window[0]),
                "width": int(self.search_window[2]),
                "height": int(self.search_window[3])
            }

            try:
                sct_img = self.sct.grab(monitor)
                frame = np.array(sct_img)
                frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)

                # Detect features in the new frame
                kp, des = self.orb.detectAndCompute(frame_gray, None)

                if des is not None and len(kp) >= 10:
                    # Match features between template and current frame
                    matches = self.matcher.match(self.template_descriptors, des)

                    # Sort them in the order of their distance (lower is better)
                    matches = sorted(matches, key=lambda x: x.distance)

                    # Keep the top matches (e.g., top 15%)
                    good_matches = matches[:int(len(matches) * 0.15)]

                    if len(good_matches) >= 4: # Need at least 4 for affine transform
                        # Extract the matched keypoints
                        src_pts = np.float32([self.template_keypoints[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                        dst_pts = np.float32([kp[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

                        # Calculate Partial Affine Transform (Translation + Rotation + Scale)
                        # We use RANSAC to ignore outliers
                        M, inliers = cv2.estimateAffinePartial2D(src_pts, dst_pts, method=cv2.RANSAC)

                        if M is not None:
                            # The matrix M maps template coordinates to search_window coordinates
                            # We want to find where the center of the template moved to

                            # Template center relative to the template image itself
                            local_center = np.array([[[self.template_region[2]/2.0, self.template_region[3]/2.0]]], dtype=np.float32)

                            # Transformed center in the search_window coordinate space
                            transformed_center = cv2.transform(local_center, M)[0][0]

                            # Convert back to absolute screen coordinates
                            abs_new_center_x = self.search_window[0] + transformed_center[0]
                            abs_new_center_y = self.search_window[1] + transformed_center[1]

                            # Calculate translation delta from ORIGINAL position
                            dx = abs_new_center_x - self.template_center[0]
                            dy = abs_new_center_y - self.template_center[1]

                            # Calculate rotation delta (angle from the affine matrix)
                            angle = np.arctan2(M[1, 0], M[0, 0]) * (180.0 / np.pi)

                            self.tracking_update.emit(float(dx), float(dy), float(angle))

                            # Optional: Update the search window dynamically to follow the object if it moves far
                            # (This prevents it from leaving the search window entirely)
                            self.search_window = (
                                max(0, abs_new_center_x - self.search_window[2]/2),
                                max(0, abs_new_center_y - self.search_window[3]/2),
                                self.search_window[2],
                                self.search_window[3]
                            )
                        else:
                            self.tracking_lost.emit()
                    else:
                        self.tracking_lost.emit()
                else:
                    self.tracking_lost.emit()

            except Exception as e:
                print(f"Tracking error: {e}")
                self.tracking_lost.emit()

            # Sleep briefly to avoid 100% CPU lock, targeting ~20-30 FPS tracking
            elapsed = time.time() - start_time
            sleep_time = max(0, 0.033 - elapsed)
            time.sleep(sleep_time)

    def stop(self):
        self.running = False
        self.wait() # Wait for the thread to safely finish its loop
