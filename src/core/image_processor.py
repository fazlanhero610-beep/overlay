import cv2
import numpy as np
import uuid

class ImageLayer:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.name = "Layer"
        self.file_path = None
        self.original_image = None
        self.current_image = None
        self.warped_image = None
        
        # State
        self.brightness = 0  # -100 to 100
        self.contrast = 1.0  # 0.1 to 3.0
        self.opacity = 1.0   # 0.0 to 1.0
        self.filter_mode = "None"
        
        # Flipping
        self.flip_h = False
        self.flip_v = False
        
        # Color Keying (Background Removal)
        self.key_color = None
        self.key_tolerance = 10
        
        # Transform state
        self.transform_matrix = np.eye(3)
        self.manual_offset_x = 0.0
        self.manual_offset_y = 0.0
        self.manual_scale = 1.0
        self.manual_rotation = 0.0

        self.visible = True

class ImageProcessor:
    def __init__(self):
        self.layers = [] # List of ImageLayer objects
        self.active_layer_idx = -1

        # Global state
        self.screen_width = 1920
        self.screen_height = 1080
        self.show_crosshair = False
        self.show_grid = False
        self.composite_image = None

    def add_layer(self, file_path, name=None):
        layer = ImageLayer()
        img = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
        if img is None:
            return False
            
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)
        elif img.shape[2] == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
            
        layer.original_image = img.copy()
        layer.current_image = img.copy()
        layer.file_path = file_path
        if name:
            layer.name = name
        else:
            import os
            layer.name = os.path.basename(file_path)

        self.layers.append(layer)
        self.active_layer_idx = len(self.layers) - 1
        self.process_layer(self.active_layer_idx)
        return True

    def remove_layer(self, idx):
        if 0 <= idx < len(self.layers):
            self.layers.pop(idx)
            if self.active_layer_idx >= len(self.layers):
                self.active_layer_idx = len(self.layers) - 1
            self.apply_all_transforms()
            return True
        return False

    def get_active_layer(self):
        if 0 <= self.active_layer_idx < len(self.layers):
            return self.layers[self.active_layer_idx]
        return None

    def set_active_layer(self, idx):
        if 0 <= idx < len(self.layers):
            self.active_layer_idx = idx

    def crop_image(self, x, y, w, h):
        layer = self.get_active_layer()
        if layer and layer.original_image is not None:
            layer.original_image = layer.original_image[y:y+h, x:x+w]
            self.process_layer(self.active_layer_idx)

    def clear_all(self):
        self.layers = []
        self.active_layer_idx = -1
        self.composite_image = None

    # Properties proxying to active layer
    @property
    def current_image(self):
        layer = self.get_active_layer()
        return layer.current_image if layer else None

    @property
    def brightness(self):
        layer = self.get_active_layer()
        return layer.brightness if layer else 0

    @property
    def contrast(self):
        layer = self.get_active_layer()
        return layer.contrast if layer else 1.0

    @property
    def opacity(self):
        layer = self.get_active_layer()
        return layer.opacity if layer else 1.0

    @property
    def filter_mode(self):
        layer = self.get_active_layer()
        return layer.filter_mode if layer else "None"

    @property
    def flip_h(self):
        layer = self.get_active_layer()
        return layer.flip_h if layer else False

    @property
    def flip_v(self):
        layer = self.get_active_layer()
        return layer.flip_v if layer else False

    @property
    def transform_matrix(self):
        layer = self.get_active_layer()
        return layer.transform_matrix if layer else np.eye(3)

    @transform_matrix.setter
    def transform_matrix(self, val):
        layer = self.get_active_layer()
        if layer: layer.transform_matrix = val

    def set_brightness(self, value):
        layer = self.get_active_layer()
        if layer:
            layer.brightness = value
            self.process_layer(self.active_layer_idx)
        
    def set_contrast(self, value):
        layer = self.get_active_layer()
        if layer:
            layer.contrast = value
            self.process_layer(self.active_layer_idx)
        
    def set_opacity(self, value):
        layer = self.get_active_layer()
        if layer:
            layer.opacity = value
            self.process_layer(self.active_layer_idx)
        
    def set_filter(self, filter_mode):
        layer = self.get_active_layer()
        if layer:
            layer.filter_mode = filter_mode
            self.process_layer(self.active_layer_idx)

    def set_flip(self, flip_horizontal, flip_vertical):
        layer = self.get_active_layer()
        if layer:
            layer.flip_h = flip_horizontal
            layer.flip_v = flip_vertical
            self.process_layer(self.active_layer_idx)

    def set_color_key(self, color_bgr, tolerance):
        layer = self.get_active_layer()
        if layer:
            layer.key_color = color_bgr
            layer.key_tolerance = tolerance
            self.process_layer(self.active_layer_idx)

    def set_screen_size(self, w, h):
        self.screen_width = w
        self.screen_height = h
        self.apply_all_transforms()

    def set_manual_transform(self, x, y, scale, rotation):
        layer = self.get_active_layer()
        if layer:
            layer.manual_offset_x = x
            layer.manual_offset_y = y
            layer.manual_scale = scale
            layer.manual_rotation = rotation
            self.apply_layer_transform(self.active_layer_idx)
            self.composite_layers()
        
    def set_overlay_tools(self, crosshair, grid):
        self.show_crosshair = crosshair
        self.show_grid = grid
        self.composite_layers() # Redraw composite with tools

    def process_layer(self, idx):
        if not (0 <= idx < len(self.layers)): return
        layer = self.layers[idx]
        if layer.original_image is None: return
            
        img = layer.original_image.copy()
        
        # 1. Apply Filter
        if layer.filter_mode == "Grayscale":
            gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
            img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGRA)
        elif layer.filter_mode == "Edge":
            gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
            edges = cv2.Canny(gray, 100, 200)
            img = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGRA)
        elif layer.filter_mode == "Invert":
            rgb = 255 - img[:, :, :3]
            img[:, :, :3] = rgb
        elif layer.filter_mode == "Blur":
            blurred = cv2.GaussianBlur(img[:, :, :3], (15, 15), 0)
            img[:, :, :3] = blurred
        elif layer.filter_mode == "Sharpen":
            kernel = np.array([[0, -1, 0], [-1, 5,-1], [0, -1, 0]])
            sharpened = cv2.filter2D(img[:, :, :3], -1, kernel)
            img[:, :, :3] = sharpened
        elif layer.filter_mode == "Red Tint":
            img[:, :, 0] = 0
            img[:, :, 1] = 0
        elif layer.filter_mode == "Green Tint":
            img[:, :, 0] = 0
            img[:, :, 2] = 0
        elif layer.filter_mode == "Blue Tint":
            img[:, :, 1] = 0
            img[:, :, 2] = 0

        # 2. Apply Brightness and Contrast
        img_bgr = img[:, :, :3]
        img_bgr = cv2.convertScaleAbs(img_bgr, alpha=layer.contrast, beta=layer.brightness)
        img[:, :, :3] = img_bgr

        # 3. Apply Color Keying
        alpha_channel = img[:, :, 3].copy()
        if layer.key_color is not None:
            lower_bound = np.array([
                max(0, layer.key_color[0] - layer.key_tolerance),
                max(0, layer.key_color[1] - layer.key_tolerance),
                max(0, layer.key_color[2] - layer.key_tolerance)
            ])
            upper_bound = np.array([
                min(255, layer.key_color[0] + layer.key_tolerance),
                min(255, layer.key_color[1] + layer.key_tolerance),
                min(255, layer.key_color[2] + layer.key_tolerance)
            ])
            mask = cv2.inRange(img[:, :, :3], lower_bound, upper_bound)
            alpha_channel[mask == 255] = 0

        # 4. Apply Opacity to Alpha Channel
        img[:, :, 3] = (alpha_channel * layer.opacity).astype(np.uint8)

        # 5. Apply Flipping
        if layer.flip_h: img = cv2.flip(img, 1)
        if layer.flip_v: img = cv2.flip(img, 0)

        layer.current_image = img
        self.apply_layer_transform(idx)
        self.composite_layers()

    def calculate_1point_transform(self, img_pt, screen_pt):
        layer = self.get_active_layer()
        if not layer: return
        # Simply translation
        dx = screen_pt[0] - img_pt[0]
        dy = screen_pt[1] - img_pt[1]
        
        M = np.float32([
            [1, 0, dx],
            [0, 1, dy],
            [0, 0, 1]
        ])
        layer.transform_matrix = M
        self.apply_layer_transform(self.active_layer_idx)
        self.composite_layers()

    def calculate_2point_transform(self, img_pts, screen_pts):
        layer = self.get_active_layer()
        if not layer: return
        if len(img_pts) != 2 or len(screen_pts) != 2:
            return
            
        src = np.array(img_pts, dtype=np.float32)
        dst = np.array(screen_pts, dtype=np.float32)
        M, _ = cv2.estimateAffinePartial2D(src, dst)
        
        if M is not None:
            M3 = np.eye(3)
            M3[0:2, :] = M
            layer.transform_matrix = M3
            self.apply_layer_transform(self.active_layer_idx)
            self.composite_layers()

    def calculate_3point_transform(self, img_pts, screen_pts):
        layer = self.get_active_layer()
        if not layer: return
        if len(img_pts) != 3 or len(screen_pts) != 3:
            return
            
        src = np.array(img_pts, dtype=np.float32)
        dst = np.array(screen_pts, dtype=np.float32)
        M = cv2.getAffineTransform(src, dst)
        
        M3 = np.eye(3)
        M3[0:2, :] = M
        layer.transform_matrix = M3
        self.apply_layer_transform(self.active_layer_idx)
        self.composite_layers()
        
    def apply_all_transforms(self):
        for i in range(len(self.layers)):
            self.apply_layer_transform(i)
        self.composite_layers()

    def apply_layer_transform(self, idx):
        if not (0 <= idx < len(self.layers)): return
        layer = self.layers[idx]
        if layer.current_image is None: return
            
        M_base = layer.transform_matrix
        center = (self.screen_width / 2, self.screen_height / 2)
        M_manual_rot_scale = cv2.getRotationMatrix2D(center, layer.manual_rotation, layer.manual_scale)
        M_manual = np.eye(3)
        M_manual[0:2, :] = M_manual_rot_scale
        
        M_translate = np.eye(3)
        M_translate[0, 2] = layer.manual_offset_x
        M_translate[1, 2] = layer.manual_offset_y
        
        M_final = np.dot(M_translate, np.dot(M_manual, M_base))
        M_final_2x3 = M_final[0:2, :]
        
        layer.warped_image = cv2.warpAffine(
            layer.current_image,
            M_final_2x3, 
            (self.screen_width, self.screen_height),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0, 0)
        )

    def composite_layers(self):
        # Create empty transparent canvas
        canvas = np.zeros((self.screen_height, self.screen_width, 4), dtype=np.uint8)

        # Composite layers bottom to top
        for layer in self.layers:
            if not layer.visible or layer.warped_image is None:
                continue

            # Simple alpha compositing
            src = layer.warped_image
            alpha_src = src[:, :, 3] / 255.0
            alpha_canvas = canvas[:, :, 3] / 255.0

            # Out alpha
            out_alpha = alpha_src + alpha_canvas * (1 - alpha_src)

            # Prevent division by zero
            safe_alpha = np.where(out_alpha == 0, 1.0, out_alpha)

            # Blend colors vectorized
            alpha_src_3d = np.expand_dims(alpha_src, axis=-1)
            alpha_canvas_3d = np.expand_dims(alpha_canvas, axis=-1)
            safe_alpha_3d = np.expand_dims(safe_alpha, axis=-1)

            canvas[:, :, :3] = (src[:, :, :3] * alpha_src_3d + canvas[:, :, :3] * alpha_canvas_3d * (1 - alpha_src_3d)) / safe_alpha_3d

            canvas[:, :, 3] = (out_alpha * 255).astype(np.uint8)

        self.composite_image = canvas
        
        # Draw Crosshair/Grid on top of everything
        if self.show_crosshair or self.show_grid:
            self._draw_overlay_tools()

    def _draw_overlay_tools(self):
        if self.composite_image is None:
            return
            
        color = (0, 255, 0, 200) # Semi-transparent green
        thickness = 1
        h, w = self.composite_image.shape[:2]
        
        if self.show_crosshair:
            cx, cy = w // 2, h // 2
            cv2.line(self.composite_image, (cx, 0), (cx, h), color, thickness)
            cv2.line(self.composite_image, (0, cy), (w, cy), color, thickness)
            
        if self.show_grid:
            grid_size = 50
            for x in range(0, w, grid_size):
                cv2.line(self.composite_image, (x, 0), (x, h), color, thickness)
            for y in range(0, h, grid_size):
                cv2.line(self.composite_image, (0, y), (w, y), color, thickness)

    def get_warped_qimage(self):
        from PyQt6.QtGui import QImage
        if self.composite_image is None:
            return None
            
        # Convert BGRA to RGBA for PyQt
        rgba = cv2.cvtColor(self.composite_image, cv2.COLOR_BGRA2RGBA)
        h, w, ch = rgba.shape
        bytes_per_line = ch * w
        
        # Create QImage
        qimg = QImage(rgba.data, w, h, bytes_per_line, QImage.Format.Format_RGBA8888)
        # We need to copy because the data points to the numpy array which might get garbage collected
        return qimg.copy()

    def get_preview_qimage(self):
        from PyQt6.QtGui import QImage
        layer = self.get_active_layer()
        if not layer or layer.current_image is None:
            return None
            
        rgba = cv2.cvtColor(layer.current_image, cv2.COLOR_BGRA2RGBA)
        h, w, ch = rgba.shape
        bytes_per_line = ch * w
        qimg = QImage(rgba.data, w, h, bytes_per_line, QImage.Format.Format_RGBA8888)
        return qimg.copy()

    def save_image(self, path):
        if self.composite_image is not None:
            cv2.imwrite(path, self.composite_image)
            return True
        return False
