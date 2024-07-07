#!/usr/bin/env python3

from lucipy import LUCIDAC
from pprint import pprint

luci = LUCIDAC("tcp://192.168.68.116:5732")

test_settings = {
    "net": {
#        "static_gw": "123.123.123.123"
#        "webserver_port": "123",
        "hostname": None,
    },
    "auth": {
#        "enable_whitelist": None
    }
}

test_settings["no_write"] = True

res = luci.query("net_set", test_settings)

print("Query:")
pprint(test_settings)
print("Response:")
pprint(res)
