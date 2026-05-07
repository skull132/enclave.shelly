#!/usr/bin/python

DOCUMENTATION = '''
---
module: schedule
short_description: Manage scheduled jobs on a Shelly gen 2+ device.
version_added: "0.0.1"
description:
  - Create or delete scheduled jobs on a Shelly gen 2+ device.
  - Matches existing jobs by timespec + method + params combination for idempotency.
options:
    timespec:
        description:
          - 6-field cron expression (seconds minute hour dom month dow).
          - Required when state is present.
        required: false
        type: str
    method:
        description:
          - RPC method to call on schedule (e.g. "Script.Start").
          - Required when state is present.
        required: false
        type: str
    params:
        description:
          - Parameters to pass to the RPC method.
        required: false
        type: dict
        default: {}
    enable:
        description:
          - Whether the schedule is enabled.
        required: false
        type: bool
        default: true
    state:
        description:
          - present - create schedule if not already matching.
          - absent - delete all matching schedules.
        required: true
        type: str
        choices: ["present", "absent"]
author:
    - Alastair McFarlane
'''

EXAMPLES = '''
- name: Run fallback script every 30 seconds
  enclave.shelly.schedule:
    timespec: "0,30 * * * * *"
    method: Script.Start
    params:
      id: 2
    enable: true
    state: present
'''

RETURN = '''
schedule_id:
  description: ID of the created or matched schedule.
  type: int
  returned: when state is present
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.connection import Connection


def jobs_match(job, timespec, method, params):
    if job.get("timespec") != timespec:
        return False
    calls = job.get("calls", [])
    if not calls:
        return False
    call = calls[0]
    return call.get("method") == method and call.get("params", {}) == params


def run_module():
    module_args = dict(
        timespec=dict(type="str", required=False),
        method=dict(type="str", required=False),
        params=dict(type="dict", required=False, default={}),
        enable=dict(type="bool", required=False, default=True),
        state=dict(type="str", required=True, choices=["present", "absent"]),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
        required_if=[
            ("state", "present", ("timespec", "method")),
        ]
    )

    result = dict(changed=False)
    connection = Connection(module._socket_path)

    existing = connection.send_request(data={"method": "Schedule.List"})
    jobs = existing.get("jobs", [])

    timespec = module.params["timespec"]
    method = module.params["method"]
    params = module.params["params"]
    enable = module.params["enable"]
    state = module.params["state"]

    matching = [j for j in jobs if jobs_match(j, timespec, method, params)]

    if state == "absent":
        if not matching:
            module.exit_json(**result)
        if not module.check_mode:
            for job in matching:
                connection.send_request(data={"method": "Schedule.Delete", "params": {"id": job["id"]}})
        result["changed"] = True
        module.exit_json(**result)

    # state == present
    if matching:
        result["schedule_id"] = matching[0]["id"]
        module.exit_json(**result)

    if not module.check_mode:
        created = connection.send_request(data={
            "method": "Schedule.Create",
            "params": {
                "timespec": timespec,
                "enable": enable,
                "calls": [{"method": method, "params": params}],
            }
        })
        result["schedule_id"] = created.get("id")

    result["changed"] = True
    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
