#!/usr/bin/python

DOCUMENTATION = '''
---
module: script
short_description: A module for managing the scripts of a Shelly gen 2+ device.
version_added: "0.0.1"
description:
  - A module for managing the scripts of a Shelly gen 2+ device.
  - Scripts can be updated, created, deleted.
  - The script name is used as a unique identifier from the ansible perspective.
options:
    name:
        description:
          - The unique name of the script.
        required: true
        type: str
    state:
        description:
          - Controls the state of the script.
          - Must be one of the following:
          - "deleted" - ensures that no script with the given name is present on the device.
          - "present" - will upload the script but not start it.
          - "running" - will upload the script and ensure that it is started.
          -
          - "present" and "running" will update the script content if it has changed.
    enable:
        description:
          - Set to true for the script to run at device boot.
          - Required if state is set to "running" or "present".
        required: false
        type: bool
    script_path:
        description:
          - The path to the script file from which to get the script code.
          - Required if state is set to "running" or "present".
        required: false
        type: path
author:
    - RustedSkull (@skull132)
'''

EXAMPLES = '''
- name: Delete script called "abc".
  enclave.shelly.script:
    name: abc
    state: deleted

- name: Upload test script
    enclave.shelly.script:
    name: test1
    state: present
    enable: false
    script_path: files/test_script.js

- name: Update and start test script
    enclave.shelly.script:
    name: test1
    state: running
    enable: false
    script_path: files/test_script.js
'''

RETURN = '''
restart_required:
  description: Set to true if Shelly device should be restarted for the changes to take full effect.
  type: bool
  returned: always
'''

import hashlib

from dataclasses import dataclass
from typing import Optional

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.facts.compat import ansible_facts
from ansible.module_utils.connection import Connection

@dataclass
class ScriptState:
    id: int
    name: str
    enable: bool
    running: bool

def get_script_state(name: str, connection: Connection) -> Optional[ScriptState]:
    script_list = connection.send_request(
        data={"method": "Script.List"}
    )

    scripts = []
    for script_obj in script_list["scripts"]:
        if script_obj["name"] == name:
            return ScriptState(**script_obj)

    return None

def create_script(name: str, connection: Connection) -> ScriptState:
    _ = connection.send_request(
        data={
            "method": "Script.Create",
            "params": {
                "name": name
            }
        }
    )

    return get_script_state(name, connection)

def delete_script(script_state: ScriptState, connection: Connection) -> None:
    _ = connection.send_request(
        data={
            "method": "Script.Delete",
            "params": {
                "id": script_state.id
            }
        }
    )

def get_current_script(script_state: ScriptState, connection: Connection) -> Optional[str]:
    to_read = 256
    offset = 0
    remaining = to_read

    request_data = {
        "id": script_state.id,
        "offset": offset,
        "len": to_read
    }

    code = ""
    while offset < remaining:
        response = connection.send_request(
            data={
                "method": "Script.GetCode",
                "params": request_data
            }
        )

        offset += to_read
        remaining = response["left"]

        code += response["data"]

    if len(code) == 0:
        return None
    else:
        return code
    
def get_new_code(path_str: str) -> str:
    with open(path_str, "r") as file:
        content = file.read()

    return content

def update_script_code(code: str, script_state: ScriptState, connection: Connection) -> None:
    if script_state.running:
        _ = connection.send_request(
            data={
                "method": "Script.Stop",
                "params": {"id": script_state.id}
            }
        )

    to_put = 256
    offset = 0

    request_data = {
        "id": script_state.id,
        "append": False,
    }

    while offset < len(code):
        request_data["code"] = code[offset:(offset + to_put)]

        _ = connection.send_request(
            data={
                "method": "Script.PutCode",
                "params": request_data
            }
        )

        offset += to_put
        request_data["append"] = True

def start_script(script_state: ScriptState, connection: Connection) -> None:
    _ = connection.send_request(
        data={
            "method": "Script.Start",
            "params": {"id": script_state.id}
        }
    )

def stop_script(script_state: ScriptState, connection: Connection) -> None:
    _ = connection.send_request(
        data={
            "method": "Script.Stop",
            "params": {"id": script_state.id}
        }
    )

def set_script_enable(script_state: ScriptState, enable: bool, connection: Connection) -> bool:
    result = connection.send_request(
        data={
            "method": "Script.SetConfig",
            "params": {
                "id": script_state.id,
                "config": {
                    "enable": enable
                }
            }
        }
    )

    return result["restart_required"]

def run_module():
    module_args = dict(
        name=dict(type="str", required=True),
        state=dict(type="str", required=True, choices=["running", "present", "deleted"]),
        enable=dict(type="bool", required=False),
        script_path=dict(type="path", required=False)
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
        required_if=[
            ("state", "running", ("enable", "script_path")),
            ("state", "present", ("enable", "script_path"))
        ]
    )

    result = dict(
        changed=False,
        restart_required=False
    )

    changed = False

    connection = Connection(module._socket_path)
    current_script_state = get_script_state(module.params["name"], connection)

    if module.params["state"] in ["running", "present"]:
        if current_script_state is None:
            if not module.check_mode:
                current_script_state = create_script(module.params["name"], connection)
            else:
                result["changed"] = True
                return module.exit_json(**result)
            changed = True
    else:
        if current_script_state is not None:
            if not module.check_mode:
                delete_script(current_script_state, connection)
                current_script_state = None
            changed = True

        result["changed"] = changed
        return module.exit_json(**result)
    
    current_code = get_current_script(current_script_state, connection)
    new_code = get_new_code(module.params["script_path"])

    if current_code is None or current_code != new_code:
        changed = True
        if not module.check_mode:
            update_script_code(new_code, current_script_state, connection)
            # Updating code will stop the script.
            current_script_state.running = False

    if module.params["state"] == "running" and current_script_state.running == False:
        changed = True
        if not module.check_mode:
            start_script(current_script_state, connection)
    elif module.params["state"] == "present" and current_script_state.running == True:
        changed = True
        if not module.check_mode:
            stop_script(current_script_state, connection)

    if module.params["enable"] != current_script_state.enable:
        changed = True
        if not module.check_mode:
            result["restart_required"] = set_script_enable(current_script_state, module.params["enable"], connection)

    result["changed"] = changed
    if current_script_state is not None:
        result["script_id"] = current_script_state.id
    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
