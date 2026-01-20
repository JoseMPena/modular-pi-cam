# https://github.com/jdc-cunningham/pi-zero-hq-cam/blob/master/camera/software/camera/camera.py

import os, time

from threading import Thread
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder, Quality
from libcamera import controls
from PIL import Image

class Camera:
  def __init__(self, main):
    self.main = main
    self.display = main.display
    self.img_base_path = os.getcwd() + "/captured-media/"
    self.mock_mode = False
    
    # Try to initialize camera, fall back to mock mode if not available
    try:
      self.picam2 = Picamera2()
      self.encoder = H264Encoder()
      # dimensions based on 4608x2592 resolution, set for camera module v3
      self.small_res_config = self.picam2.create_still_configuration(main={"size": (240, 240)}) # should not be a square
      self.full_res_config = self.picam2.create_still_configuration()
      self.picam2.configure(self.small_res_config)
      print("Camera initialized successfully")
    except (IndexError, RuntimeError) as e:
      print(f"WARNING: No camera detected ({e}). Running in MOCK MODE for development.")
      self.mock_mode = True
      self.picam2 = None
      self.encoder = None
      self.small_res_config = None
      self.full_res_config = None
    
    self.last_mode = "small"
    self.live_preview_active = False
    self.live_preview_pause = False
    self.display = main.display

  def start(self):
    if not self.mock_mode:
      self.picam2.start()
    else:
      print("MOCK: Camera start called")
    # 0 is infinity, 1 is 1 meter. 10 max is closest 1/10 meters or 10 cm

  def check_focus(self):
    if self.mock_mode:
      return
    
    if (self.main.focus_level == -1):
      self.picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous})
    else:
      # steps of 0.5 I guess, I'll use 1
      self.picam2.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": self.main.focus_level})

  def change_mode(self, mode):
    if self.mock_mode:
      print(f"MOCK: Change mode to {mode}")
      self.last_mode = mode
      return
    
    if (mode == "full"):
      self.picam2.switch_mode(self.full_res_config)
    else:
      self.picam2.switch_mode(self.small_res_config)
      self.last_mode = mode

  def take_photo(self):
    print('taking photo')
    time.sleep(0.25) # add delay for recoil of spring button
    img_path = self.img_base_path + str(time.time()).split(".")[0] + "f" + str(self.main.focus_level) + ".jpg"
    
    if self.mock_mode:
      print(f"MOCK: Would capture photo to {img_path}")
      return
    
    self.change_mode("full")
    self.picam2.capture_file(img_path)
    self.change_mode(self.last_mode)

  # you can do zoom-crop panning here
  def check_mod(self, pil_img):
    return pil_img
  
  def start_live_preview(self):
    Thread(target=self.live_preview).start()

  def live_preview(self):
    self.display.clear_screen()

    while (self.live_preview_active):
      branch_hit = False # wtf is this

      if (not self.live_preview_pause):
        # check focus
        self.check_focus()

        branch_hit = True
        
        if self.mock_mode:
          # Create a dummy image for mock mode
          pil_img = Image.new('RGB', (240, 240), color=(100, 100, 150))
        else:
          pil_img = self.picam2.capture_image()
        
        pil_img = self.check_mod(pil_img) # bad name

        # rotate down
        # pil_img_r1 = pil_img.rotate(-90)
        pil_img_r1 = pil_img
        
        # add focus info
        img_stamped = self.display.add_focus_level(pil_img_r1, self.main.focus_level)

        pil_img_r2 = img_stamped.rotate(270) # display is rotated left 90

        self.display.lcd.ShowImage(pil_img_r2)

      # after 1 min turn live preview off
      if (time.time() > self.main.live_preview_start + 30 and not self.live_preview_pause):
        branch_hit = True
        self.main.live_passthrough = False
        self.live_preview_pause = True
        # self.zoom_level = 1
        # self.pan_offset = [0, 0]
        self.display.clear_screen()
        self.change_mode("small")
        self.display.draw_menu("home")

      if (not branch_hit):
        time.sleep(0.1)

      branch_hit = False