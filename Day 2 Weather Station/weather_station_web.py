#
# Raspberry Pi Web-Enabled Weather Station
#
# This script reads data from a DHT11 sensor (temperature, humidity),
# displays it on an SSD1306 OLED screen with custom icons, hosts a
# web page with live data, and logs the data to a CSV file every 10 minutes.
#
# Required Libraries:
# sudo pip3 install adafruit-circuitpython-dht
# sudo pip3 install adafruit-circuitpython-ssd1306
# sudo pip3 install Pillow
# sudo pip3 install pytz
#
# Make sure to enable I2C on your Raspberry Pi using 'sudo raspi-config'
#

import time
from datetime import datetime
import pytz
import board
import busio
import adafruit_dht
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306
import threading
import http.server
import socketserver
import csv
import os

# --- Configuration ---
WEB_PORT = 8000
LOG_INTERVAL_SECONDS = 600  # 10 minutes
DATA_FILE = 'sensor_data.csv'
TIMEZONE = 'Asia/Kolkata'
LOCATION = 'Chapra, Bihar'

# --- Global variables for sharing data between threads ---
sensor_data = {'temperature': None, 'humidity': None}
data_lock = threading.Lock()


# --- Hardware Initialization ---
def init_hardware():
    """Initializes all connected hardware components."""
    global oled, dht11
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        oled = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3C)
        oled.fill(0)
        oled.show()
        print("OLED display initialized successfully.")
    except Exception as e:
        print(f"Error initializing OLED display: {e}")
        return False

    try:
        dht11 = adafruit_dht.DHT11(board.D4, use_pulseio=True)
        print("DHT11 sensor initialized successfully.")
    except Exception as e:
        print(f"Error initializing DHT11 sensor: {e}")
        return False

    return True


# --- OLED Display Management ---
def display_message(draw, image, font, text, duration):
    """Helper function to show a centered message on the OLED for a set duration."""
    draw.rectangle((0, 0, oled.width, oled.height), outline=0, fill=0)
    text_width, text_height = draw.textsize(text, font=font)
    x = (oled.width - text_width) // 2
    y = (oled.height - text_height) // 2
    draw.text((x, y), text, font=font, fill=255)
    oled.image(image)
    oled.show()
    time.sleep(duration)


def run_startup_sequence(draw, image, font_main, font_small):
    """Displays the startup messages on the OLED."""
    display_message(draw, image, font_main, "Hello :)", 3)
    display_message(draw, image, font_main, "Day 2", 3)
    display_message(draw, image, font_small, "Pi Weather Station", 3)
    display_message(draw, image, font_main, "By Sushant", 3)


def update_oled_display():
    """Continuously updates the OLED screen with sensor data and time."""
    try:
        font_main = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        font_icon_label = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
    except IOError:
        font_main = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_icon_label = ImageFont.load_default()

    image = Image.new("1", (oled.width, oled.height))
    draw = ImageDraw.Draw(image)

    # Run startup sequence once
    run_startup_sequence(draw, image, font_main, font_small)

    while True:
        with data_lock:
            temp = sensor_data['temperature']
            hum = sensor_data['humidity']

        draw.rectangle((0, 0, oled.width, oled.height), outline=0, fill=0)

        # Draw Time
        now_tz = datetime.now(pytz.timezone(TIMEZONE))
        time_str = now_tz.strftime("%I:%M:%S %p")
        time_width, _ = draw.textsize(time_str, font=font_small)
        draw.text(((oled.width - time_width) // 2, 0), time_str, font=font_small, fill=255)
        draw.line((0, 14, oled.width, 14), fill=100)

        # --- Temperature Section (Left) ---
        # Icon
        draw.ellipse((8, 28, 20, 40), outline=255, fill=0, width=1)
        draw.rectangle((12, 20, 16, 32), outline=255, fill=0)
        draw.rectangle((13, 25, 15, 31), outline=255, fill=255)
        # Label
        draw.text((12, 45), "T    \u00B0C", font=font_icon_label, fill=255)
        # Data
        temp_text = f"{temp:.1f}" if temp is not None else "N/A"
        draw.text((26, 25), temp_text, font=font_main, fill=255)

        # --- Humidity Section (Right) ---
        # Icon
        draw.arc((72, 28, 88, 44), 0, 180, fill=255, width=2)
        draw.line((72, 36, 80, 20), fill=255, width=2)
        draw.line((88, 36, 80, 20), fill=255, width=2)
        # Label
        draw.text((76, 45), "H    %", font=font_icon_label, fill=255)
        # Data
        hum_text = f"{hum:.1f}%" if hum is not None else "N/A"
        draw.text((92, 25), hum_text, font=font_main, fill=255)

        oled.image(image)
        oled.show()
        time.sleep(1)


# --- Data Logging ---
def write_log_entry(temp, hum):
    """Writes a single data entry to the CSV file."""
    timestamp = datetime.now(pytz.timezone(TIMEZONE)).strftime('%Y-%m-%d %H:%M:%S')
    try:
        with open(DATA_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, f"{temp:.1f}", f"{hum:.1f}"])
        return True
    except Exception as e:
        print(f"Error writing to log file: {e}")
        return False


def log_data_to_csv():
    """Logs sensor data to a CSV file at a specified interval."""
    while True:
        time.sleep(LOG_INTERVAL_SECONDS)
        with data_lock:
            temp = sensor_data['temperature']
            hum = sensor_data['humidity']

        if temp is not None and hum is not None:
            if write_log_entry(temp, hum):
                print(f"Data logged at {datetime.now(pytz.timezone(TIMEZONE)).strftime('%H:%M:%S')}")


# --- Web Server ---
class WeatherHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP request handler to serve live sensor data."""

    def do_GET(self):
        with data_lock:
            temp = sensor_data['temperature']
            hum = sensor_data['humidity']

        temp_str = f"{temp:.1f}" if temp is not None else "..."
        hum_str = f"{hum:.1f}" if hum is not None else "..."

        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Raspberry Pi Weather Station</title>
            <meta http-equiv="refresh" content="15">
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
            <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;700&display=swap" rel="stylesheet">
            <style>
                body {{
                    font-family: 'Poppins', sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                    text-align: center;
                }}
                .container {{
                    background: rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(10px);
                    border-radius: 20px;
                    padding: 2em 3em;
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
                }}
                h1 {{
                    font-weight: 700;
                    margin-bottom: 0.2em;
                }}
                p.location {{
                    font-weight: 300;
                    font-size: 1.2em;
                    margin-top: 0;
                    margin-bottom: 2em;
                    opacity: 0.8;
                }}
                .data-grid {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 2em;
                }}
                .data-box {{
                    background: rgba(255, 255, 255, 0.15);
                    padding: 1.5em;
                    border-radius: 15px;
                }}
                .data-box .label {{
                    font-size: 1em;
                    font-weight: 300;
                    opacity: 0.8;
                }}
                .data-box .value {{
                    font-size: 2.5em;
                    font-weight: 700;
                }}
            </style>
        </head>
        <body>
            <div class="container">
		<h1>Raspberry Pi Weather Station</h1>
                <h2>By Sushant</h2>
                <p class="location">{LOCATION}</p>
                <div class="data-grid">
                    <div class="data-box">
                        <div class="label">ðŸŒ¡ï¸ Temperature</div>
                        <div class="value">{temp_str}&deg;C</div>
                    </div>
                    <div class="data-box">
                        <div class="label">ðŸ’§ Humidity</div>
                        <div class="value">{hum_str}%</div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(bytes(html, "utf8"))


def run_web_server():
    """Starts the web server in a separate thread."""
    try:
        with socketserver.TCPServer(("", WEB_PORT), WeatherHTTPRequestHandler) as httpd:
            print(f"Web server started at http://<YOUR_PI_IP>:{WEB_PORT}")
            httpd.serve_forever()
    except Exception as e:
        print(f"Could not start web server: {e}")


# --- Main Application Logic ---
def main():
    """Main function to start all threads and read sensor data."""
    if not init_hardware():
        print("Hardware initialization failed. Exiting.")
        return

    # Create CSV file and header if it doesn't exist
    if not os.path.isfile(DATA_FILE):
        with open(DATA_FILE, 'w', newline='') as f:
            csv.writer(f).writerow(['Timestamp', 'Temperature (C)', 'Humidity (%)'])
        print(f"Created data log file: {DATA_FILE}")

    # Start background threads
    threading.Thread(target=run_web_server, daemon=True).start()
    threading.Thread(target=update_oled_display, daemon=True).start()
    threading.Thread(target=log_data_to_csv, daemon=True).start()

    print("Starting sensor reading loop... Press CTRL+C to exit.")
    first_log_done = False
    while True:
        try:
            temperature_c = dht11.temperature
            humidity = dht11.humidity

            if temperature_c is not None and humidity is not None:
                with data_lock:
                    sensor_data['temperature'] = temperature_c
                    sensor_data['humidity'] = humidity

                # Log the very first successful reading immediately
                if not first_log_done:
                    if write_log_entry(temperature_c, humidity):
                        print("First data point logged successfully.")
                        first_log_done = True
            else:
                print("DHT11 sensor read failed. Check wiring.")

        except RuntimeError as error:
            print(f"DHT11 Read error: {error.args[0]}")
            pass
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            break

        time.sleep(2.0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram stopped by user.")
    finally:
        if 'dht11' in globals():
            dht11.exit()
        if 'oled' in globals():
            oled.fill(0)
            oled.show()
        print("Hardware resources released. Exiting.")
