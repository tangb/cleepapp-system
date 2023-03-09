#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.event import Event


class SystemResourceAcquiredEvent(Event):
    """
    system.resource.acquired event
    """

    EVENT_NAME = u"system.resource.acquired"
    EVENT_PROPAGATE = False
    EVENT_PARAMS = [u"resource", u"module"]

    def __init__(self, params):
        """
        Constructor

        Args:
            params (dict): event parameters
        """
        Event.__init__(self, params)
