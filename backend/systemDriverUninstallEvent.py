#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.event import Event

class SystemDriverUninstallEvent(Event):
    """
    System.driver.uninstall event
    This event is sent just before restart command is launched. It allows modules to perform something before.
    """

    EVENT_NAME = 'system.driver.uninstall'
    EVENT_PROPAGATE = False
    EVENT_PARAMS = ['drivertype', 'drivername', 'uninstalling', 'success', 'message']

    def __init__(self, params):
        """ 
        Constructor

        Args:
            params (dict): event parameters
        """
        Event.__init__(self, params)

