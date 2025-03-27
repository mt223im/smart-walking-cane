import pyRTOS
import time
import board
import digitalio
import math
import microcontroller
import watchdog
from watchdog import WatchDogMode
import supervisor
import wifi
import socketpool
import adafruit_requests


SSID = "Mustafa"
PASSWORD = "12345678"
SERVER_URL = "http://192.168.219.181:3000/obstacle"


def connect_wifi():
    try:
        print("📡 Connecting to WiFi...")
        wifi.radio.connect(SSID, PASSWORD)
        print("✅ Connected to WiFi, IP Address:", wifi.radio.ipv4_address)
        return wifi.radio
    except Exception as e:
        print("❌ WiFi connection failed:", e)
        return None

radio = connect_wifi()
pool = socketpool.SocketPool(radio)
requests = adafruit_requests.Session(pool)

# ✅ Watchdog Timer Settings
WDT_TIMEOUT = 8 
microcontroller.watchdog.timeout = WDT_TIMEOUT
microcontroller.watchdog.mode = WatchDogMode.RESET
microcontroller.watchdog.feed()

# ✅ Sleep Mode Button (GPIO13)
sleep_button = digitalio.DigitalInOut(board.GP13)
sleep_button.direction = digitalio.Direction.INPUT
sleep_button.pull = digitalio.Pull.UP
sleep_mode = False

# ✅ Define Ultrasonic Sensors (4 Sensors)
ULTRASONIC_SENSORS = [
    {"TRIG": digitalio.DigitalInOut(board.GP3), "ECHO": digitalio.DigitalInOut(board.GP2), "name": "Sensor 1", "range": 50},
    {"TRIG": digitalio.DigitalInOut(board.GP15), "ECHO": digitalio.DigitalInOut(board.GP14), "name": "Sensor 2", "range": 50},
    {"TRIG": digitalio.DigitalInOut(board.GP10), "ECHO": digitalio.DigitalInOut(board.GP11), "name": "Sensor 3", "range": 50},
    {"TRIG": digitalio.DigitalInOut(board.GP4), "ECHO": digitalio.DigitalInOut(board.GP5), "name": "Sensor 4", "range": 70},  # 🔥 New sensor detects at 70 cm
]

for sensor in ULTRASONIC_SENSORS:
    sensor["TRIG"].direction = digitalio.Direction.OUTPUT
    sensor["ECHO"].direction = digitalio.Direction.INPUT

# ✅ IR Sensor & Buzzer
ir_sensor = digitalio.DigitalInOut(board.GP16)
ir_sensor.direction = digitalio.Direction.INPUT
buzzer = digitalio.DigitalInOut(board.GP17)
buzzer.direction = digitalio.Direction.OUTPUT

object_detected = False
ir_object_detected = False

# ✅ Sleep Mode Function
def toggle_sleep():
    global sleep_mode
    sleep_mode = not sleep_mode

    if sleep_mode:
        print("💤 Entering Sleep Mode...")
        buzzer.value = False 
        time.sleep(1)
        microcontroller.reset()
    else:
        print("🚀 Waking Up...")

# ✅ OWA Function with Weights (for 4 sensors)
def normalize_weights(weights):
    total = sum(weights)
    return [w / total for w in weights] if total != 0 else weights

def owa_aggregation(values, weights):
    valid_values = [v for v in values if v != -1]
    
    if not valid_values:
        return -1
    
    if len(valid_values) != len(weights):
        weights = normalize_weights(weights[:len(valid_values)])

    sorted_values = sorted(valid_values, reverse=True)
    return round(sum(v * w for v, w in zip(sorted_values, weights)), 2)

# ✅ Kalman Filter
class KalmanFilter:
    def __init__(self, initial_value=0, process_noise=1e-2, measurement_noise=1e-1, estimate_error=1.0):
        self.q = process_noise
        self.r = measurement_noise
        self.p = estimate_error
        self.x = initial_value  

    def update(self, measurement):
        if measurement == -1:
            return self.x

        self.p += self.q
        k = self.p / (self.p + self.r)
        self.x += k * (measurement - self.x)
        self.p *= (1 - k)
        return round(self.x, 2)

# ✅ Initialize Kalman Filters
kalman_filters = [KalmanFilter() for _ in ULTRASONIC_SENSORS]

# ✅ Function to Send Data to Server
def send_data(data):
    try:
        response = requests.post(SERVER_URL, json=data)
        print("✅ Sent data:", response.text)
        response.close()
    except Exception as e:
        print("❌ Error sending data:", e)

# ✅ Sleep Mode Button Task
def button_task(self):
    last_state = sleep_button.value
    while True:
        current_state = sleep_button.value
        if current_state == False and last_state == True:
            time.sleep(0.2) 
            if sleep_button.value == False:
                toggle_sleep()
        last_state = current_state
        yield [pyRTOS.timeout(100)]

# ✅ Watchdog Task
def watchdog_task(self):
    while True:
        if sleep_mode:
            microcontroller.watchdog.feed()
            yield [pyRTOS.timeout(5000)]
        else:
            microcontroller.watchdog.feed()
        yield [pyRTOS.timeout(500)]

# ✅ IR Sensor Task
def ir_task(self):
    global ir_object_detected
    ir_detection_count = 0

    while True:
        if sleep_mode:
            buzzer.value = False  
            yield [pyRTOS.timeout(100)]
            continue

        ir_object_detected = not ir_sensor.value
        if ir_object_detected:
            ir_detection_count += 1
            print("IR Sensor detected an obstacle!")

        send_data({"ir_detections": ir_detection_count})
        microcontroller.watchdog.feed()
        yield [pyRTOS.timeout(100)]

# ✅ Ultrasonic Sensor Task
def ultrasonic_task(self):
    global object_detected
    detection_counts = {sensor["name"]: 0 for sensor in ULTRASONIC_SENSORS}

    while True:
        if sleep_mode:
            buzzer.value = False  
            yield [pyRTOS.timeout(500)]
            continue

        for index, sensor in enumerate(ULTRASONIC_SENSORS):
            raw_distance = read_ultrasonic(sensor["TRIG"], sensor["ECHO"])
            filtered_distance = kalman_filters[index].update(raw_distance)
            if raw_distance != -1 and filtered_distance <= sensor["range"]:
                detection_counts[sensor["name"]] += 1

        send_data({"ultrasonic_detections": detection_counts})
        microcontroller.watchdog.feed()
        yield [pyRTOS.timeout(500)]

# ✅ Buzzer Task
def buzzer_task(self):
    while True:
        if sleep_mode:
            buzzer.value = False
            yield [pyRTOS.timeout(100)]
            continue
        buzzer.value = object_detected or ir_object_detected
        yield [pyRTOS.timeout(500)]

# ✅ Add Tasks
pyRTOS.add_task(pyRTOS.Task(button_task))
pyRTOS.add_task(pyRTOS.Task(ultrasonic_task))
pyRTOS.add_task(pyRTOS.Task(ir_task))
pyRTOS.add_task(pyRTOS.Task(buzzer_task))
pyRTOS.add_task(pyRTOS.Task(watchdog_task))

# ✅ Start RTOS
pyRTOS.start()

