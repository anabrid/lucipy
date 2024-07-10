# Lucipy: The simple LUCIDAC python client

Installation: `pip install lucipy` or just clone the repository (which is just online
at https://github.com/anabrid/lucipy) and import the `lucipy` directory.

This is a minimal python client, making simple things simple. That means things
like device managament is capable of the python REPL without headache:

```
shell> python
> from simplehc import HybridController
> hc = HybridController("192.168.68.60", 5732)
INFO:simplehc:Connecting to TCP 192.168.68.60:5732...
> hc.query("status")
{'dist': {'OEM': 'anabrid',
  'OEM_MODEL_NAME': 'LUCIDAC',
  'OEM_HARDWARE_REVISION': 'LUCIDAC-v1.2.3',
  'BUILD_SYSTEM_NAME': 'pio',
  'BUILD_SYSTEM_BOARD': 'teensy41',
  'BUILD_SYSTEM_BOARD_MCU': 'imxrt1062',
  'BUILD_SYSTEM_BOARD_F_CPU': '600000000',
  'BUILD_SYSTEM_BUILD_TYPE': 'release',
  'BUILD_SYSTEM_UPLOAD_PROTOCOL': 'teensy-cli',
  'BUILD_FLAGS': '-DANABRID_DEBUG_INIT -DANABRID_UNSAFE_INTERNET -DANABRID_ENABLE_GLOBAL_PLUGIN_LOADER',
  'DEVICE_SERIAL_NUMBER': '123',
  'SENSITIVE_FIELDS': 'DEVICE_SERIAL_UUID DEVICE_SERIAL_REGISTRATION_LINK DEFAULT_ADMIN_PASSWORD',
  'FIRMWARE_VERSION': '0.0.0+g0d3e361',
  'FIRMWARE_DATE': 'unavailable',
  'PROTOCOL_VERSION': '0.0.1',
  'PROTOCOL_DATE': 'unavailable'},
 'flashimage': {'size': 316416,
  'sha256sum': 'cd2f35648aba6a95dc1b32f88a0e3bf36346a5dc1977acbe6edbd2cdf42432d3'},
 'auth': {'enabled': False, 'users': []},
 'ethernet': {'interfaceStatus': True,
  'mac': '04-E9-E5-0D-CB-93',
  'ip': {'local': [192, 168, 68, 60],
   'broadcast': [192, 168, 68, 255],
   'gateway': [192, 168, 68, 1]},
  'dhcp': {'active': True, 'enabled': True},
  'link': {'state': True,
   'speed': 100,
   'isCrossover': True,
   'isFullDuplex': True}}}
> 
```

The code was formerly known as "Synchronous Hybrid Controller Python Client for REDAC/LUCIDAC"
(shcpy). It differs from the [pybrid-computing](https://pypi.org/project/pybrid-computing/)
code as it is much simpler:

* near to no dependencies
* no async
* no typing
* not a framework

In contrast, lucipy ships

* a simple usable hybrid controller class
* a bit of syntactic sugar for route-based analog circuit programming
* Routines for device autodiscovery with zeroconf and USB Serial detection

This makes lucipy ideally suited to be used interactively in IPython and Jupyter Notebooks.

Lucipy is 20 times smaller then pybrid (4 files instead of 80,
800SLOC instead of 16,000).

The repo also contains an Over-The-Air demo updater client.