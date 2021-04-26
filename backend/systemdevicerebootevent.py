#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.event import Event

class SystemDeviceRebootEvent(Event):
    """
    System.device.reboot event
    This event is sent just before reboot command is launched. It allows modules to perform something before.
    """

    EVENT_NAME = 'system.device.reboot'
    EVENT_PROPAGATE = False
    EVENT_PARAMS = ['delay']

    def __init__(self, params):
        """
        Constructor

        Args:
            params (dict): event parameters
        """
        Event.__init__(self, params)

