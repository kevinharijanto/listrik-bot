"""Debug script — try every TinyTuya Cloud API method to find device data."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
import tinytuya

Config.validate()
DEVICE_ID = Config.DEVICE_ID

cloud = tinytuya.Cloud(
    apiRegion=Config.TUYA_API_REGION,
    apiKey=Config.TUYA_API_KEY,
    apiSecret=Config.TUYA_API_SECRET,
)

# Method 1: getstatus (already known to return empty)
print("=== 1. cloud.getstatus() ===")
r = cloud.getstatus(Config.DEVICE_ID)
print(json.dumps(r, indent=2))

# Method 2: getdps 
print("\n=== 2. cloud.getdps() ===")
try:
    r = cloud.getdps(Config.DEVICE_ID)
    print(json.dumps(r, indent=2))
except Exception as e:
    print(f"Error: {e}")

# Method 3: Direct API call to /v1.0/devices/{id}/status
print("\n=== 3. Direct /v1.0/devices/{id}/status ===")
try:
    r = cloud._tuyaplatform(f"v1.0/devices/{DEVICE_ID}/status")
    print(json.dumps(r, indent=2))
except Exception as e:
    print(f"Error: {e}")

# Method 4: /v1.0/iot-03/devices/{id}/status
print("\n=== 4. /v1.0/iot-03/devices/{id}/status ===")
try:
    r = cloud._tuyaplatform(f"v1.0/iot-03/devices/{DEVICE_ID}/status")
    print(json.dumps(r, indent=2))
except Exception as e:
    print(f"Error: {e}")

# Method 5: /v2.0/cloud/thing/{id}/shadow/properties
print("\n=== 5. /v2.0/cloud/thing/{id}/shadow/properties ===")
try:
    r = cloud._tuyaplatform(f"v2.0/cloud/thing/{DEVICE_ID}/shadow/properties")
    print(json.dumps(r, indent=2))
except Exception as e:
    print(f"Error: {e}")

# Method 6: device specification (to understand the DPS structure)
print("\n=== 6. /v1.0/devices/{id}/specifications ===")
try:
    r = cloud._tuyaplatform(f"v1.0/devices/{DEVICE_ID}/specifications")
    print(json.dumps(r, indent=2))
except Exception as e:
    print(f"Error: {e}")
