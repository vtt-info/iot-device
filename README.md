# IoT Device

## TODO

* send age (Device.__seen) with advertising message

## Usage Example:

```python
# or DiscoverSerial, if USB ports are available
from iot_device import DiscoverNet as Discover  

discover = Discover()
discover.scan()    # look for advertised devices, run this whenever things may have changed

with discover as devices:
    
    for dev in devices:
        print(dev.uid)
        with dev as repl do:
            repl.eval("print('hello world!')")
        
```

## Classes

see *OVERVIEW.dio*

* abstract `Discover`
  * implementations `DiscoverNet`, `DiscoverSerial`
  * `scan` finds and keeps a list of available devices (run repeatedly)
  * Keeps a list of devices, returned via context manager: `with Discover as devices: ...`
  * `get_device(uid)` returns up a specific device
  * Lock: prevents co-modification (simultaneous calls to scan, etc)
  
* abstract `Device`
  * implementations `SerialDevice`, `NetDevice`
  * Not instantiated directly, get from `Discover`
  * Property `uid` - unique, read from device and cached
  * Property `locked` - True if device is in used (e.g. `eval` from different process)
  * Context manager `with dev as repl: ...`
    * `repl.eval`, `softreset`, `rsync`
    * see `Rsync`, `Fcopy`, `Repl` classes for available functions
    * `repl` object has all these capabilities 
    * (it's presently a `Rsync`, more capabilities could be added in derived classes)
    
* `Config` (singleton)
    * gets configuration from
      * `DefaultConfig`
      * `config.py`

* `certificate` - Used to encrypt communication (`DiscoverNet`)