from gpiozero import Button
import time

button_a = Button(26, pull_up=True)
button_b = Button(19, pull_up=True)
button_c = Button(13, pull_up=True)


def button_a_held_cb():
    print('held button A')


def button_a_released_cb():
    print('released button A')


def button_b_pressed_cb():
    print('pressed button B')


button_a.when_held = button_a_held_cb
button_a.when_released = button_a_released_cb
button_b.when_pressed = button_b_pressed_cb

while True:
    if button_c.is_pressed:
        print("Button C is pressed")

    print('.')
    time.sleep(1)

