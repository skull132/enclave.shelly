# Ansible Collection - enclave.shelly

A collection for managing Shelly gen 2+ home automation devices via ansible.

The goal of the collection is to enable the management of a fleet of Shelly devices
from a single point of truth.

The module works by invoking the JSON-RPCv2 API that Shelly devices expose over HTTP.
The module supports the authentication scheme which Shelly devices use for this method of
communication.

Current features include:
* Basic device management (restarting remotely).
* Managing the device API password.
* MQTT settings management.
* WiFi settings mangement.
* Script management.

A lot of the modules accept inputs which transparently modify the settings exposed via API.
As such, if the module's own documentation is lacking, please refer to [Shelly's own API documentation](https://shelly-api-docs.shelly.cloud/gen2/ComponentsAndServices/Introduction).

## Installing the Collection

The collection can be installed using ansible-galaxy:
`ansible-galaxy collection install git+https://github.com/skull132/enclave.shelly.git,main`

## Configuring Hosts

Each device should be added as an individual host in your inventory.
The minimum configuration required is as follows:

```yaml
shelly:
  hosts:
    some_shelly_device: # host's name
      # Set the device to use the httpapi connection ansible provides, and tell
      # that plugin to use the enclave.shelly.shelly_api network OS.
      ansible_connection: "httpapi"
      ansible_network_os: "enclave.shelly.shelly_api"

      # Set the host to the IP/DNS name of the shelly device.
      ansible_host: "10.0.0.123"
      # Port must be 80.
      ansible_port: "80"
      # No SSL, this must be set to false.
      ansible_httpapi_use_ssl: false

      # If you have enabled or plan to enable API authentication, then
      # ansible_httpapi_password is the way by which you pass the password
      # to the connection.
      #ansible_httpapi_password: some_secret_here.

      # Not setting these will require you to set gather_facts: false in the playbook.
      ansible_facts_modules:
        - setup
        - enclave.shelly.shelly_api_facts
```

## Samples:

Device control:
```yaml
# Restart the shelly device. Wait 2 seconds for it to become available again.
- name: Restart Shelly
  enclave.shelly.device:
    state: restarted
    timeout: 2000
```

Controlling the authentication parameters:
```yaml
# Enable authentication, set the password to "abc"
- name: Enable auth.
  enclave.shelly.auth:
    enable: true
    password: abc

# Disable authentication.
- name: Disable auth.
  enclave.shelly.auth:
    enable: false
```

MQTT connection setup:
```yaml
# Disable MQTT on the device.
- name: Disable MQTT
  enclave.shelly.mqtt:
    enable: false

# Configure an MQTT server connection.
- name: Enable MQTT
  enclave.shelly.mqtt:
    enable: true
    server: mqtt_server.lan:8883
    client_id: "" # Use the shelly's own device_id
    user: "" # no username required
    ssl_ca: "*" # Accept any serverside SSL certificate.
    topic_prefix: "home/v1/room/device_1"
```

WiFi connection examples:
```yaml
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
```

Script management:
```yaml
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
```
