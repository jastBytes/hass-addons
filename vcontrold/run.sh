#!/usr/bin/env bashio
set -e

CONFIG_PATH=/data/options.json

USB_DEVICE=$(bashio::config 'device')
bashio::log.info "Using usb device ${USB_DEVICE}"

# adjust config to use configured device
sed -i -e "/<serial>/,/<\/serial>/ s|<tty>[0-9a-z\/._A-Z:]\{1,\}</tty>|<tty>$USB_DEVICE</tty>|g" /etc/vcontrold/vcontrold.xml

# start vcontrold
# https://github.com/openv/vcontrold/blob/master/doc/man/vcontrold.rst
bashio::log.info "Starting vcontrold.."
vcontrold -x /etc/vcontrold/vcontrold.xml --nodaemon
