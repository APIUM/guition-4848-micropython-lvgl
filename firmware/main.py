"""LVGL widget demo on Guition ESP32-S3-4848S040."""

import time
import lvgl as lv
import board

board.display_dev = board.init_display()

# -- Build a simple demo UI --------------------------------------------------

scr = lv.screen_active()
scr.set_style_bg_color(lv.color_hex(0x003A57), 0)

# Title
title = lv.label(scr)
title.set_text("Guition 4848 LVGL Demo")
title.set_style_text_color(lv.color_hex(0xFFFFFF), 0)
title.set_style_text_font(lv.font_montserrat_28, 0)
title.align(lv.ALIGN.TOP_MID, 0, 30)

# Subtitle
sub = lv.label(scr)
sub.set_text("ESP32-S3 \u2022 480x480 RGB \u2022 ST7701S")
sub.set_style_text_color(lv.color_hex(0x90CAF9), 0)
sub.set_style_text_font(lv.font_montserrat_16, 0)
sub.align(lv.ALIGN.TOP_MID, 0, 70)

# Slider
slider = lv.slider(scr)
slider.set_width(300)
slider.set_value(70, False)
slider.align(lv.ALIGN.CENTER, 0, -30)

slider_label = lv.label(scr)
slider_label.set_text("Slider: 70")
slider_label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)
slider_label.align_to(slider, lv.ALIGN.OUT_TOP_MID, 0, -10)

def slider_cb(evt):
    val = slider.get_value()
    slider_label.set_text("Slider: %d" % val)

slider.add_event_cb(slider_cb, lv.EVENT.VALUE_CHANGED, None)

# Button
btn = lv.button(scr)
btn.set_size(200, 60)
btn.align(lv.ALIGN.CENTER, 0, 60)

btn_label = lv.label(btn)
btn_label.set_text("Press Me")
btn_label.center()

btn_count = 0

def btn_cb(evt):
    global btn_count
    btn_count += 1
    btn_label.set_text("Pressed %d" % btn_count)

btn.add_event_cb(btn_cb, lv.EVENT.CLICKED, None)

# Bar (animated)
bar = lv.bar(scr)
bar.set_size(300, 20)
bar.align(lv.ALIGN.CENTER, 0, 150)
bar.set_value(0, False)

bar_label = lv.label(scr)
bar_label.set_text("Progress")
bar_label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)
bar_label.align_to(bar, lv.ALIGN.OUT_TOP_MID, 0, -10)

# Info footer
info = lv.label(scr)
info.set_text("MicroPython + LVGL on rgb_panel_lvgl driver")
info.set_style_text_color(lv.color_hex(0x607D8B), 0)
info.set_style_text_font(lv.font_montserrat_14, 0)
info.align(lv.ALIGN.BOTTOM_MID, 0, -20)

print("UI ready")

# -- Main loop ----------------------------------------------------------------

bar_val = 0
bar_dir = 1
tick = 0

while True:
    lv.task_handler()
    time.sleep_ms(5)

    tick += 1
    if tick % 10 == 0:
        bar_val += bar_dir
        if bar_val >= 100:
            bar_dir = -1
        elif bar_val <= 0:
            bar_dir = 1
        bar.set_value(bar_val, False)
