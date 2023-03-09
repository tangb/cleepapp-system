#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.event import Event


class SystemAlertDiskEvent(Event):
    """
    System.alert.disk event
    """

    EVENT_NAME = "system.alert.disk"
    EVENT_PROPAGATE = True
    EVENT_PARAMS = ["percent", "threshold", "mountpoint"]

    def __init__(self, params):
        """
        Constructor

        Args:
            params (dict): event parameters
        """
        Event.__init__(self, params)
