#!/usr/bin/env python

#
# This is a small demonstrator script checking the firmware version on a LUCIDAC
# against the anabrid github releases.
#

from lucipy import LUCIDAC
import re, json
import urllib.request

hc = LUCIDAC()

print(f"Checking installed version at device {hc}...")
ident = hc.sys_ident()

try:
    cur_version = ident["fw_build"]["FIRMWARE_VERSION"]
    # re.match("^v(?<major>\d+).(?<minor>\d+).(?<patch>\d+)")
except KeyError:
    cur_version = None

check_updates_url = "https://api.github.com/repos/anabrid/lucidac-firmware/releases"

print(f"Checking most recent version at {check_updates_url}...")
with urllib.request.urlopen(check_updates_url) as url_json_body:
    releases = json.load(url_json_body)

unstable_branch = False
if not unstable_branch:
    releases = list(filter(lambda release: not release["draft"] and not release["prerelease"], releases))

most_recent_release = releases[0]

newest_version = most_recent_release["tag_name"]

# string value comparision is not bad, since the following holds:
assert "v1.1" > "v1.0"
assert "v1.2" > "v1.1-bla"
assert "v1.1-bla" > "v1.1"

update_available = newest_version > cur_version

message = "Firmware upate available!" if update_available else "Most recent firwmare already installed"

print(f"========= {message} ==========")
print(f"Currently installed:  {cur_version}")
print(f"Latest available:     {newest_version}")

force_update = True

if not update_available and force_update:
    print("Forcing update...")

#if update_available or force_update:
    
# firmware.bin for the OTA updater
asset_fname = "firmware.bin"

asset_candidates = list(filter(lambda asset: asset["name"]==asset_fname, most_recent_release["assets"]))

if len(asset_candidates) != 1:
    print(f"Cannot proceed because I cannot find the {asset_fname} file in the release assets")

asset = asset_candidates[0]

asset_size_kB = int(asset["size"] / 1024)
asset_url = asset["browser_download_url"]

print(f"Download URL: {asset_url}")
print(f"Downloading {asset_fname} ({asset_size_kB} kB) to hard drive...")

urllib.request.urlretrieve(asset_url, asset_fname)
