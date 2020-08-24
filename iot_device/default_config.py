# default config for IoT49

import os

default_config = {
    'host_dir': os.path.expanduser(os.path.join(os.getenv('IOT49', '~/iot49'), 'mcu')),
    'mcu_dir': '/volumes/CIRCUITPY',
    'device_scan_interval': 1.0,
    'advertise_port': 50003,
    'connection_server_port': 50001,
}
