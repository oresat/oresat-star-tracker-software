#!/bin/bash

bus_id=vcan0
node_id=0x2C
capture_idx=0x6002

sudo olaf-sdo-transfer $bus_id $node_id 'w' $capture_idx  0 u16
