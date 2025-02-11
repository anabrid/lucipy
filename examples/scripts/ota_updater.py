#!/usr/bin/env python3

from lucipy import LUCIDAC as HybridController

import logging, sys, pathlib, subprocess, hashlib, datetime, time, base64
log = logging.getLogger('hcota')
now = datetime.datetime.now().isoformat()

try:
    from tqdm import tqdm
    progressbar = tqdm
except ModuleNotFoundError:
    # https://stackoverflow.com/a/34482761
    def progressbar(it, total=None, prefix="", size=60, out=sys.stdout): # Python3.6+
        if not total: total = len(it)
        start = time.time()
        def show(j):
            x = int(size*j/total)
            remaining = ((time.time() - start) / j) * (total - j)
            
            mins, sec = divmod(remaining, 60)
            time_str = f"{int(mins):02}:{sec:05.2f}"
            
            print(f"{prefix}[{u'█'*x}{('.'*(size-x))}] {j}/{total} Est wait {time_str}", end='\r', file=out, flush=True)
            
        for i, item in enumerate(it):
            yield item
            show(i+1)
        print("\n", flush=True, file=out)

hc = HybridController() # expect the LUCIDAC_ENDPOINT env variable
reset_running_upgrades = True

builddir = pathlib.Path("/home/koeppel/hybrid-controller/.pio/build/teensy41")
elffile = builddir / "firmware.elf"
binfile = builddir / "firmware.bin"
log.info(f"Converting {elffile.name} ({elffile.stat().st_size} bytes) to {binfile.name}")
subprocess.run(["objcopy", "--input-target=ihex", "--output-target=binary", elffile, binfile ])

binimage = binfile.read_bytes()
binimage_size = len(binimage)
log.info(f"Preparing image {binfile.name} ({binimage_size} bytes) for upload...")

binimage_hash = hashlib.sha256(binimage).hexdigest()

cur_image = hc.query("sys_ident").fw_image
log.info(f"Current old image at {hc} has {cur_image.size} bytes")
log.info(f"Old Image Sha256 = {cur_image.sha256sum}")
log.info(f"New Image Sha256 = {binimage_hash}")

ota_status = hc.query("ota_update_status")
if ota_status.is_upgrade_running:
    if reset_running_upgrades:
        hc.query('ota_update_abort')
    else:
        log.error(f"Upgrade already running at {hc}. Pass reset_running_upgrades=True to continue anyway.")
        sys.exit(2)

if ota_status.buffer_size and ota_status.buffer_size < binimage_size:
    log.error(f"Available buffer {ota_status.ota_upgrade_buffer_size=} to small (require {binimage_size=}).")
    # requires some multistep method
    sys.exit(3)

log.info(f"Using flash buffer at 0x%0X size 0x%0X" % (ota_status.buffer_addr, ota_status.buffer_size))

instructions = hc.query('ota_update_init', dict(
    name = binfile.name + now,
    imagelen = binimage_size,
    upstream_hash = binimage_hash
))

if instructions.encoding != "binary-base64":
    log.error(f"Can only write base64 binary objects, but required are {instructions=}")

bin_chunk_size = instructions.bin_chunk_size
num_transfers = int(binimage_size / bin_chunk_size) + 1

def divide_chunks(l, n): 
    "Yield successive n-sized chunks from l. "
    for i in range(0, len(l), n):
        yield l[i:i + n] 

log.info(f"Uploading firmware in {num_transfers} lines with {bin_chunk_size} bytes each.")

## Critical section: It is important not to interrupt this loop.
##   If it is done, hc.query("ota_update_abort") shall be called.

try:
    for chunk in progressbar(divide_chunks(binimage, bin_chunk_size), total=num_transfers):
        payload = base64.b64encode(chunk).decode()
        #log.info(f"Sending {payload=} bytes of base64 payload...")
        hc.query('ota_update_stream', dict(payload=payload))
except (KeyboardInterrupt,Exception) as e:
    log.error(e)
    log.warning("Aborting update")
    hc.query("ota_update_abort")
    sys.exit(4)

ota_status = hc.query("ota_update_status")
if not ota_status.is_upgrade_running or not ota_status.transfer_completed:
    log.error(f"Have nothing more to send but remote site is not happy: {ota_status=}")
    sys.exit(3)
if not ota_status.hash_correct:
    log.error(f"Finished upload but got corrupted data: Sha256 Hash is {ota_status.actual_hash} but should be {ota_status.upstream_hash}. Cannot proceed.")
    hc.query("ota_update_abort")
    sys.exit(5)

log.info("Finished uploading. Rebooting the teensy...")
hc.send("ota_update_complete")

# Don't expect an answer and assume the socket to die.
hc.sock.close()
del hc

# instead, ping and wait for teensy to come back...
