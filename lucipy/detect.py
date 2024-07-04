#!/usr/bin/env python3

"""
This is a small interactive command line script for discovering/detecting LUCIDACs.
It will look for the Teensy Microcontroller (Hybrid Controller) both directly
connected over USB Serial Device as well as Network services announced by
MDNS/Zeroconf over the network (local IPv4 broadcast domain). The network lookup
happens typically within a few hundred milliseconds. If you want to wait for more
then one device, use the --all option.
"""

import asyncio, logging, socket, sys, argparse, inspect, ast, pathlib
from typing import Any, Optional, List, cast
from dataclasses import dataclass

# pip install pyserial
import serial, serial.tools.list_ports

# pip install zeroconf
# An OS-independent all-python zeroconf/bonjour client
from zeroconf import IPVersion, ServiceStateChange, Zeroconf
from zeroconf.asyncio import (
    AsyncServiceBrowser,
    AsyncServiceInfo,
    AsyncZeroconf,
    AsyncZeroconfServiceTypes,
)

verbosity = 0
err = lambda msg: print(msg, file=sys.stderr)
log = lambda level, msg: print(msg, file=sys.stderr) if verbosity >= level else None
v   = lambda msg: log(1, msg)
vv  = lambda msg: log(2, msg)

def can_resolve(hostname, target_ip:str=None) -> Optional[str]:
    "gethostbyname but without the exceptions, i.e. with a boolean representation of the return value"
    try:
        return socket.gethostbyname(hostname)
    except socket.error:
        return None

def can_resolve_to(hostname, expected_ip:str):
    return can_resolve(hostname) == expected_ip

@dataclass
class LucidacEndpoint: # actually an URI
    scheme: str # transport method, such as http, tcp, etc.
    authority: str # netloc, such as "lucidac-AA-BB-CC", "foobar" or "192.168.1.2", including ":port" at end
    #path: Optional[str] # also collects params, query, fragment
    
    def __str__(self):  # doesnt work...
        return f"{self.scheme}:/{self.authority}"

class ZeroconfDetector:
    def __init__(self, infinite=False):
        # self.search_for = "lucidac-AA-BB-CC" # something which results in an abortion condition!
        self.aiobrowser: Optional[AsyncServiceBrowser] = None
        self.aiozc: Optional[AsyncZeroconf] = None
        self.results: List[LucidacEndpoint] = []
        self.infinite = infinite
        
    def on_service_state_change(self,
        zeroconf: Zeroconf, service_type: str, name: str, state_change: ServiceStateChange
    ) -> None:
        vv(f"Service {name} of type {service_type} state changed: {state_change}")
        if state_change is not ServiceStateChange.Added:
            return
        asyncio.ensure_future(self._enqueue_service_info(zeroconf, service_type, name))
        
    async def _enqueue_service_info(self, zeroconf: Zeroconf, service_type: str, name: str):
        info = AsyncServiceInfo(service_type, name)
        await info.async_request(zeroconf, 3000)
        vv("Zeroconf found: %r" % (info))
        if info:
            for addr in info.parsed_scoped_addresses():
                v(f"Found {info.server} resolving to {addr}; TCP Port {info.port}")
                # Use Hostname only if the system can resolve it (functional mDNS setup).
                # Most Windows, Mac OS and Linux systems can do it, some (in particular Linux) cannot.
                addr = info.server if can_resolve_to(info.server, expected_ip=addr) else addr
                netloc = f"{addr}:{info.port}"
                endpoint = LucidacEndpoint("tcp", netloc)
                if self.infinite:
                    print(endpoint)
                else:
                    self.results.append(endpoint)
                    vv(self.results)

    async def start(self) -> None:
        self.aiozc = aiozc = AsyncZeroconf(ip_version=IPVersion.V4Only)
    
        services = [ "_lucijsonl._tcp.local." ] # not even _http
        v("...Scanning local broadcast network for network, press Ctrl-C to exit..." % services)

        self.aiobrowser = AsyncServiceBrowser(
            self.aiozc.zeroconf, services, handlers=[self.on_service_state_change]
        )
        
        #await asyncio.sleep(1)
        while self.infinite or len(self.results) < 1:
            await asyncio.sleep(.2)
        
        return self.results
        
    async def stop(self) -> None:
        assert self.aiozc is not None
        assert self.aiobrowser is not None
        await self.aiobrowser.async_cancel()
        await self.aiozc.async_close()
          
    def sync_start(self, infinite=False):
        "merely a helper to trigger and endless run"
        
        #loop = asyncio.get_event_loop()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.start())
        except KeyboardInterrupt:
            loop.run_until_complete(self.stop())
            return self.results


def filter_usb_teensys():
    teensy_vid = 0x16C0
    teensy_pid = 0x0483
    
    for port in serial.tools.list_ports.comports(): 
        if port.pid == teensy_pid and port.vid == teensy_vid:
            v(f"Serial device at {port.device} - {port.hwid}") # sth like "USB VID:PID=16C0:0483 SER=15240110 LOCATION=1-3:1.0"
            yield LucidacEndpoint("serial", port.device) # sth like "/dev/ttyACM0" at Linux/Mac
            
    # TODO: Has to connect and make sure it is a Teensy belonging to a LUCIDAC
    #       and not to something else. i.e. make sure it speaks the JSONL protocol.
  
def detect(unlimited=True):
    for x in filter_usb_teensys():
        print(x)
    z = ZeroconfDetector(unlimited)
    for x in z.sync_start():
        print(x)

if __name__ == '__main__':
    #logging.basicConfig(level=logging.INFO)
    file_docstring = ast.get_docstring(ast.parse(pathlib.Path(__file__).read_text()), clean=True)    
    parser = argparse.ArgumentParser(description="Scanner to discover locally or network-attached LUCIDAC analog/digital hybrid computers.",
        epilog = file_docstring,
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-v', '--verbose', action='count', default=0, help="Verbosity, add more -v for more verbose output")
    parser.add_argument('-a', '--all', action='store_true', help='Scan unlimited, try to find more then one device in the network (stop with CTRL-C)')
    args = parser.parse_args()
    verbosity = args.verbose
    detect(args.all)
