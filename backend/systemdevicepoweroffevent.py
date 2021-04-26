#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.event import Event

class SystemDevicePoweroffEvent(Event):
    """
    System.device.poweroff event
    This event is sent just before poweroff command is launched. It allows modules to perform something before.
    """

    EVENT_NAME = 'system.device.poweroff'
    EVENT_PROPAGATE = False
    EVENT_PARAMS = ['delay']

    def __init__(self, params):
        """
        Constructor

        Args:
            params (dict): event parameters
        """
        Event.__init__(self, params)

