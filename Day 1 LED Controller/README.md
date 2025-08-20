# Day 1: Raspberry Pi – LED & LCD Controller  

This is the **first project** in my **“10 Days, 10 Projects”** series using the Raspberry Pi.  

![LED_Controller](Day1_LED_Controller.jpg)

The script allows a user to control an LED with a push button, cycling through **four modes**:  

- 🔴 **OFF**  
- 🟢 **ON**  
- ✨ **Blinking**  
- 🌗 **Fading (brightness control)**  

The **current mode** is displayed on a **16x2 I²C LCD screen**.  

---

## 🛠 Hardware Required  

- Raspberry Pi (3B+ or similar)  
- 1 × LED (any color)  
- 1 × 330Ω Resistor (for the LED)  
- 1 × Push Button  
- 1 × 16x2 I²C LCD Display  
- Breadboard + Jumper Wires  

---

## ⚙️ Setup and Installation  

### 1. Enable I²C Interface  
The LCD uses the I²C protocol.
- Enable it with:  

```bash
sudo raspi-config
```

- Navigate to the following menu:
- 
```bash
3 Interface Options → I5 I2C
```

- Select Yes to enable the interface and reboot if prompted.

### 2. Install LCD Library

This project requires the RPLCD Python library. On recent versions of Raspberry Pi OS, you must override the system package protection.

```bash
pip install RPLCD --break-system-packages
```

### 3. Check LCD Address

Before running the script, find your LCD’s unique I²C address.

```bash
i2cdetect -y 1
```
You’ll see a value like **27** or **3f**.

👉 Important: Update the address variable in the Python script to match this value.

### Running the Script

Navigate to the project directory in your terminal and run the main Python file:

```bash
python3 led_controller.py
```

The LCD will display a startup message. You can then press the push button to cycle through the different LED modes. To stop the program, press **CTRL + C**.
