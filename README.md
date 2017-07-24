## Socket Chat
#### A portable, lightweight LAN Messenger

A Python script that can be copied to as many machines as needed and allow basic chat functionality between machines.  
Built using Python builtin modules only *(see Requirements section for tkinter issues on MacOS)*

**Compatibility:**
* Windows (7 Enterprise using Python 2.7.5 & 10 Home using Python 3.6.1)
* MacOS (10.12 Sierra using Python 3.5.2)
* Linux/GNU (Ubuntu 16.04 LTS using Python )

**Requirements:**
* Python - Python3 Recommended. Python2 is supported *(see below for instructions for Unix/Linux)*
* tkinter - [IDLE and tkinter with Tcl/Tk on macOS](https://www.python.org/download/mac/tcltk/)
* IPv4 (IPv6 not supported)

**In a Unix or Linux/GNU environment, the script tries to run with Python3**
If attempting to run using Python2, Linux/Unix will require updating the first line from `#!/usr/bin/env python3` to `#!/usr/bin/env python`


#### Getting Started

Clone or download this repository. The entire application is the single file **chat.pyw**  
If click to run is available (Windows), double-click the script to start.  
Otherwise (Unix/Linux), **chat.pyw** can be initialized from a terminal:  
`cd` to directory containing **chat.pyw**  
`./chat.pyw &`
