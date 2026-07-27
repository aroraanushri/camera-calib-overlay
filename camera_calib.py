import cv2
import numpy as np
import argparse
from pathlib import Path

class CameraCalibration:
    def __init__(self, image_path, camera_id=0):
        self.image_path = image_path
        self.cap = cv2.VideoCapture(camera_id)
        
        # Load reference image
        self.ref_image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
        if self.ref_image is None:
            raise ValueError(f"Could not load image: {image_path}")
        
        # Get image dimensions
        if self.ref_image.shape[2] == 4:  # Has alpha channel
            self.has_alpha = True
        else:
            self.has_alpha = False
            # Add alpha channel if not present
            self.ref_image = cv2.cvtColor(self.ref_image, cv2.COLOR_BGR2BGRA)
        
        # Calibration parameters
        self.opacity = 0.5  # 0.0 to 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.scale = 1.0
        self.rotation = 0  # degrees
        self._auto_positioned = False
        
        self.paused = False
        
    def resize_image(self, img, scale):
        h, w = img.shape[:2]
        new_h, new_w = int(h * scale), int(w * scale)
        return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    
    def rotate_image(self, img, angle):
        h, w = img.shape[:2]
        center = (w // 2, h // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(img, matrix, (w, h), 
                                 borderMode=cv2.BORDER_CONSTANT,
                                 borderValue=(0, 0, 0, 0))
        return rotated

    def auto_place_overlay(self, frame_shape):
        frame_h, frame_w = frame_shape[:2]
        overlay_h, overlay_w = self.ref_image.shape[:2]

        max_w = frame_w * 0.85
        max_h = frame_h * 0.85
        fit_scale = min(max_w / overlay_w, max_h / overlay_h, 1.0)

        self.scale = fit_scale
        placed_w = int(overlay_w * self.scale)
        placed_h = int(overlay_h * self.scale)
        self.offset_x = max(0, (frame_w - placed_w) // 2)
        self.offset_y = max(0, (frame_h - placed_h) // 2)
        self._auto_positioned = True
    
    def overlay_image(self, frame, overlay_img, opacity, offset_x, offset_y):
        h_frame, w_frame = frame.shape[:2]
        h_overlay, w_overlay = overlay_img.shape[:2]
        
        # Calculate position
        x1 = max(0, offset_x)
        y1 = max(0, offset_y)
        x2 = min(w_frame, offset_x + w_overlay)
        y2 = min(h_frame, offset_y + h_overlay)
        
        # Calculate crop region in overlay
        crop_x1 = max(0, -offset_x)
        crop_y1 = max(0, -offset_y)
        crop_x2 = crop_x1 + (x2 - x1)
        crop_y2 = crop_y1 + (y2 - y1)
        
        if x2 > x1 and y2 > y1:
            overlay_crop = overlay_img[crop_y1:crop_y2, crop_x1:crop_x2]
            
            if overlay_crop.shape[2] == 4:
                alpha = overlay_crop[:, :, 3] / 255.0 * opacity
                for c in range(3):
                    frame[y1:y2, x1:x2, c] = (
                        frame[y1:y2, x1:x2, c] * (1 - alpha) +
                        overlay_crop[:, :, c] * alpha
                    )
            else:
                frame[y1:y2, x1:x2] = (
                    frame[y1:y2, x1:x2] * (1 - opacity) +
                    overlay_crop * opacity
                )
        
        return frame
    
    def print_controls(self):
        print("\n" + "="*50)
        print("CAMERA CALIBRATION CONTROLS")
        print("="*50)
        print("Opacity (Transparency):")
        print("  UP/DOWN      - Increase/decrease opacity")
        print("\nPosition:")
        print("  Arrow Keys   - Move overlay image")
        print("  W/A/S/D      - Fine movement (1px)")
        print("\nScale/Zoom:")
        print("  [ / ]        - Decrease/increase size")
        print("  { / }        - Fine size adjustment")
        print("\nRotation:")
        print("  Q / E        - Rotate left/right (5°)")
        print("  Shift+Q/E    - Fine rotation (1°)")
        print("\nOther:")
        print("  SPACE        - Pause/resume camera")
        print("  R            - Reset all values")
        print("  S            - Save current settings")
        print("  P            - Print current values")
        print("  ESC          - Exit")
        print("="*50 + "\n")
    
    def print_current_values(self):
        print(f"\nCurrent Settings:")
        print(f"  Opacity:  {self.opacity:.2f} (0.0-1.0)")
        print(f"  Position: X={self.offset_x}, Y={self.offset_y}")
        print(f"  Scale:    {self.scale:.2f}")
        print(f"  Rotation: {self.rotation}°")
    
    def save_settings(self):
        settings = {
            'opacity': self.opacity,
            'offset_x': self.offset_x,
            'offset_y': self.offset_y,
            'scale': self.scale,
            'rotation': self.rotation
        }
        settings_file = Path(self.image_path).stem + "_calibration.txt"
        with open(settings_file, 'w') as f:
            for key, value in settings.items():
                f.write(f"{key}={value}\n")
        print(f"Settings saved to {settings_file}")
    
    def reset_values(self):
        self.opacity = 0.5
        self.offset_x = 0
        self.offset_y = 0
        self.scale = 1.0
        self.rotation = 0
        print("All values reset to default")
    
    def run(self):
        self.print_controls()
        window_name = "Camera Calibration"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        
        while True:
            if not self.paused:
                ret, frame = self.cap.read()
                if not ret:
                    print("Error: Could not read frame")
                    break

                if not self._auto_positioned:
                    self.auto_place_overlay(frame.shape)
            
            # Prepare overlay
            overlay = self.ref_image.copy()
            overlay = self.resize_image(overlay, self.scale)
            overlay = self.rotate_image(overlay, self.rotation)
            
            # Blend images
            frame = self.overlay_image(frame, overlay, self.opacity, 
                                      self.offset_x, self.offset_y)
            
            # Add UI text
            h, w = frame.shape[:2]
            cv2.putText(frame, f"Opacity: {self.opacity:.2f}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Scale: {self.scale:.2f}x", (10, 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Rotation: {self.rotation}°", (10, 110),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Pos: ({self.offset_x}, {self.offset_y})", (10, 150),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            status = "PAUSED" if self.paused else "LIVE"
            cv2.putText(frame, status, (w - 150, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            cv2.imshow(window_name, frame)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == 27:  # ESC
                break
            elif key == ord(' '):  # Space - pause/resume
                self.paused = not self.paused
            elif key == ord('r'):  # Reset
                self.reset_values()
            elif key == ord('s'):  # Save
                self.save_settings()
            elif key == ord('p'):  # Print values
                self.print_current_values()
            
            # Opacity control
            elif key == 82:  # UP arrow
                self.opacity = min(1.0, self.opacity + 0.05)
            elif key == 84:  # DOWN arrow
                self.opacity = max(0.0, self.opacity - 0.05)
            
            # Position control
            elif key == 83:  # RIGHT arrow
                self.offset_x += 10
            elif key == 81:  # LEFT arrow
                self.offset_x -= 10
            elif key == 82:  # UP arrow (already used, use W/A/S/D instead)
                self.offset_y -= 10
            elif key == 84:  # DOWN arrow (already used)
                self.offset_y += 10
            
            elif key == ord('w'):  # W - fine up
                self.offset_y -= 1
            elif key == ord('s'):  # S - fine down
                self.offset_y += 1
            elif key == ord('a'):  # A - fine left
                self.offset_x -= 1
            elif key == ord('d'):  # D - fine right
                self.offset_x += 1
            
            # Scale control
            elif key == ord('['):  # Decrease size
                self.scale = max(0.1, self.scale - 0.1)
            elif key == ord(']'):  # Increase size
                self.scale += 0.1
            elif key == ord('{'):  # Fine decrease
                self.scale = max(0.1, self.scale - 0.01)
            elif key == ord('}'):  # Fine increase
                self.scale += 0.01
            
            # Rotation control
            elif key == ord('q'):  # Q - rotate left
                self.rotation -= 5
            elif key == ord('e'):  # E - rotate right
                self.rotation += 5
            elif key == ord('Q'):  # Shift+Q - fine rotate left
                self.rotation -= 1
            elif key == ord('E'):  # Shift+E - fine rotate right
                self.rotation += 1
        
        self.cap.release()
        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description="Camera Calibration Tool")
    parser.add_argument("image", help="Path to reference image (PNG with alpha for best results)")
    parser.add_argument("--camera", type=int, default=0, help="Camera ID (default: 0)")
    
    args = parser.parse_args()
    
    try:
        calibrator = CameraCalibration(args.image, args.camera)
        calibrator.run()
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())