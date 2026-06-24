import requests
import json
import time

ESP32_IP = "http://192.168.0.77"

def test_off():
    print("=== Test /off ===")
    r = requests.get(f"{ESP32_IP}/off")
    print(r.status_code, r.text)

def test_set():
    print("=== Test /set ===")
    payload = {
        "leds": [
            {"i": 11, "rgb": [255, 0, 0]},     # LED 1 - czerwony
            {"i": 12, "rgb": [0, 255, 0]},     # LED 2 - zielony
            {"i": 13, "rgb": [0, 0, 255]},     # LED 3 - niebieski
            {"i": 14, "rgb": [255, 255, 0]},   # LED 4 - żółty
            {"i": 15, "rgb": [255, 0, 255]},   # LED 5 - fioletowy
        ]
    }
    r = requests.post(f"{ESP32_IP}/set", json=payload)
    print(r.status_code, r.text)

def test_scan_board():
    print("=== Test /scan_board ===")
    print("Czekam na wciśnięcie przycisku")
    t0 = time.time()
    r = requests.get(f"{ESP32_IP}/scan_board")
    dt = time.time() - t0
    print(f"Odpowiedź po {dt:.2f} s:")
    print(r.status_code, r.text)
    try:
        data = r.json()
        print("JSON:", json.dumps(data, indent=2))
    except Exception:
        pass

if __name__ == "__main__":
    test_scan_board()
    test_set()
    time.sleep(5)
    test_off()
    time.sleep(2)
    
