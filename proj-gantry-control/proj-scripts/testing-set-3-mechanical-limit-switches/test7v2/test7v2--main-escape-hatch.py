# test7v2--main-escape-hatch.py  -- deploy as main.py on the ESP32.
# =============================================================================
# ESCAPE HATCH FIRST. This is v2 step 1: prove we can ALWAYS recover the board
# before any real listener logic (or kbd_intr) goes on it. v1 got bricked by a
# runaway main.py with the REPL disabled; this makes that impossible.
#
# HOW IT PROTECTS YOU (verified against MicroPython "Reset and Boot Sequence"):
#   * If main.py EXITS or crashes, MicroPython drops to the REPL -- as long as no
#     infinite loop traps it first. So we decide whether to enter the loop BEFORE
#     doing anything that could lock us out.
#   * SKIP FILE: if a file named 'SAFE' exists on flash, main.py prints and exits
#     immediately -> REPL. kbd_intr is never touched. Full control, always.
#   * BOOT DELAY: a few seconds before the loop, with normal Ctrl-C still working,
#     so mpremote/Ctrl-C can break in the ordinary way during that window.
#
# RECOVERY (no erase-flash needed):
#   Disable the listener ->   mpremote fs touch :SAFE   (then reset)   -> boots to REPL
#   Re-enable it        ->   mpremote fs rm :SAFE       (then reset)   -> runs the loop
#   Ultimate backstop   ->   BOOT+EN button -> bootloader -> esptool erase_flash
#
# This file has NO listener yet -- the loop is a harmless placeholder. Step 2 puts
# the real echo/listener code where marked, once the hatch is proven.
# =============================================================================

import time
import sys

SAFE_FILE = "SAFE"

def safe_file_present():
    try:
        import os
        return SAFE_FILE in os.listdir()
    except Exception:
        return False

# 1) SKIP CHECK -- exit to REPL if the SAFE file exists.
if safe_file_present():
    print("SAFE file present -> skipping listener, dropping to REPL.")
    sys.exit()                      # main.py exits -> MicroPython drops to REPL

# 2) BOOT DELAY -- a window to break in normally (Ctrl-C / mpremote) before the loop.
print("main starting in 3s... (create SAFE file or Ctrl-C now to stay at REPL)")
for i in range(3, 0, -1):
    print("  {}...".format(i))
    time.sleep(1)

# 3) THE LOOP -- placeholder only. Ctrl-C still works here (kbd_intr NOT disabled).
#    Step 2 replaces this block with the real listener behind the same hatch.
print("PLACEHOLDER LOOP running (no listener yet). Ctrl-C to stop -> REPL.")
try:
    while True:
        print("  ...alive")
        time.sleep(2)
except KeyboardInterrupt:
    print("stopped -> REPL.")