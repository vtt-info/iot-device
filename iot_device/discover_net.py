from .discover import Discover
from .net_device import NetDevice

import logging

logger = logging.getLogger(__file__)

class DiscoverNet(Discover):

    def __init__(self):
        # find & serve devices advertised online
        pass
