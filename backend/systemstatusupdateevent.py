#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.event import Event

class SystemStatusUpdateEvent(Event):
    """
    System.status.update event
    """

    EVENT_NAME = u'system.status.update'
    EVENT_PROPAGATE = False
    EVENT_PARAMS = [u'status', u'downloadfilesize', u'downloadpercent']

    def __init__(self, params):
        """ 
        Constructor

        Args:
            params (dict): event parameters
        """
        Event.__init__(self, params)

