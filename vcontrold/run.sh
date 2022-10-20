#!/bin/bash
sleep 3                 # search the USB device as it sometimes is USB0 or USB1
USB_DEVICE=/dev/vitocal # USB_DEVICE=`find /dev/ -name vitocal*`

echo "Device ${USB_DEVICE}"

# make device accessable
chmod 777 ${USB_DEVICE}

# start vcontrold
# https://github.com/openv/vcontrold/blob/master/doc/man/vcontrold.rst
echo "Starting vcontrold..."
vcontrold -x /config/vcontrold.xml
