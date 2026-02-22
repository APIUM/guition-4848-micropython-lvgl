"""LVGL widget demo on Guition ESP32-S3-4848S040."""

import time
import lvgl as lv
import board

display = board.init_display()

lv.demo_widgets()

while True:
    lv.task_handler()
    time.sleep_ms(5)
