# deepseek generated


# Template.py
#
# Skeleton for adding support for a new architecture / chip to PyroFlash.
#
# How to use:
#   1. Copy this file to <Arch>_flash.py
#   2. Rename the class if you like (a short alias at the bottom is customary).
#   3. Fill in the TODOs.
#   4. Import and use:  from PyroFlash import <Arch>
#
# The BaseFlasher machinery (verify, slice, pad, vcw (Verify Clear Write), read_memory, flash ...)
# works on top of the three primitives implemented here:  RM, WM, CM.
#
# Contract of the primitives (keep it simple, this is what makes porting easy):
#
#   RM(addr, sz)      -> read sz bytes starting at addr.
#                        Should NOT split, chunk or verify anything.
#                        One bus transaction / one page read.
#
#   WM(addr, data)    -> write a single block (one page / one bus request).
#                        Do not loop over pages here.
#
#   CM(addr=None)     -> clear (erase) one page/sector at addr,
#                        or the whole chip if addr is None.
#                        One erase operation, no looping.
#
# The BaseFlasher loop will call RM/WM/CM page by page for you.
#
# vcw - Verify Clear Write - the main flashing path.
#   The core of BaseFlasher is the vcw() / vcw_memory() loop, which for
#   every page does:
#       1. read back the page              (via RM)
#       2. compare it with the data to be written (verify_memory)
#          - if identical           -> skip, print "same"
#          - if page is fully erased-> proceed to write
#          - if page is not erased  -> CM (erase) if allowed, else raise
#       3. write the page                  (via WM)
#   So flashing is not a blind write: pages that already contain the right
#   bytes are left untouched, and pages that are only partially programmed
#   are erased first (when autoclear is True and CM is available).
#   This is why RM, WM and CM must each be a single primitive - vcw
#   combines them page by page.
#
# Optimisation note for WM:
#   It is RECOMMENDED (but not required) to start WM with:
#       if super().WM(addr, data):
#           return
#   super().WM() skips the write when the target block is already erased,
#   which speeds up re-flashing significantly.  A plain WM without this
#   check works correctly, it just writes every block unconditionally.
#
# autoclear:
#   True  (default) - Use this for chips that require erase-before-write (STM32,
#                     W25Q, ...).
#   False           - the chip erases the page automatically as part of the
#                     write sequence (e.g. STM8 block write). No pre-erase,
#
# erased_value:
#   0xff for most parallel/SPI NOR flashes.
#   0x00 for STM8.
#
# tsz vs psz:
#   tsz = transport block size (max bytes one bus request can carry).
#   psz = programming page/sector size.
#   read_memory()/write_memory() slice over these for you.
#
# getPage():
#   For chips with mixed page sizes (e.g. STM32F411)
#
# Protection commands (optional, STM32-like naming):
#   WP(page)  - Write Protect   : enable write protection for a page/sector.
#   WU(page)  - Write Unprotect : disable write protection (whole chip or page).
#   RP(page)  - Read  Protect   : enable readout protection (usually whole chip).
#   RU(page)  - Read  Unprotect : disable readout protection (usually whole chip).
#   These are user-facing helpers; the core flasher never calls them
#   automatically.  Implement only the ones your chip actually supports.
#   Readout protection often triggers a full chip erase on the target when
#   disabled - warn the user in the docstring.


from PyroFlash.Core.BaseFlasher import *


class Flasher (BaseFlasher):

    # --- Platform parameters -------------------------------------------------
    # Sizes are in bytes unless noted otherwise.

    tsz = 256              # transport block size (one bus request)
    psz = 256              # programming page / sector size

    wdelay = 100           # delay after a write/erase, ms

    addr = 0x0000_0000     # base address of the flash in this memory space

    erased_value = 0xff    # byte value of an erased cell (0x00 for STM8)

    pad_block = False      # pad the last (short) block to page size with erased_value

    autoclear = True       # True: require pre-erased page (raise otherwise)
                           # False: chip erases on write (STM8-like)

    id = None              # chip id, filled in start()

    pages = None           # dict {id: [page_size_kb, ...]} for mixed-page chips
                           # or None for uniform psz


    # --- Init ----------------------------------------------------------------
    def __init__(self, comm, *args, **kwargs):
        """
        comm is whatever the platform driver needs:
          - int  (UART/SPI bus number)  -> wrap into machine.UART / machine.SPI
          - an already opened bus object
          - a custom driver object
        Store it on self, then call super().__init__().
        super() will call self.start() and self.print_flash_size().
        """

        # Example: wrap a plain UART number.
        # if type(comm) is int:
        #     from machine import UART
        #     comm = UART(comm)
        # self.comm = comm
        # self.comm.init(baudrate=115200, bits=8, parity=0, stop=1, timeout=100)

        # Example: wrap a plain SPI number.
        # if type(comm) is int:
        #     from machine import SPI, Pin
        #     comm = SPI(comm, **kwargs)
        #     cs = Pin(kwargs.pop("cs"))
        #     cs.init(Pin.OUT, value=1)
        #     self.cs = cs
        # self.spi = comm

        self.comm = comm

        super().__init__(*args)


    # --- Required primitives -------------------------------------------------
    def start(self):
        """
        Connect to the device, enter programming mode, identify the chip.
        May print diagnostics.
        """
        pass


    def RM(self, addr, sz):
        """
        Read sz bytes at addr. One bus transaction / one page read.
        Do not split or chunk - BaseFlasher.read_memory() does that.

        Return bytes or bytearray.
        """
        # TODO
        raise NotImplementedError("RM")


    def WM(self, addr, data):
        """
        Write one block at addr. One page / one bus request.
        Do not loop over pages - BaseFlasher.write_memory() does that.

        Recommended (optional) optimisation - skip already-erased blocks:
            if super().WM(addr, data):
                return
        Without it, WM still works, it just writes unconditionally.
        """
        # if super().WM(addr, data):   # optional fast path
        #     return
        # TODO: send the write command / data / wait for completion
        # time.sleep_ms(self.wdelay)
        raise NotImplementedError("WM")


    def CM(self, addr=None):
        """
        Clear (erase) one page at addr, or the whole chip if addr is None.
        One erase operation, no looping.

        Not needed at all if the chip auto-erases on write
        (autoclear = False, STM8-like), but BaseFlasher may still call it
        if the user asks for an explicit clear.
        """
        # TODO
        # if addr is None:
        #     # chip erase
        # else:
        #     page, psz = self.getPage(addr)
        #     # page erase
        # time.sleep_ms(self.wdelay)
        raise NotImplementedError("CM")


    # --- Optional: size / run ------------------------------------------------
    def read_flash_size(self):
        """
        Return flash size in bytes, or 0 if unknown.
        BaseFlasher will print either "Flash size: N KB" or "Flash size unknown".
        """
        # TODO
        return 0


    def run(self):
        """
        Start the target after flashing (jump to reset vector, leave ISP, ...).
        """
        # TODO
        pass


    # --- Optional: protection commands (STM32-like naming) -------------------
    #
    # These toggle the on-chip protection fuses/registers.  They are NOT
    # called by the flasher core; expose them to the user.
    #
    # Naming convention (matches STM32_flash.py):
    #   WP - Write  Protect    (enable write protection for a page/sector)
    #   WU - Write  Unprotect  (disable write protection)
    #   RP - Read   Protect    (enable readout protection, usually whole chip)
    #   RU - Read   Unprotect  (disable readout protection, usually whole chip)
    #
    # Notes:
    #   * WP/WU may take a page/sector index, RP/RU usually take no argument
    #     (whole chip) - keep the same signature as STM32 for API symmetry:
    #     WP(page), WU(page=None), RP(page=None), RU(page=None).
    #   * Changes to readout protection often take effect only after a reset
    #     and may trigger a mass erase when disabling RP.  Warn the user
    #     in the docstring and/or print a message.
    #   * On chips without per-page write protection, WP/WU may be no-ops
    #     or may apply to the whole chip.

    def WP(self, page=None):
        """
        Write Protect: enable write protection for the given page/sector.
        page = None -> apply to all pages (if the chip supports it).
        """
        # TODO: send the write-protect command / set the option bytes
        # self.write_cmd(0x63)
        # ...
        raise NotImplementedError("WP")

    def WU(self, page=None):
        """
        Write Unprotect: disable write protection for the given page/sector,
        or for the whole chip if page is None.
        """
        # TODO
        # self.write_cmd(0x73)
        # ...
        raise NotImplementedError("WU")

    def RP(self, page=None):
        """
        Read Protect: enable readout protection (usually whole chip).
        After enabling, RM()/verify_memory() may return garbage or 0x00
        until RU() is issued (and RU() may mass-erase the chip).
        """
        # TODO
        # self.write_cmd(0x82)
        # ...
        raise NotImplementedError("RP")

    def RU(self, page=None):
        """
        Read Unprotect: disable readout protection (usually whole chip).
        WARNING: on most parts this triggers a full chip erase.
        """
        # TODO
        # self.write_cmd(0x92)
        # ...
        raise NotImplementedError("RU")


    # --- Optional: mixed page sizes -----------------------------------------
    # Override getPage() if psz is not adequate to describe page layout (F411).
    # Return (page_index, page_size_in_bytes) for addr.
    #
    # def getPage(self, addr):
    #     addr -= self.addr
    #     plist = self.pages[self.id]
    #     i = 0
    #     for psz in plist:
    #         psz *= 1024
    #         if addr < psz:
    #             return i, psz
    #         addr -= psz
    #         i += 1
    #     n, r = divmod(addr, psz)
    #     return i + n, psz


# Short alias used in imports, e.g.  from PyroFlash.Template import Template
Template = Flasher