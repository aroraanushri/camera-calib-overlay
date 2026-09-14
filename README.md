
## Camera Calibration Script

Use `camera_calib.py` to overlay a reference image on a live camera feed and adjust its position, scale, rotation, and opacity.

### Run

```shell
python3 camera_calib.py path/to/reference_image.png --camera 0
```

<img width="2560" height="1440" alt="Screenshot from 2026-07-03 18-10-22" src="https://github.com/user-attachments/assets/6e419180-90c9-4ff8-8054-13b65affd61c" />


### Notes

* `path/to/reference_image.png` is the image you want to calibrate against.
* `--camera 0` selects the camera device; change the value if your camera uses a different ID.
* Use a PNG with an alpha channel for the best overlay results.
* The window supports keyboard controls for moving, scaling, rotating, pausing, saving, and resetting the overlay.

---
