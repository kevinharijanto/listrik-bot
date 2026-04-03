"""Power monitor module — reads Tuya smart plug via Cloud API or Local LAN."""

import logging
import tinytuya
from config import Config

logger = logging.getLogger(__name__)


class PowerMonitor:
    """Reads power data from a Tuya smart plug."""

    def __init__(self):
        self.mode = Config.CONNECTION_MODE
        self._cloud = None
        self._device = None
        self._init_connection()

    def _init_connection(self):
        if self.mode == "cloud":
            logger.info("Initializing Tuya Cloud connection (region=%s)", Config.TUYA_API_REGION)
            self._cloud = tinytuya.Cloud(
                apiRegion=Config.TUYA_API_REGION,
                apiKey=Config.TUYA_API_KEY,
                apiSecret=Config.TUYA_API_SECRET,
            )
        else:
            logger.info("Initializing Tuya Local connection (ip=%s)", Config.DEVICE_IP)
            self._device = tinytuya.Device(
                dev_id=Config.DEVICE_ID,
                address=Config.DEVICE_IP,
                local_key=Config.LOCAL_KEY,
            )
            self._device.set_version(Config.DEVICE_VERSION)

    def read(self):
        """Read current power data from the smart plug.
        
        Returns:
            dict with keys: voltage, current, power
            or None if reading failed.
        """
        try:
            if self.mode == "cloud":
                return self._read_cloud()
            else:
                return self._read_local()
        except Exception as e:
            logger.error("Failed to read power data: %s", e)
            return None

    def _read_cloud(self):
        """Read via Tuya Cloud API."""
        result = self._cloud.getstatus(Config.DEVICE_ID)
        logger.debug("Cloud API response: %s", result)

        if not result or "result" not in result:
            logger.error("Invalid cloud response: %s", result)
            return None

        # Cloud API returns DPS in a list format
        dps = {}
        for item in result["result"]:
            dps[str(item["code"])] = item["value"]

        voltage = None
        current = None

        # Cloud uses descriptive codes; fallback to numeric DPS IDs
        if "cur_voltage" in dps:
            voltage = dps["cur_voltage"] / 10.0
        elif "20" in dps:
            voltage = dps["20"] / 10.0

        if "cur_current" in dps:
            current = dps["cur_current"] / 1000.0
        elif "18" in dps:
            current = dps["18"] / 1000.0

        if voltage is None or current is None:
            logger.warning("Could not find voltage/current in cloud response: %s", dps)
            return None

        power = voltage * current

        return {
            "voltage": round(voltage, 1),
            "current": round(current, 3),
            "power": round(power, 1),
        }

    def _read_local(self):
        """Read via local LAN."""
        status = self._device.status()
        logger.debug("Local status response: %s", status)

        if not status or "dps" not in status:
            logger.error("Invalid local response: %s", status)
            return None

        dps = status["dps"]

        voltage = dps.get("20", 0) / 10.0
        current = dps.get("18", 0) / 1000.0
        power = voltage * current

        return {
            "voltage": round(voltage, 1),
            "current": round(current, 3),
            "power": round(power, 1),
        }
