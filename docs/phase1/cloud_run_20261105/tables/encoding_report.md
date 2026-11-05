| column | rule | distinct_raw | distinct_encoded | field_group |
|---|---|---|---|---|
| tcp.flags | hex -> integer; plain '0' (absent) -> -1 | 8 | 8 | TCP |
| tcp.time_delta | numeric (float) | 10514 | 10514 | TCP |
| tcp.len | numeric (float) | 773 | 773 | TCP |
| mqtt.conack.flags | hex -> integer; plain '0' (absent) -> -1 | 2 | 2 | MQTT |
| mqtt.conack.val | numeric (float) | 2 | 2 | MQTT |
| mqtt.conflag.cleansess | numeric (float) | 2 | 2 | MQTT |
| mqtt.conflag.passwd | numeric (float) | 2 | 2 | MQTT |
| mqtt.conflag.uname | numeric (float) | 2 | 2 | MQTT |
| mqtt.conflags | hex -> integer; plain '0' (absent) -> -1 | 4 | 4 | MQTT |
| mqtt.dupflag | numeric (float) | 2 | 2 | MQTT |
| mqtt.hdrflags | hex -> integer; plain '0' (absent) -> -1 | 14 | 14 | MQTT |
| mqtt.kalive | numeric (float) | 7 | 7 | MQTT |
| mqtt.len | numeric (float) | 92 | 92 | MQTT |
| mqtt.msgid | numeric (float) | 9999 | 9999 | MQTT |
| mqtt.msgtype | numeric (float) | 11 | 11 | MQTT |
| mqtt.proto_len | numeric (float) | 2 | 2 | MQTT |
| mqtt.protoname | category map {'0': 0, 'MQTT': 1} | 2 | 2 | MQTT |
| mqtt.qos | numeric (float) | 2 | 2 | MQTT |
| mqtt.retain | numeric (float) | 2 | 2 | MQTT |
| mqtt.ver | numeric (float) | 2 | 2 | MQTT |
