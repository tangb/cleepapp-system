#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.event import Event

class SystemAlertMemoryEvent(Event):
    """
    System.alert.memory event
    """

    EVENT_NAME = 'system.alert.memory'
    EVENT_PROPAGATE = True
    EVENT_PARAMS = ['percent', 'threshold']

    def __init__(self, params):
        """ 
        Constructor

        Args:
            params (dict): event parameters
        """
        Event.__init__(self, params)

