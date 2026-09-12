
### RP 2040
Step 1:
Unplug the QT Py RP2040 USB-C cable.
Hold down the BOOT button on the QT Py board.
Continue to hold BOOT on the board, plug the USB-C cable back into the computer, then release the button.
A white drive named RPI-RP2 will now mount on your file system.
Download the latest QT Py RP2040 CircuitPython .uf2 firmware file from [here](circuitpython.org/board/adafruit_qtpy_rp2040/).
Drag and drop the downloaded .uf2 file directly onto the RPI-RP2 drive.
The board will reboot automatically, and a drive named CIRCUITPY will appear on your Mac. You can now save your code.py script onto it.

Step 2:
Download the Adafruit CircuitPython Library Bundle (select the 10.x bundle matching your firmware version) from circuitpython.org/libraries.
Extract the downloaded .zip file and navigate inside the lib/ folder.
Locate the file named neopixel.mpy (or the neopixel/ directory).
Drag and drop neopixel.mpy into the lib/ folder on your mounted CIRCUITPY drive (create the lib directory at the drive root if it doesn't exist yet).

Debugging:
Sometimes the flash fails / wipes itself so this needs to be repeated. Use `just log-rp2040` in the terminal to see the logs.
Common issues include `ImportError: no module named 'neopixel'`, in this case, repeat step #2.