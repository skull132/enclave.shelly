#!/usr/bin/python

DOCUMENTATION = '''
---
module: wifi
short_description: A module for controlling the WiFi settings on a Shelly gen 2+ device.
version_added: "0.0.1"
description:
  - A module for controlling the WiFi settings on a Shelly gen 2+ device.
  -
  - The configuration of a Shelly's WiFi interface has 4 sections: "ap" for the access point it
  - can create itself. "sta" and "sta1" for WiFi client connections. And "roam" for the roaming settings.
  - This plugin lets you configure these individually.
options:
    configuring:
        description:
          - Determines which subsystem is being configured.
        required: true
        type: str
        choices: ["ap", "sta", "sta1", "roam"]
    timeout:
        description:
          - In milliseconds. Determines how long to wait until the module should become available again.
          - If the device is not available after the time specified, the module fails.
        required: false
        type: int
        default: 5000
    ssid:
        description:
          - The SSID for a given connection.
          - Required if configuring is "ap", "sta", or "sta1".
          -
          - If configuring is "ap", then this controls the SSID of the hosted WiFi network.
          - If configuring is "sta" or "sta1", then this controls the SSID of the WiFi network with which the
          - interface should connect to.
        required: false
        type: str
    password:
        description:
          - The password for a given connection.
          - Required if configuring is "ap", "sta", or "sta1".
          -
          - If configuring is "ap", then this controls the password of the hosted WiFi network.
          - If configuring is "sta" or "sta1", then this controls the password of the WiFi network with which the
          - interface should connect to.
        required: false
        type: str
    is_open:
        description:
          - True if the access point is open, false otherwise.
          - Required if configuring is "ap".
        required: false
        type: bool
    enable:
        description:
          - Controls whether or not the interface is enabled.
          - Required if configuring is "ap", "sta",  or "sta1".
        required: false
        type: bool
    range_extender:
        description:
          - Controls whether the range extender is enabled or not.
          - Not all Shelly devices have a range extender.
        required: false
        type: bool
    ipv4mode:
        description:
          - Sets the IPv4 mode of the device. Must be either "dhcp" or "static".
          - Required if configuring is "sta" or "sta1".
        required: false
        type: str
        choices: ["dhcp", "static"]
    ip:
        description:
          - Sets the IPv4 address that's used if ipv4mode is "static".
          - Required if ipv4mode is "static".
        required: false
        type: str
    netmask:
        description:
          - Sets the netmask that's used if ipv4mode is "static".
          - Required if ipv4mode is "static".
        required: false
        type: str
    gw:
        description:
          - Sets the gateway that's used if ipv4mode is "static".
          - Required if ipv4mode is "static".
        required: false
        type: str
    nameserver:
        description:
          - Sets the nameserver address that's used if ipv4mode is "static".
          - Required if ipv4mode is "static".
        required: false
        type: str
    rssi_thr:
        description:
          - Sets the RSSI threshold at which roaming is triggered.
          - Required if configuring is "roam".
        required: false
        type: int
    interval:
        description:
          - Sets the interval with which to scan for better access points.
          - Set to 0 to disable.
          - Required if configuring is "roam".
        require: false
        type: int
author:
    - RustedSkull (@skull132)
'''

EXAMPLES = '''
# Disable the access point.
- name: Disable AP
  enclave.shelly.wifi:
    configuring: ap
    ssid: ""
    password: ""
    is_open: false
    enable: false

# Set the primary WiFi connection to some network.
- name: Primary WiFi interface connection
  enaclave.shelly.wifi:
    configuring: sta
    ssid: my_home
    password: some_secret
    enable: true
    ipv4mode: dhcp
'''

RETURN = '''
restarted:
  description: Set to true if the module issued the restart command to the Shelly device.
  type: bool
  returned: always
'''


from dataclasses import dataclass, asdict
from typing import Optional

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.connection import Connection

import ansible_collections.enclave.shelly.plugins.module_utils.helpers as shelly_utils

@dataclass
class RangeExtenderConfig:
    enable: bool

@dataclass
class ApConfig:
    ssid: Optional[str]
    password: Optional[str]
    is_open: bool
    enable: bool
    range_extender: Optional[RangeExtenderConfig]

@dataclass
class StaConfig:
    ssid: Optional[str]
    password: Optional[str]
    is_open: bool
    enable: bool
    ipv4mode: str
    ip: Optional[str]
    netmask: Optional[str]
    gw: Optional[str]
    nameserver: Optional[str]

@dataclass
class RoamConfig:
    rssi_thr: int
    interval: int

@dataclass
class WifiConfig:
    ap: ApConfig
    sta: StaConfig
    sta1: StaConfig
    roam: RoamConfig

def result_into_wifi_config(result):
    ap_data = result["ap"]
    if "range_extender" in ap_data and ap_data["range_extender"] is not None:
        ap_data["range_extender"] = RangeExtenderConfig(**ap_data["range_extender"])
    
    ap = ApConfig(**ap_data)
    sta = StaConfig(**result["sta"])
    sta1 = StaConfig(**result["sta1"])
    roam = RoamConfig(**result["roam"])

    return WifiConfig(ap, sta, sta1, roam)

def compose_module_args():
    module_args = dict(
        configuring=dict(type="str", required=True, choices=["ap", "sta", "sta1", "roam"]),
        timeout=dict(type="int", required=False, default=5000)
    )
    ap_args = shelly_utils.dataclass_into_ansible_spec(ApConfig)
    ap_args["range_extender"] = dict(type="bool", required=False)
    module_args.update(ap_args)

    sta_args = shelly_utils.dataclass_into_ansible_spec(StaConfig)
    sta_args["ipv4mode"]["choices"] = ["dhcp", "static"]
    module_args.update(sta_args)

    roaming_args = shelly_utils.dataclass_into_ansible_spec(RoamConfig)
    module_args.update(roaming_args)

    return module_args

def run_module():
    module_args = compose_module_args()

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
        required_if=[
            ("configuring", "ap", ("ssid", "password", "is_open", "enable")),
            ("configuring", "sta", ("ssid", "password", "enable", "ipv4mode")),
            ("configuring", "sta1", ("ssid", "password", "enable", "ipv4mode")),
            ("configuring", "roam", ("rssi_thr", "interval")),
            ("ipv4mode", "static", ("ip", "netmask", "gw", "nameserver"))
        ]
    )

    result = dict(
        changed=False,
        restart_required=False
    )

    connection = Connection(module._socket_path)
    current_config = connection.send_request(
        data={
            "method": "Wifi.GetConfig"
        }
    )

    if module.params["configuring"] == "ap":
        data = shelly_utils.sanitize_dataclass_args(ApConfig, module.params.copy())
        if "range_extender" in data:
            data["range_extender"] = RangeExtenderConfig(data["range_extender"])
        data = shelly_utils.optional_strs_to_none(data)

        input_args = ApConfig(**data)
        existing_args = ApConfig(current_config["ap"])
    elif module.params["configuring"] == "sta" or module.params["configuring"] == "sta1":
        data = shelly_utils.sanitize_dataclass_args(StaConfig, module.params.copy())
        data = shelly_utils.optional_strs_to_none(data)
        input_args = StaConfig(**data)
        existing_args = StaConfig(current_config[module.params["configuring"]])
    else:
        data = shelly_utils.sanitize_dataclass_args(RoamConfig, module.params.copy())
        data = shelly_utils.optional_strs_to_none(data)
        input_args = RoamConfig(**data)
        existing_args = RoamConfig(current_config["roam"])

    if input_args != existing_args:
        result["changed"] = True

    if module.check_mode:
        if result["changed"]:
            # Most, if not all, changes to Wifi config require a restart.
            result["restart_required"] = True
        return module.exit_json(**result)

    if result["changed"]:
        new_config = current_config.copy()
        new_config[module.params["configuring"]] = asdict(input_args)

        set_result = connection.send_request(
            data={
                "method": "Wifi.SetConfig",
                "params": {
                    "config": new_config
                }
            }
        )

        result["restart_required"] = set_result["restart_required"]

        connection_available = shelly_utils.poll_for_connection(module.params["timeout"], connection)

        if not connection_available:
            module.fail_json(msg="Shelly device did not become available after reconfiguring Wifi interface.", **result)

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
