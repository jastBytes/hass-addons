#!/usr/bin/with-contenv bashio
set -e

CONFIG_PATH=/data/options.json

USB_DEVICE=$(bashio::config 'device')
PORT="$(bashio::addon.port 3002)"
bashio::log.info "Using usb device ${USB_DEVICE}"
bashio::log.info "Using port ${PORT}"

# start vcontrold
# https://github.com/openv/vcontrold/blob/master/doc/man/vcontrold.rst
bashio::log.info "Starting vcontrold.."
vcontrold -x /etc/vcontrold/vcontrold.xml --nodaemon -h $USB_DEVICE -p $PORT
