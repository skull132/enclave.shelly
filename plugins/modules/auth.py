#!/usr/bin/python

DOCUMENTATION = '''
---
module: auth
short_description: A module for configuring the API authentication of a Shelly gen 2+ device.
version_added: "0.0.1"
description:
  - A module for configuring the API authentication of a Shelly gen 2+ device.
  - If this module is used to enable authentication, then all subsequent module calls need to provide the same password
  - via the ansible_httpapi_password variable on a host.
options:
    enable:
        description:
          - Set to true to enable authentication, false to disable.
        required: true
        type: bool
    password:
        description:
          - The password to use for the device.
          - Required if enable is set to true.
        required: false
        type: str
author:
    - RustedSkull (@skull132)
'''

EXAMPLES = '''
# Enable authentication, set the password to "abc"
- name: Enable auth.
  enclave.shelly.auth:
    enable: true
    password: abc

# Disable authentication.
- name: Disable auth.
  enclave.shelly.auth:
    enable: false
'''

RETURN = '''
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.facts.compat import ansible_facts
from ansible.module_utils.connection import Connection

def run_module():
    module_args = dict(
        enable=dict(type="bool", required=True),
        password=dict(type="str", required=False, no_log=True)
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
        required_if=[
            ("enable", True, ("password",), False)
        ]
    )

    result = dict(
        changed=True
    )

    connection = Connection(module._socket_path)

    device_info = connection.send_request(
        data={
            "method": "Shelly.GetDeviceInfo"
        }
    )

    realm = device_info["id"]

    if module.params["enable"]:
        ha1 = connection.ha1(realm, module.params["password"])
    else:
        ha1 = None

    _ = connection.send_request(
        data={
            "method": "Shelly.SetAuth",
            "params": {
                "user": "admin",
                "realm": realm,
                "ha1": ha1
            }
        }
    )

    if module.check_mode:
        return module.exit_json(**result)

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
