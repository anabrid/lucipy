#!/usr/bin/env python3

"""
This is a small interactive command line script for discovering/detecting LUCIDACs.
It will look for the Teensy Microcontroller (Hybrid Controller) both directly
connected over USB Serial Device as well as Network services announced by
MDNS/Zeroconf over the network (local IPv4 broadcast domain). The network lookup
happens typically within a few hundred milliseconds. If you want to wait for more
then one device, use the --all option.
"""

# all python included
import asyncio, logging, socket, sys, argparse, inspect, ast, pathlib, time, collections, itertools, urllib, re
from typing import Any, Optional, List, cast, Iterator

try:
    # pip install pyserial
    import serial, serial.tools.list_ports
except ModuleNotFoundError:
    serial = None

try:
    # pip install zeroconf
    # An OS-independent all-python zeroconf/bonjour client
    from zeroconf import IPVersion, ServiceStateChange, Zeroconf
    from zeroconf.asyncio import (
        AsyncServiceBrowser,
        AsyncServiceInfo,
        AsyncZeroconf,
        AsyncZeroconfServiceTypes,
    )
except ModuleNotFoundError:
    Zeroconf = None

verbosity = 0
err = lambda msg: print(msg, file=sys.stderr)
log = lambda level, msg: print(msg, file=sys.stderr) if verbosity >= level else None
v   = lambda msg: log(1, msg)
vv  = lambda msg: log(2, msg)


class Endpoint:
    """
    This class models the LUCIDAC/REDAC endpoint URI convention in lucipy.
    Given there is no proper URI object in python, we make use of
    ``urllib.urlparse``. This class is used for instance in
    :func:`lucipy.synchc.endpoint2socket`.

    Create instances either directly or via helpers which prepend
    the correct scheme:

    >>> Endpoint("tcp://123.123.123.123:7890")
    Endpoint("tcp://123.123.123.123:7890")
    >>> Endpoint.fromJSONL("localhost", 1234)
    Endpoint("tcp://localhost:1234")

    For serial devices, there is a little extra work done ontop of
    URL parsing, which makes the syntax less weird in contexts where
    URIs are typically not used. Serial devices just don't follow the
    double slash convention but more a kio/gfs single slash
    convention:

    >>> Endpoint("serial:/dev/ttyACM0") # device file at Linux/Mac
    Endpoint("serial:/dev/ttyACM0")
    >>> Endpoint.fromDevice("/dev/ttyACM0")
    Endpoint("serial:/dev/ttyACM0")
    >>> Endpoint("serial:/COM0")
    Endpoint("serial:/COM0")
    >>> Endpoint.fromDevice("COM0") # port name at Windows
    Endpoint("serial:/COM0")

    Endpoints with scheme only are fine and used in the code. Note that
    schemes are the only part of the URL which is always canonically
    lowercased:

    >>> Endpoint("EMU:")
    Endpoint("emu:")

    An example of an endpoint which uses all fields:

    >>> e = Endpoint("TCP://myuser:mypass@FOO.bar:4711?flitz=bums&baz=bla")
    >>> e.user
    'myuser'
    >>> e.args
    {'flitz': 'bums', 'baz': 'bla'}
    >>> e
    Endpoint("tcp://myuser:foo.bar:4711?flitz=bums&baz=bla")
    """
    default_tcp_port = 5732
    
    def __init__(self, endpoint):
        if isinstance(endpoint, Endpoint):
            endpoint = endpoint.url()
        if not isinstance(endpoint, str):
            raise ValueError("Expecting endpoint URL as string")
            
        result = urllib.parse.urlparse(endpoint)
        #result = re.match("(?P<scheme>[a-zA-Z0-9]+):(?P<sep>/?/?)(?P<userpass>[^@:]+(:[^@]+)?)...

        #: Scheme, such as "serial", "tcp", etc.
        self.scheme = result.scheme
        #: Username for login, if present. None is a valid value.
        self.user = result.username
        #: Password for login, if present. None is a valid value.
        self.password = result.password
        #: Host or device name. Note that hostnames are transfered to lowercase while
        #: pathnames will not.
        self.host = (result.hostname or "") + (result.path or "")
        #: TCP/IP Port as integer. If not given, defaults to default TCP port.
        self.port = int(result.port or self.default_tcp_port)
        #: Further query arguments from the URL
        self.args = urllib.parse.parse_qs(result.query, keep_blank_values=True)
        # improve for queries such as ?foo -> should result in foo=True
        #                             ?foo=bar -> should not result in foo=["bar"] but foo=bar
        for k in self.args.keys():
            if len(self.args[k]) == 0:
                self.args[k] = True
            if len(self.args[k]) == 1:
                self.args[k] = self.args[k][0] # unwrap

        # fixes for serial scheme, mainly neccessary because
        # result.hostname is lowercased, which is bad for "ttyACM0" or "COM0".
        # Will also fix problems such as serial://dev/foo resulting in host= "dev/foo"
        posix = re.match("serial:/?(/.+)", endpoint, re.IGNORECASE)
        win = re.match("serial:/?/(.+)", endpoint, re.IGNORECASE)
        if posix:
            self.host = posix.group(1)
        elif win:
            self.host = win.group(1)

        #if self.scheme == "serial" and "/" in self.host and self.host[0] != "/":
            # fix Unix absolute filenames: serial://dev/foo would result in host = "dev/foo"
            # however serial:/dev/foo gets correct "/dev/foo". This corrects the double slash version.
        #    self.host = "/" + self.host
        
        #if not self.scheme:
        #    raise ValueError(f"Invalid Endpoint '{endpoint}' is not a string-encoded URL.")

    @staticmethod
    def fromDevice(device_name):
        "Initialize for a device name"
        sep_host = "//"+device_name if device_name[0] != "/" else device_name
        return Endpoint(f"serial:{sep_host}")
    
    @staticmethod
    def fromJSONL(addr, port=None):
        "Initialize for a TCP addr/port address tuple"
        return Endpoint(f"tcp://{addr}" + (f":{port}" if port else ""))
    
    def url(self):
        s = self.scheme + ":"
        if self.host and self.host[0] != "/":
            s += "//"
        if self.user and not self.password:
            s += self.user + ":" + self.password + "@"
        elif self.user:
            s += self.user + ":"
        s += self.host
        # the way attaching the port to the host won't work for websockets
        # (think of Endpoint("http://foo.bar:80/bla.ws")) but we don't support them anyway.
        if self.port != self.default_tcp_port:
            s += ":" + str(self.port)
        if self.args:
            s += "?" + "&".join([f"{k}={v}" for k,v in self.args.items()])
        return s
    
    def __repr__(self):
        return 'Endpoint("' + self.url() +  '")'
    
    def __str__(self):
        return self.__repr__()

def can_resolve(hostname, target_ip:str=None) -> Optional[str]:
    "gethostbyname but without the exceptions, i.e. with a boolean representation of the return value"
    try:
        return socket.gethostbyname(hostname)
    except socket.error:
        return None

def can_resolve_to(hostname, expected_ip:str):
    "Checks whether the host system can resolve a given (zeroconf) DNS name"
    return can_resolve(hostname) == expected_ip

class ZeroconfDetector:
    def __init__(self, timeout_ms=500):
        # self.search_for = "lucidac-AA-BB-CC" # something which results in an abortion condition!
        if not Zeroconf:
            raise ModuleNotFoundError("Constructing a ZeroconfDetector object requires zeroconf, install with 'pip install zeroconf'")
        self.aiobrowser: Optional[AsyncServiceBrowser] = None
        self.aiozc: Optional[AsyncZeroconf] = None
        self.results: List[Endpoint] = []
        self.timeout_ns = timeout_ms*1000
        
    def on_service_state_change(self, zeroconf, service_type: str, name: str, state_change) -> None:
        # types are actually
        # zeroconf: Zeroconf, service_type: str, name: str, state_change: ServiceStateChange
        # but not using them for avoiding dependencies.
        vv(f"Service {name} of type {service_type} state changed: {state_change}")
        if state_change is not ServiceStateChange.Added:
            return
        asyncio.ensure_future(self._enqueue_service_info(zeroconf, service_type, name))
        
    async def _enqueue_service_info(self, zeroconf, service_type: str, name: str):
        info = AsyncServiceInfo(service_type, name)
        await info.async_request(zeroconf, 3000)
        vv("Zeroconf found: %r" % (info))
        if info:
            for addr in info.parsed_scoped_addresses():
                v(f"Found {info.server} resolving to {addr}; TCP Port {info.port}")
                # Use Hostname only if the system can resolve it (functional mDNS setup).
                # Most Windows, Mac OS and Linux systems can do it, some (in particular Linux) cannot.
                addr = info.server if can_resolve_to(info.server, expected_ip=addr) else addr
                endpoint = Endpoint.fromJSONL(addr, info.port)
                if self.timeout_ns == 0:
                    print(endpoint)
                else:
                    self.results.append(endpoint)
                    vv(self.results)

    async def start(self) -> None:
        "Starts Zeroconf browser detection. Returns after timeout."
        self.aiozc = aiozc = AsyncZeroconf(ip_version=IPVersion.V4Only)
    
        services = [ "_lucijsonl._tcp.local." ] # not even _http
        v("...Scanning local broadcast network for network, press Ctrl-C to exit..." % services)

        self.aiobrowser = AsyncServiceBrowser(
            self.aiozc.zeroconf, services, handlers=[self.on_service_state_change]
        )
        
        started = time.time_ns()
        while 0 == self.timeout_ns or (time.time_ns() - started) < self.timeout_ns: # or len(self.results) < 1:
            print("waiting...")
            await asyncio.sleep(.5)
        
        return self.results
        
    async def stop(self) -> None:
        "Stops Zeroconf browser detection"
        assert self.aiozc is not None
        assert self.aiobrowser is not None
        await self.aiobrowser.async_cancel()
        await self.aiozc.async_close()
          
    def sync_start(self):
        "merely a helper to trigger and endless run"
        
        #loop = asyncio.get_event_loop()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.start())
        except KeyboardInterrupt:
            loop.run_until_complete(self.stop())
            return self.results


def detect_usb_teensys() -> List[Endpoint]:
    "Yields all found endpoints on local system using serial.tools.list_ports, requires pyserial"
    teensy_vid = 0x16C0
    teensy_pid = 0x0483
    
    if not serial:
        raise ModuleNotFoundError("lucipy.detect.detect_usb_teensys for USB requires pyserial, install with 'pip install pyserial'")
    
    found = []
    for port in serial.tools.list_ports.comports(): 
        if port.pid == teensy_pid and port.vid == teensy_vid:
            v(f"Serial device at {port.device} - {port.hwid}") # sth like "USB VID:PID=16C0:0483 SER=15240110 LOCATION=1-3:1.0"
            found.append(Endpoint.fromDevice(port.device)) # sth like "/dev/ttyACM0" at Linux/Mac
            
    # TODO: Has to connect and make sure it is a Teensy belonging to a LUCIDAC
    #       and not to something else. i.e. make sure it speaks the JSONL protocol.
    
    return found

def detect_network_teensys(zeroconf_timeout=500) -> List[Endpoint]:
    "Yields all endpoints in the local broadcast domain using Zeroconf, requires python zeroconf package"
    if not Zeroconf:
        raise ModuleNotFoundError("lucipy.detect.detect_network_teensys requires zeroconf, install with 'pip install zeroconf'")
    
    return ZeroconfDetector(zeroconf_timeout).sync_start()

def detect(single=False, prefer_network=True, zeroconf_timeout=500):# -> Optional[Endpoint | List[Endpoint]]:
    """
    Yields or returns possible endpoints using all methods. This function will raise an ModuleNotFoundError
    if a library is not available which might have found more.

    :param single: Return only first found instance or None, if nothing found. If this
         option is False, this function will return an array of endpoints discovered using all methods.
    :param zeroconf_timeout: Maximum search time: How long to wait for zeroconf answers,
         in milliseconds. Set to 0 or None for unlimited search.
    :param prefer_network: Return network result first. Typically a TCP/IP connection is
         faster and more reliable then the USBSerial connection.
    """
    res = []
    singlize = lambda res: (res[0] if len(res) else None) if single else res
    if prefer_network:
        res += detect_network_teensys(zeroconf_timeout)
    if single and len(res):
        return singlize(res)
    if True:
        res += detect_usb_teensys()
    if single and len(res):
        return singlize(res)
    if not prefer_network:
        res += detect_network_teensys(zeroconf_timeout)
    return singlize(res)

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
    for res in detect(zeroconf_timeout=0 if args.all else 1000):
        print(res)
