#!/bin/bash
jq -c '.[]' result.json | while read i; do
    COMMAND=$(echo $i | jq -r ' .command')
    RAW=$(echo $i | jq -r ' .value')
    PAYLOAD=$(echo $i | jq -r '. ')
    mosquitto_pub -u $MQTTUSERNAME -P $MQTTPASSWORD -h $MQTTHOST -p $MQTTPORT -t $MQTTTOPIC/$COMMAND -m "$PAYLOAD" -x 120 -c --id "VCONTROLD-PUB" -V "mqttv5"
done