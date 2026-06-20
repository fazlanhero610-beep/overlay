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

        # OpenCV tracking setup using SIFT features (better for text and smooth details)
        self.sift = cv2.SIFT_create()

        # SIFT uses L2 distance
        index_params = dict(algorithm=1, trees=5) # KDTree
        search_params = dict(checks=50)
        self.matcher = cv2.FlannBasedMatcher(index_params, search_params)

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

        # Compute SIFT features for the template
        self.template_keypoints, self.template_descriptors = self.sift.detectAndCompute(gray, None)

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

        # Lowered threshold to 4 (minimum needed for homography) so we don't bail on small text features easily
        if self.template_descriptors is None or len(self.template_keypoints) < 4:
            print(f"Not enough features found in the template to track. Found: {len(self.template_keypoints) if self.template_keypoints else 0}")
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
                kp, des = self.sift.detectAndCompute(frame_gray, None)

                if des is not None and len(kp) >= 4:
                    # Match features using KNN
                    matches = self.matcher.knnMatch(self.template_descriptors, des, k=2)

                    # Apply Lowe's ratio test to filter out bad matches
                    good_matches = []
                    for match_set in matches:
                        if len(match_set) == 2:
                            m, n = match_set
                            if m.distance < 0.7 * n.distance:
                                good_matches.append(m)
                        elif len(match_set) == 1:
                            good_matches.append(match_set[0])

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
