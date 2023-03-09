#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.event import Event


class SystemResourceReleasedEvent(Event):
    """
    system.resource.released event
    """

    EVENT_NAME = u"system.resource.released"
    EVENT_PROPAGATE = False
    EVENT_PARAMS = [u"resource", u"module"]

    def __init__(self, params):
        """
        Constructor

        Args:
            params (dict): event parameters
        """
        Event.__init__(self, params)
