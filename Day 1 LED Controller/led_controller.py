import RPi.GPIO as GPIO
import time
# Import the LCD library
from RPLCD.i2c import CharLCD

# --- Configuration ---
# Define which pin is for what
LED_PIN = 17
BUTTON_PIN = 18

# LCD Configuration
# You might need to change the address and port expander chip
# Common addresses: 0x27, 0x3f
# Common chips: 'PCF8574', 'PCF8574A'
lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1,
              cols=16, rows=2, dotsize=8,
              charmap='A02',
              auto_linebreaks=True,
              backlight_enabled=False)

# This is for controlling brightness
pwm = None

def setup():
    """Sets up the GPIO pins and the LCD."""
    global pwm
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_PIN, GPIO.OUT)
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    pwm = GPIO.PWM(LED_PIN, 100) # Setup PWM for brightness control
    
    # Clear the LCD screen on startup with a custom message
    lcd.clear()
    lcd.write_string("Day 1 Project:")
    time.sleep(2)
    lcd.write_string("  LED Controller")
    time.sleep(2)
    lcd.clear()
    lcd.write_string("By Sushant :)")
    time.sleep(3)
    update_lcd("Date: 21 Aug 25")
    # Wait a moment before showing the next instruction
    time.sleep(3)
    update_lcd("Press button...")


def update_lcd(message):
    """A helper function to clear and write a new message to the LCD."""
    lcd.clear()
    lcd.write_string(message)

def main_loop():
    """The main part of the program that runs forever."""
    print("Program running. Press CTRL+C to stop.")
    
    # Start with mode 0 (OFF)
    mode = 0 # 0=OFF, 1=ON, 2=BLINK, 3=FADE
    
    # Variables for fading effect
    brightness = 0
    fade_direction = 1 # 1 means getting brighter, -1 means getting dimmer

    while True:
        # --- Check if the button is pressed ---
        if GPIO.input(BUTTON_PIN) == GPIO.HIGH:
            # Go to the next mode
            mode = (mode + 1) % 4 # A cleaner way to cycle 0, 1, 2, 3
            
            print(f"Button pressed. New mode: {mode}")
            
            # --- Update LCD based on the new mode ---
            if mode == 0:
                update_lcd("Mode: LED OFF")
            elif mode == 1:
                update_lcd("Mode: LED ON")
            elif mode == 2:
                update_lcd("Mode: Blinking")
            elif mode == 3:
                update_lcd("Mode: Fading")

            # Turn everything off before switching to the new mode
            pwm.stop()
            GPIO.output(LED_PIN, GPIO.LOW)
            
            # If the new mode is FADE, start the PWM
            if mode == 3:
                pwm.start(0)
            
            time.sleep(0.3) # A small delay to prevent one press from counting as many

        # --- Run the code for the current mode ---
        if mode == 1: # Solid ON
            GPIO.output(LED_PIN, GPIO.HIGH)
            
        elif mode == 2: # BLINK
            GPIO.output(LED_PIN, GPIO.HIGH)
            time.sleep(0.5)
            GPIO.output(LED_PIN, GPIO.LOW)
            time.sleep(0.5)

        elif mode == 3: # FADE (increase/decrease brightness)
            brightness = brightness + fade_direction
            
            if brightness >= 100: fade_direction = -1
            elif brightness <= 0: fade_direction = 1
            
            pwm.ChangeDutyCycle(brightness)
            time.sleep(0.02)

# --- Run the program ---
setup()
try:
    main_loop()
except KeyboardInterrupt:
    print("\nStopping program.")
finally:
    # Clean up everything when the program stops
    lcd.clear()
    lcd.backlight_enabled = False
    GPIO.cleanup()

