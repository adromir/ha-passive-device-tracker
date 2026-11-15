"""Constants for the Passive Device Tracker integration."""

DOMAIN = "passive_device_tracker"

# Device Registry info
MANUFACTURER = "Omni Consumer Products"
DEFAULT_MODEL = "Passive Device Tracker"

# Configuration keys
CONF_NAME = "name"
CONF_INTERFACES = "interfaces"

INTERFACE_LAN = "lan"
INTERFACE_WLAN = "wlan"
INTERFACE_BLUETOOTH = "bluetooth"

ALL_INTERFACES = [INTERFACE_LAN, INTERFACE_WLAN, INTERFACE_BLUETOOTH]

CONF_LAN_IP = "lan_ip"
CONF_LAN_MAC = "lan_mac"
CONF_WLAN_IP = "wlan_ip"
CONF_WLAN_MAC = "wlan_mac"
CONF_BT_MAC = "bluetooth_mac"

CONF_CONSIDER_HOME = "consider_home"
DEFAULT_CONSIDER_HOME = 180  # seconds

CONF_PING_INTERVAL = "ping_interval"
DEFAULT_PING_INTERVAL = 30  # seconds

CONF_PING_TIMEOUT = "ping_timeout"
DEFAULT_PING_TIMEOUT = 2  # seconds

# Attributes
ATTR_LAST_SEEN_BY = "last_seen_by"
ATTR_ACTIVE_INTERFACES = "active_interfaces"
ATTR_LAN_STATUS = "lan_status"
ATTR_WLAN_STATUS = "wlan_status"
ATTR_BT_STATUS = "bluetooth_status"
ATTR_LAN_IP = "lan_ip"
ATTR_WLAN_IP = "wlan_ip"
ATTR_BT_RSSI = "bluetooth_rssi"
ATTR_CONSIDER_HOME = "consider_home"
