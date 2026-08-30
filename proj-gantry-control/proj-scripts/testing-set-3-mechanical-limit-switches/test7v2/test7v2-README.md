


Reflashed...

```bash
❯    esptool --port /dev/ttyUSB0 erase-flash
esptool v5.3.1
Connected to ESP32 on /dev/ttyUSB0:
Chip type:          ESP32-D0WD-V3 (revision v3.1)
Features:           Wi-Fi, BT, Dual Core + LP Core, 240MHz, Vref calibration in eFuse, Coding Scheme None
Crystal frequency:  40MHz
MAC:                b0:cb:d8:cd:f2:f8

Stub flasher running.

Flash memory erased successfully in 0.6 seconds.

Hard resetting via RTS pin...
~/l/robotics-oak062426/p/p/testing-set-3/test7v2 main ?1
❯    esptool --port /dev/ttyUSB0 --baud 460800 write_flash 0x1000 <esp32-firmware>.bin
zsh: no such file or directory: esp32-firmware
~/l/robotics-oak062426/p/p/testing-set-3/test7v2 main ?1
❯    esptool --port /dev/ttyUSB0 --baud 460800 write_flash 0x1000 ~/Downloads/ESP32_GENERIC-20260824-v1.29.0.bin 
Warning: Deprecated: Command 'write_flash' is deprecated. Use 'write-flash' instead.
esptool v5.3.1
Connected to ESP32 on /dev/ttyUSB0:
Chip type:          ESP32-D0WD-V3 (revision v3.1)
Features:           Wi-Fi, BT, Dual Core + LP Core, 240MHz, Vref calibration in eFuse, Coding Scheme None
Crystal frequency:  40MHz
MAC:                b0:cb:d8:cd:f2:f8

Stub flasher running.
Changing baud rate to 460800...
Changed.

Configuring flash size...
Flash will be erased from 0x00001000 to 0x001b6fff...
Compressed 1790544 bytes to 1172437...
Writing at 0x00001000 [                              ] 
Writing at 0x0001098e [                              ] 
Writing at 0x00019883 [                              ] 
Writing at 0x00028424 [>                             ] 
Writing at 0x000335a0 [>                             ] 
Writing at 0x0003a098 [=>                            ] 
Writing at 0x0004022d [=>                            ] 
Writing at 0x000486fc [=>                            ] 
Writing at 0x000542e5 [==>                           ] 
Writing at 0x0005b606 [==>                           ] 
Writing at 0x000613d4 [===>                          ] 
Writing at 0x000685c6 [===>                          ] 
Writing at 0x0006d744 [====>                         ] 
Writing at 0x00072b2f [====>                         ] 
Writing at 0x00077f1c [====>                         ] 
Writing at 0x0007d18c [=====>                        ] 
Writing at 0x0008285f [=====>                        ] 
Writing at 0x00087d65 [======>                       ] 
Writing at 0x0008cea1 [======>                       ] 
Writing at 0x0009231c [======>                       ] 
Writing at 0x000973ce [=======>                      ] 
Writing at 0x0009c684 [=======>                      ] 
Writing at 0x000a1c5e [========>                     ] 
Writing at 0x000a70f3 [========>                     ] 
Writing at 0x000abdef [=========>                    ] 
Writing at 0x000b0c9e [=========>                    ] 
Writing at 0x000b6486 [=========>                    ] 
Writing at 0x000bc4f8 [==========>                   ] 
Writing at 0x000c1b4b [==========>                   ] 
Writing at 0x000c6e87 [===========>                  ] 
Writing at 0x000cce98 [===========>                  ] 
Writing at 0x000d2833 [===========>                  ] 
Writing at 0x000d7e61 [============>                 ] 
Writing at 0x000dd581 [============>                 ] 
Writing at 0x000e2f86 [=============>                ] 
Writing at 0x000e8b0e [=============>                ] 
Writing at 0x000ef651 [==============>               ] 
Writing at 0x000f5a82 [==============>               ] 
Writing at 0x000fb833 [==============>               ] 
Writing at 0x00101035 [===============>              ] 
Writing at 0x00106d11 [===============>              ] 
Writing at 0x0010ca80 [================>             ] 
Writing at 0x001126d7 [================>             ] 
Writing at 0x00117e64 [=================>            ] 
Writing at 0x0011cec6 [=================>            ] 
Writing at 0x0012242e [=================>            ] 
Writing at 0x00127baa [==================>           ] 
Writing at 0x0012d042 [==================>           ] 
Writing at 0x00132401 [===================>          ] 
Writing at 0x00138198 [===================>          ] 
Writing at 0x0013d7d2 [===================>          ] 
Writing at 0x00142c92 [====================>         ] 
Writing at 0x001488c0 [====================>         ] 
Writing at 0x0014e51b [=====================>        ] 
Writing at 0x00153d24 [=====================>        ] 
Writing at 0x00159726 [======================>       ] 
Writing at 0x0015f470 [======================>       ] 
Writing at 0x00164d98 [======================>       ] 
Writing at 0x00169e3a [=======================>      ] 
Writing at 0x0016ef87 [=======================>      ] 
Writing at 0x00174880 [========================>     ] 
Writing at 0x0017a3f0 [========================>     ] 
Writing at 0x0017fcb7 [========================>     ] 
Writing at 0x00185e4c [=========================>    ] 
Writing at 0x0018b359 [=========================>    ] 
Writing at 0x0019143b [==========================>   ] 
Writing at 0x001969ab [==========================>   ] 
Writing at 0x0019bee9 [===========================>  ] 
Writing at 0x001a1d82 [===========================>  ] 
Writing at 0x001a7461 [===========================>  ] 
Writing at 0x001acff7 [============================> ] 
Writing at 0x001b2df5 [============================> ] 
Wrote 1790544 bytes (1172437 compressed) at 0x00001000 in 29.7 seconds (482.1 kbit/s).
Hash of data verified.

Hard resetting via RTS pin...
```