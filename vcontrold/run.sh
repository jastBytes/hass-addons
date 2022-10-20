#!/bin/bash

USB_DEVICE=$(bashio::config 'device')
bashio::log.info "Using usb device ${USB_DEVICE}"

# start vcontrold
# https://github.com/openv/vcontrold/blob/master/doc/man/vcontrold.rst
bashio::log.info "Starting vcontrold.."
vcontrold -x /config/vcontrold.xml --nodaemon
