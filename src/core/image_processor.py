import cv2
import numpy as np

class ImageProcessor:
    def __init__(self):
        self.original_image = None
        self.current_image = None
        self.warped_image = None
        
        # State
        self.brightness = 0  # -100 to 100
        self.contrast = 1.0  # 0.1 to 3.0
        self.opacity = 1.0   # 0.0 to 1.0
        self.filter_mode = "None" # "None", "Edge", "Grayscale", "Invert"
        
        # Color Keying (Background Removal)
        self.key_color = None # Tuple (B, G, R)
        self.key_tolerance = 10 # 0 to 255
        
        # Overlay tools
        self.show_crosshair = False
        self.show_grid = False
        
        # Transform state
        self.transform_matrix = np.eye(3)
        self.screen_width = 1920
        self.screen_height = 1080
        
        # Manual adjustment offsets (applied after alignment matrix)
        self.manual_offset_x = 0.0
        self.manual_offset_y = 0.0
        self.manual_scale = 1.0
        self.manual_rotation = 0.0

    def load_image(self, file_path):
        # cv2.imread usually reads BGR. For tiff/png with alpha it might be BGRA
        # We will standardize on BGRA internally so we can manipulate opacity easily.
        img = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
        if img is None:
            return False
            
        if len(img.shape) == 2:
            # Grayscale
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)
        elif img.shape[2] == 3:
            # BGR
            img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
            
        self.original_image = img.copy()
        self.current_image = img.copy()
        self.process()
        return True

    def set_brightness(self, value):
        self.brightness = value
        self.process()
        
    def set_contrast(self, value):
        self.contrast = value
        self.process()
        
    def set_opacity(self, value):
        self.opacity = value
        self.process()
        
    def set_filter(self, filter_mode):
        self.filter_mode = filter_mode
        self.process()

    def set_color_key(self, color_bgr, tolerance):
        self.key_color = color_bgr
        self.key_tolerance = tolerance
        self.process()

    def set_screen_size(self, w, h):
        self.screen_width = w
        self.screen_height = h

    def set_manual_transform(self, x, y, scale, rotation):
        self.manual_offset_x = x
        self.manual_offset_y = y
        self.manual_scale = scale
        self.manual_rotation = rotation
        self.apply_transform()
        
    def set_overlay_tools(self, crosshair, grid):
        self.show_crosshair = crosshair
        self.show_grid = grid
        self.apply_transform() # these are drawn on the warped image

    def process(self):
        if self.original_image is None:
            return
            
        img = self.original_image.copy()
        
        # 1. Apply Filter
        if self.filter_mode == "Grayscale":
            gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
            img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGRA)
            
        elif self.filter_mode == "Edge":
            gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
            edges = cv2.Canny(gray, 100, 200)
            img = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGRA)
            
        elif self.filter_mode == "Invert":
            # Invert only RGB, keep A
            rgb = 255 - img[:, :, :3]
            img[:, :, :3] = rgb

        # 2. Apply Brightness and Contrast
        # cv2.convertScaleAbs does: dst = src * alpha + beta
        # alpha is contrast, beta is brightness
        img_bgr = img[:, :, :3]
        img_bgr = cv2.convertScaleAbs(img_bgr, alpha=self.contrast, beta=self.brightness)
        img[:, :, :3] = img_bgr

        # 3. Apply Color Keying
        alpha_channel = img[:, :, 3].copy()
        
        if self.key_color is not None:
            # Create a mask of pixels that match the key color within the tolerance
            lower_bound = np.array([
                max(0, self.key_color[0] - self.key_tolerance),
                max(0, self.key_color[1] - self.key_tolerance),
                max(0, self.key_color[2] - self.key_tolerance)
            ])
            upper_bound = np.array([
                min(255, self.key_color[0] + self.key_tolerance),
                min(255, self.key_color[1] + self.key_tolerance),
                min(255, self.key_color[2] + self.key_tolerance)
            ])
            
            # Find pixels in range
            mask = cv2.inRange(img[:, :, :3], lower_bound, upper_bound)
            # Set alpha to 0 where mask is 255
            alpha_channel[mask == 255] = 0

        # 4. Apply Opacity to Alpha Channel
        img[:, :, 3] = (alpha_channel * self.opacity).astype(np.uint8)

        self.current_image = img
        self.apply_transform()

    def calculate_1point_transform(self, img_pt, screen_pt):
        # Simply translation
        dx = screen_pt[0] - img_pt[0]
        dy = screen_pt[1] - img_pt[1]
        
        M = np.float32([
            [1, 0, dx],
            [0, 1, dy],
            [0, 0, 1]
        ])
        self.transform_matrix = M
        self.apply_transform()

    def calculate_2point_transform(self, img_pts, screen_pts):
        """
        img_pts: list of 2 (x,y) tuples
        screen_pts: list of 2 (x,y) tuples
        Calculates similarity transform: rotation, uniform scaling, translation
        """
        if len(img_pts) != 2 or len(screen_pts) != 2:
            return
            
        p1, p2 = np.array(img_pts[0]), np.array(img_pts[1])
        s1, s2 = np.array(screen_pts[0]), np.array(screen_pts[1])
        
        # Calculate scale
        d_img = np.linalg.norm(p2 - p1)
        d_screen = np.linalg.norm(s2 - s1)
        if d_img < 1e-5: return # Avoid division by zero
        scale = d_screen / d_img
        
        # Calculate angle
        angle_img = np.arctan2(p2[1] - p1[1], p2[0] - p1[0])
        angle_screen = np.arctan2(s2[1] - s1[1], s2[0] - s1[0])
        angle = angle_screen - angle_img
        
        # We can construct the 2x3 matrix directly, or use estimateAffinePartial2D
        src = np.array(img_pts, dtype=np.float32)
        dst = np.array(screen_pts, dtype=np.float32)
        M, _ = cv2.estimateAffinePartial2D(src, dst)
        
        if M is not None:
            # Pad to 3x3
            M3 = np.eye(3)
            M3[0:2, :] = M
            self.transform_matrix = M3
            self.apply_transform()

    def calculate_3point_transform(self, img_pts, screen_pts):
        """
        Calculates affine transform: translation, rotation, scale, shear.
        """
        if len(img_pts) != 3 or len(screen_pts) != 3:
            return
            
        src = np.array(img_pts, dtype=np.float32)
        dst = np.array(screen_pts, dtype=np.float32)
        
        M = cv2.getAffineTransform(src, dst)
        
        M3 = np.eye(3)
        M3[0:2, :] = M
        self.transform_matrix = M3
        self.apply_transform()
        
    def apply_transform(self):
        if self.current_image is None:
            return
            
        M_base = self.transform_matrix
        
        # Create manual transformation matrix
        center = (self.screen_width / 2, self.screen_height / 2)
        # 1. Rotate & Scale around center
        M_manual_rot_scale = cv2.getRotationMatrix2D(center, self.manual_rotation, self.manual_scale)
        M_manual = np.eye(3)
        M_manual[0:2, :] = M_manual_rot_scale
        
        # 2. Translate
        M_translate = np.eye(3)
        M_translate[0, 2] = self.manual_offset_x
        M_translate[1, 2] = self.manual_offset_y
        
        # Final matrix = Translate * RotateScale * Base Alignment
        M_final = np.dot(M_translate, np.dot(M_manual, M_base))
        
        M_final_2x3 = M_final[0:2, :]
        
        # Warp the image onto a canvas the size of the screen
        self.warped_image = cv2.warpAffine(
            self.current_image, 
            M_final_2x3, 
            (self.screen_width, self.screen_height),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0, 0) # Transparent border
        )
        
        # Draw Crosshair/Grid
        if self.show_crosshair or self.show_grid:
            self._draw_overlay_tools()

    def _draw_overlay_tools(self):
        if self.warped_image is None:
            return
            
        color = (0, 255, 0, 200) # Semi-transparent green
        thickness = 1
        h, w = self.warped_image.shape[:2]
        
        if self.show_crosshair:
            cx, cy = w // 2, h // 2
            cv2.line(self.warped_image, (cx, 0), (cx, h), color, thickness)
            cv2.line(self.warped_image, (0, cy), (w, cy), color, thickness)
            
        if self.show_grid:
            grid_size = 50
            for x in range(0, w, grid_size):
                cv2.line(self.warped_image, (x, 0), (x, h), color, thickness)
            for y in range(0, h, grid_size):
                cv2.line(self.warped_image, (0, y), (w, y), color, thickness)

    def get_warped_qimage(self):
        from PyQt6.QtGui import QImage
        if self.warped_image is None:
            return None
            
        # Convert BGRA to RGBA for PyQt
        rgba = cv2.cvtColor(self.warped_image, cv2.COLOR_BGRA2RGBA)
        h, w, ch = rgba.shape
        bytes_per_line = ch * w
        
        # Create QImage
        qimg = QImage(rgba.data, w, h, bytes_per_line, QImage.Format.Format_RGBA8888)
        # We need to copy because the data points to the numpy array which might get garbage collected
        return qimg.copy()

    def get_preview_qimage(self):
        from PyQt6.QtGui import QImage
        if self.current_image is None:
            return None
            
        rgba = cv2.cvtColor(self.current_image, cv2.COLOR_BGRA2RGBA)
        h, w, ch = rgba.shape
        bytes_per_line = ch * w
        qimg = QImage(rgba.data, w, h, bytes_per_line, QImage.Format.Format_RGBA8888)
        return qimg.copy()

    def save_image(self, path):
        if self.warped_image is not None:
            cv2.imwrite(path, self.warped_image)
            return True
        return False
