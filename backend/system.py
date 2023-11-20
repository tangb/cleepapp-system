#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
from datetime import datetime
import time
from zipfile import ZipFile, ZIP_DEFLATED
from tempfile import NamedTemporaryFile
import psutil
from cleep.exception import InvalidParameter, CommandError, CommandInfo
from cleep.core import CleepModule
from cleep.libs.internals.task import Task
from cleep.libs.internals.console import Console
from cleep.libs.configs.cleepconf import CleepConf
import cleep.libs.internals.tools as Tools
from cleep import __version__ as VERSION
from cleep.libs.internals.cleepbackup import CleepBackup


__all__ = ["System"]


class System(CleepModule):
    """
    Helps controlling the system device (poweroff, reboot) and monitoring it, and the connected hardware
    """

    MODULE_AUTHOR = "Cleep"
    MODULE_VERSION = "2.2.0"
    MODULE_CATEGORY = "APPLICATION"
    MODULE_DEPS = []
    MODULE_DESCRIPTION = "Helps controlling and monitoring the device"
    MODULE_LONGDESCRIPTION = "Application that helps you to configure your system"
    MODULE_TAGS = ["troubleshoot", "monitoring", "log", "rendering", "driver", "backup"]
    MODULE_COUNTRY = None
    MODULE_URLINFO = "https://github.com/CleepDevice/cleepapp-system"
    MODULE_URLHELP = None
    MODULE_URLBUGS = "https://github.com/CleepDevice/cleepapp-system/issues"
    MODULE_URLSITE = None

    MODULE_CONFIG_FILE = "system.conf"

    DEFAULT_CONFIG = {
        "monitoring": False,
        "ssl": False,
        "auth": False,
        "rpcport": 80,
        "eventsnotrenderable": [],
        "crashreport": True,
        "cleepbackupdelay": 15,
        "needreboot": False,
        "enablepowerled": True,
        "enableactivityled": True,
    }

    MONITORING_CPU_DELAY = 60.0  # 1 minute
    MONITORING_MEMORY_DELAY = 300.0  # 5 minutes
    MONITORING_DISKS_DELAY = 21600  # 6 hours

    THRESHOLD_MEMORY = 80.0
    THRESHOLD_DISK_SYSTEM = 80.0
    THRESHOLD_DISK_EXTERNAL = 90.0

    EVENT_SEPARATOR = "__"

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects
            debug_enabled (bool): flag to set debug level to logger
        """
        CleepModule.__init__(self, bootstrap, debug_enabled)

        # members
        self.bootstrap = bootstrap
        self.events_broker = bootstrap["events_broker"]
        self.log_file = bootstrap["log_file"]
        self.__monitor_cpu_uuid = None
        self.__monitor_memory_uuid = None
        self.__monitoring_cpu_task = None
        self.__monitoring_memory_task = None
        # self.__monitoring_disks_task = None
        self.__process = None
        self.__need_restart = False
        self.cleep_update_pending = False
        self.cleep_backup = CleepBackup(self.cleep_filesystem, self.crash_report)
        self.cleep_backup_delay = None
        self.cleep_conf = CleepConf(self.cleep_filesystem)
        self.drivers = bootstrap["drivers"]

        # events
        self.device_poweroff_event = self._get_event("system.device.poweroff")
        self.device_reboot_event = self._get_event("system.device.reboot")
        self.cleep_restart_event = self._get_event("system.cleep.restart")
        self.cleep_need_restart_event = self._get_event("system.cleep.needrestart")
        self.monitoring_cpu_event = self._get_event("system.monitoring.cpu")
        self.monitoring_memory_event = self._get_event("system.monitoring.memory")
        self.alert_memory_event = self._get_event("system.alert.memory")
        self.driver_install_event = self._get_event("system.driver.install")
        self.driver_uninstall_event = self._get_event("system.driver.uninstall")

    def _configure(self):
        """
        Configure module
        """
        # reset needreboot flag
        self._set_config_field("needreboot", False)

        # configure crash report
        self._configure_crash_report(self._get_config_field("crashreport"))

        # set members
        self.cleep_backup_delay = self._get_config_field("cleepbackupdelay")

        # init first cpu percent for current process
        self.__process = psutil.Process(os.getpid())
        self.__process.cpu_percent()

        # store device uuids for events
        devices = self.get_module_devices()
        monitor_uuid = None
        for (device_uuid, device) in devices.items():
            if device["type"] == "monitorcpu":
                self.__monitor_cpu_uuid = device_uuid
            elif device["type"] == "monitormemory":
                self.__monitor_memory_uuid = device_uuid
            elif device["type"] == "monitor":
                monitor_uuid = device_uuid

        # create missing devices
        if not monitor_uuid:
            # add fake monitor device (used to have a device on dashboard)
            self.logger.info('Create missing "monitor" device')
            self._add_device({"type": "monitor", "name": "System monitor"})
        if not self.__monitor_cpu_uuid:
            # add monitor cpu device (used to save cpu data into database and has no widget)
            self.logger.info('Create missing "monitorcpu" device')
            self._add_device({"type": "monitorcpu", "name": "Cpu monitor"})
        if not self.__monitor_memory_uuid:
            # add monitor memory device (used to save cpu data into database and has no widget)
            self.logger.info('Create missing "monitormemory" device')
            self._add_device({"type": "monitormemory", "name": "Memory monitor"})

        # configure not renderable events
        self._set_not_renderable_events()

        # apply tweaks
        self.__apply_tweaks()

    def _on_start(self):
        """
        Application started
        """
        self.__start_monitoring_tasks()

    def _on_stop(self):
        """
        Application stop
        """
        # stop monitoring task
        self.__stop_monitoring_tasks()

    def _configure_crash_report(self, enable):
        """
        Configure crash report

        Args:
            enable (bool): True to enable crash report
        """
        # configure crash report
        if enable:
            self.crash_report.enable()
        else:
            self.crash_report.disable()

        if not self.crash_report.is_enabled():
            self.logger.info("Crash report is disabled")

    def get_module_config(self):
        """
        Return full module configuration

        Returns:
            dict: configuration
        """
        config = self._get_config()

        # add volatile infos
        config.update(
            {
                "needrestart": self.__need_restart,
                "version": VERSION,
                "eventsnotrenderable": self.get_not_renderable_events(),
                "debug": {
                    "core": self.cleep_conf.is_core_debugged(),
                    "trace": self.cleep_conf.is_trace_enabled(),
                },
            }
        )

        return config

    def get_module_devices(self):
        """
        Return system devices

        Returns:
            dict: devices
        """
        devices = super().get_module_devices()

        monitor_device = next((dev for dev in devices.values() if dev["type"] == "monitor"), None)
        if monitor_device:
            monitor_device.update({
                "uptime": System.get_uptime(),
                "cpu": self.get_cpu_usage(),
                "memory": self.get_memory_usage(),
            })

        cpu_data = {
            "hidden": not bool(self.__monitoring_cpu_task),
        }
        cpu_data.update(self.get_cpu_usage())
        cpu_device = next((dev for dev in devices.values() if dev["type"] == "monitorcpu"), None)
        if cpu_device:
            cpu_device.update(cpu_data)

        mem_data = {
            "hidden": not bool(self.__monitoring_memory_task),
        }
        mem_data.update(self.get_memory_usage())
        mem_device = next((dev for dev in devices.values() if dev["type"] == "monitormemory"), None)
        if mem_device:
            mem_device.update(mem_data)

        return devices

    def on_event(self, event):
        """
        Receive event

        Args:
            event (MessageRequest): event data
        """
        # handle restart event
        if event["event"] == "system.cleep.needrestart":
            self.__need_restart = True

        # handle reboot event
        elif event["event"].endswith("device.needreboot"):
            self._set_config_field("needreboot", True)

        if event["event"] == "parameters.time.now":
            # backup configuration
            if not event["params"]["minute"] % self.cleep_backup_delay:
                self.backup_cleep_config()

    def set_monitoring(self, monitoring):
        """
        Set monitoring flag

        Args:
            monitoring (bool): monitoring flag
        """
        self._check_parameters(
            [
                {"name": "monitoring", "type": bool, "value": monitoring},
            ]
        )

        if not self._set_config_field("monitoring", monitoring):
            raise CommandError("Unable to save configuration")

        if self._get_config_field("monitoring"):
            self.__start_monitoring_tasks()
        else:
            self.__stop_monitoring_tasks()

    def get_monitoring(self):
        """
        Return monitoring configuration

        Returns:
            bool: True if monitoring is enabled
        """
        return self._get_config_field("monitoring")

    def reboot_device(self, delay=5.0):
        """
        Reboot device

        Args:
            delay (float, optional): delay before rebooting the device. Defaults to 5.0.
        """
        # backup configuration
        self.backup_cleep_config()

        # send event
        self.device_reboot_event.send({"delay": delay})

        # and reboot system
        console = Console()
        console.command_delayed("reboot -f", delay)

    def poweroff_device(self, delay=5.0):
        """
        Poweroff device

        Args:
            delay (float, optional): delay before powering off the device. Defaults to 5.0.
        """
        # backup configuration
        self.backup_cleep_config()

        # send event
        self.device_poweroff_event.send({"delay": delay})

        # and reboot system
        console = Console()
        console.command_delayed("poweroff -f", delay)

    def restart_cleep(self, delay=3.0):
        """
        Restart Cleep

        Args:
            delay (float, optional): delay before restarting the device. Defaults to 3.0.
        """
        # backup configuration
        self.backup_cleep_config()

        # send event
        self.cleep_restart_event.send({"delay": delay})

        # and restart cleep
        console = Console()
        console.command_delayed("/etc/cleep/cleephelper.sh restart", delay)

    def get_memory_usage(self):
        """
        Return system memory usage

        Returns:
            dict: memory usage::

                {
                    total (int): total memory in bytes
                    available (int): available memory in bytes
                    availablehr (string): human readable available memory
                    cleep (float): cleep process memory in bytes
                }

        """
        system = psutil.virtual_memory()
        cleep = self.__process.memory_info()[0]
        return {
            "total": system.total,
            # 'totalhr': Tools.hr_bytes(system.total),
            "available": system.available,
            "availablehr": Tools.hr_bytes(system.available),
            # 'used_percent': system.percent,
            "cleep": cleep,
            # 'cleephr': Tools.hr_bytes(cleep),
            # 'others': system.total - system.available - cleep
        }

    def get_cpu_usage(self):
        """
        Return cpu usage for cleep process and system

        Returns:
            dict: cpu usage::

                {
                    system (float): system cpu usage percentage
                    cleep (float): cleep cpu usage percentage
                }

        """
        system = min(psutil.cpu_percent(), 100.0)
        cleep = min(self.__process.cpu_percent(), 100.0)
        return {"system": system, "cleep": cleep}

    @staticmethod
    def get_uptime():
        """
        Return system uptime (in seconds)

        Returns:
            dict: uptime info ::

                {
                    uptime (int): timestamp
                    uptimehr (string): uptime human readble string
                }

        """
        uptime = int(time.time() - psutil.boot_time())
        return {"uptime": uptime, "uptimehr": Tools.hr_uptime(uptime)}

    def __start_monitoring_tasks(self):
        """
        Start monitoring threads
        """
        self.logger.info("Starting monitoring")
        if not self._get_config_field("monitoring"):
            return

        self.__monitoring_cpu_task = Task(
            self.MONITORING_CPU_DELAY, self._monitoring_cpu_task, self.logger
        )
        self.__monitoring_cpu_task.start()
        self.__monitoring_memory_task = Task(
            self.MONITORING_MEMORY_DELAY, self._monitoring_memory_task, self.logger
        )
        self.__monitoring_memory_task.start()
        # self.__monitoring_disks_task = Task(self.MONITORING_DISKS_DELAY, self._monitoring_disks_task, self.logger)
        # self.__monitoring_disks_task.start()

    def __stop_monitoring_tasks(self):
        """
        Stop monitoring threads
        """
        self.logger.info("Stopping monitoring")
        if self.__monitoring_cpu_task is not None:
            self.__monitoring_cpu_task.stop()
            self.__monitoring_cpu_task = None
        if self.__monitoring_memory_task is not None:
            self.__monitoring_memory_task.stop()
            self.__monitoring_memory_task = None
        # if self.__monitoring_disks_task is not None:
        #     self.__monitoring_disks_task.stop()

    def _monitoring_cpu_task(self):
        """
        Read cpu usage
        """
        self.monitoring_cpu_event.send(
            params=self.get_cpu_usage(), device_id=self.__monitor_cpu_uuid
        )

    def _monitoring_memory_task(self):
        """
        Read memory usage
        Send alert if threshold reached
        """
        memory = self.get_memory_usage()

        # detect memory leak
        percent = (
            (float(memory["total"]) - float(memory["available"]))
            / float(memory["total"])
            * 100.0
        )
        if percent >= self.THRESHOLD_MEMORY:
            self.alert_memory_event.send(
                params={"percent": percent, "threshold": self.THRESHOLD_MEMORY}
            )

        self.monitoring_memory_event.send(
            params=memory, device_id=self.__monitor_memory_uuid
        )

    # TODO move to filesystem app
    # def _monitoring_disks_task(self):
    # """
    #    Read disks usage
    #    Only used to send alert when threshold reached
    #    """
    #    disks = self.get_filesystem_infos()
    #    for disk in disks:
    #        if not disk['mounted']:
    #            continue
    #
    #        if disk['mountpoint'] == '/' and disk['percent'] >= self.THRESHOLD_DISK_SYSTEM:
    #            self.alert_disk_event.send(params={
    #                'percent': disk['percent'],
    #                'threshold': self.THRESHOLD_DISK_SYSTEM,
    #                'mountpoint': disk['mountpoint']
    #            })
    #
    #        elif disk['mountpoint'] not in ('/', '/boot') and disk['percent'] >= self.THRESHOLD_DISK_EXTERNAL:
    #            self.alert_disk_event.send(params={
    #                'percent': disk['percent'],
    #                'threshold': self.THRESHOLD_DISK_EXTERNAL,
    #                'mountpoint': disk['mountpoint']
    #            })

    # TODO move to filesystem app
    # def get_filesystem_infos(self):
    #    """
    #    Return filesystem infos (all values are in octets)
    #
    #    Returns:
    #        list: list of devices available with some informations::
    #
    #            [
    #                {
    #                    'device': <device path /dev/XXX (string)>
    #                    'uuid': <device uuid like found in blkid (string)>,
    #                    'system': <system partition (bool)>,
    #                    'mountpoint': <mountpoint (string)>
    #                    'mounted': <partition is mounted (bool)>,
    #                    'mounttype': <partition type (string)>,
    #                    'options': <mountpoint options (string)>,
    #                    'total': <partition total space in octets (number)>,
    #                    'used': <partition used space in octets (number)>,
    #                    'free': <partition free space in octets (number)>,
    #                    'percent': <partition used space in percentage (number)>
    #                },
    #                ...
    #            ]
    #
    #    """
    #    # get mounted partitions and all devices
    #    fstab = Fstab(self.cleep_filesystem)
    #    mounted_partitions = fstab.get_mountpoints()
    #    self.logger.debug('mounted_partitions=%s' % mounted_partitions)
    #    all_devices = fstab.get_all_devices()
    #    self.logger.debug('all_devices=%s' % all_devices)
    #
    #    # build output
    #    fsinfos = []
    #    for device in all_devices:
    #        # check if partition is mounted
    #        mounted = {'mounted':False, 'mountpoint':'', 'mounttype':'-', 'options':'', 'uuid':None}
    #        system = False
    #        for partition in mounted_partitions:
    #            if mounted_partitions[partition]['device'] == device:
    #                mounted['mounted'] = True
    #                mounted['mountpoint'] = mounted_partitions[partition]['mountpoint']
    #                mounted['device'] = mounted_partitions[partition]['device']
    #                mounted['uuid'] = mounted_partitions[partition]['uuid']
    #                mounted['mounttype'] = mounted_partitions[partition]['mounttype']
    #                mounted['options'] = mounted_partitions[partition]['options']
    #                if mounted_partitions[partition]['mountpoint'] in ('/', '/boot'):
    #                    system = True
    #
    #        # get mounted partition usage
    #        usage = {'total':0, 'used':0, 'free':0, 'percent':0.0}
    #        if mounted['mounted']:
    #            sdiskusage = psutil.disk_usage(mounted['mountpoint'])
    #            self.logger.debug('diskusage for %s: %s' % (device, sdiskusage))
    #            usage['total'] = sdiskusage.total
    #            usage['used'] = sdiskusage.used
    #            usage['free'] = sdiskusage.free
    #            usage['percent'] = sdiskusage.percent
    #
    #        # fill infos
    #        fsinfos.append({
    #            'device': device,
    #            'uuid': mounted['uuid'],
    #            'system': system,
    #            'mountpoint': mounted['mountpoint'],
    #            'mounted': mounted['mounted'],
    #            'mounttype': mounted['mounttype'],
    #            'options': mounted['options'],
    #            'total': usage['total'],
    #            'used': usage['used'],
    #            'free': usage['free'],
    #            'percent': usage['percent']
    #        })
    #
    #    self.logger.debug('Filesystem infos: %s' % fsinfos)
    #    return fsinfos

    def download_logs(self):
        """
        Download logs file

        Returns:
            string: script full path

        Raises:
            Exception: if error occured
        """
        if not os.path.exists(self.log_file):
            # file doesn't exist, raise exception
            raise CommandError("Logs file doesn't exist")

        # log file exists, zip it
        with NamedTemporaryFile(delete=False) as file_descriptor:
            log_filename = file_descriptor.name
            self.logger.debug("Zipped log filename: %s", log_filename)
            with ZipFile(file_descriptor, "w", ZIP_DEFLATED) as archive:
                archive.write(self.log_file, "cleep.log")

        now = datetime.now()
        filename = f"cleep_{now.year}{now.month:02d}{now.day:02d}_{now.hour:02d}{now.minute:02d}{now.second:02d}.zip"

        return {"filepath": log_filename, "filename": filename}

    def get_logs(self):
        """
        Return logs file content

        Returns:
            list: list of lines from log file::

                [
                    line1 (str),
                    line2 (str),
                    ...
                ]

        """
        lines = []
        if os.path.exists(self.log_file):
            lines = self.cleep_filesystem.read_data(self.log_file)

        return lines

    def clear_logs(self):
        """
        Clear logs file

        Returns:
            bool: True if operation succeed, False otherwise
        """
        if os.path.exists(self.log_file):
            return self.cleep_filesystem.write_data(self.log_file, "")

        return False

    def set_trace(self, trace):
        """
        Set trace (full debug)

        Args:
            trace (bool): enable trace
        """
        self._check_parameters(
            [
                {"name": "trace", "type": bool, "value": trace},
            ]
        )

        # save log level in conf file
        if trace:
            self.cleep_conf.enable_trace()
        else:
            self.cleep_conf.disable_trace()

        # send event cleep needs to be restarted
        self.__need_restart = True
        self.cleep_need_restart_event.send()

    def set_core_debug(self, debug):
        """
        Set debug on all core modules

        Args:
            debug (bool): enable debug
        """
        self._check_parameters(
            [
                {"name": "debug", "type": bool, "value": debug},
            ]
        )

        if debug:
            self.bootstrap["internal_bus"].logger.setLevel(logging.DEBUG)
            self.bootstrap["events_broker"].logger.setLevel(logging.DEBUG)
            self.bootstrap["cleep_filesystem"].logger.setLevel(logging.DEBUG)
            self.bootstrap["formatters_broker"].logger.setLevel(logging.DEBUG)
            self.bootstrap["crash_report"].logger.setLevel(logging.DEBUG)
            self.bootstrap["critical_resources"].logger.setLevel(logging.DEBUG)
            self.bootstrap["drivers"].logger.setLevel(logging.DEBUG)

            self.cleep_conf.enable_core_debug()
        else:
            self.bootstrap["internal_bus"].logger.setLevel(logging.INFO)
            self.bootstrap["events_broker"].logger.setLevel(logging.INFO)
            self.bootstrap["cleep_filesystem"].logger.setLevel(logging.INFO)
            self.bootstrap["formatters_broker"].logger.setLevel(logging.INFO)
            self.bootstrap["crash_report"].logger.setLevel(logging.INFO)
            self.bootstrap["critical_resources"].logger.setLevel(logging.INFO)
            self.bootstrap["drivers"].logger.setLevel(logging.INFO)

            self.cleep_conf.disable_core_debug()

    def set_module_debug(self, module_name, debug):
        """
        Set module debug flag

        Args:
            module_name (string): module name
            debug (bool): enable debug
        """
        self._check_parameters(
            [
                {"name": "module_name", "type": str, "value": module_name},
                {"name": "debug", "type": bool, "value": debug},
            ]
        )

        # save log level in conf file
        if debug:
            self.cleep_conf.enable_module_debug(module_name)
        else:
            self.cleep_conf.disable_module_debug(module_name)

        # set debug on module
        if module_name == "rpc":
            # specific command for rpcserver
            resp = self.send_command("set_rpc_debug", "inventory", {"debug": debug})
        else:
            resp = self.send_command("set_debug", module_name, {"debug": debug})
        if resp.error:
            self.logger.error(
                "Unable to set debug on module %s: %s", module_name, resp.message
            )
            raise CommandError("Update debug failed")

    def _set_not_renderable_events(self):
        """
        Set renderable flag on all events that are configured as not renderable
        """
        events_to_delete = []
        for event_not_renderable in self.get_not_renderable_events():
            try:
                self.logger.debug(
                    'Disable event "%s" rendering for "%s"', event_not_renderable["event"], event_not_renderable["renderer"],
                )
                event = self.events_broker.get_event_instance(
                    event_not_renderable["event"]
                )
                event.set_renderable(event_not_renderable["renderer"], False)
            except Exception:
                # event does not exists anymore, delete it
                key = f"{event_not_renderable['renderer']}{self.EVENT_SEPARATOR}{event_not_renderable['event']}"
                if key not in events_to_delete:
                    events_to_delete.append(key)

        # remove old not renderable events
        not_renderable_events = self._get_config_field("eventsnotrenderable")
        for event in events_to_delete:
            not_renderable_events.remove(event)
        self._set_config_field("eventsnotrenderable", not_renderable_events)

    def set_event_renderable(self, renderer_name, event_name, renderable):
        """
        Set event renderable status

        Args:
            renderer_name (string): renderer name
            event_name (string): event name
            renderable (bool): True to allow event rendering for renderer, False otherwise

        Returns:
            list: list of not renderable events::

                [
                    {
                        event (string): event name,
                        renderer (string): renderer name
                    },
                    ...
                ]

        """
        self._check_parameters(
            [
                {"name": "renderer_name", "type": str, "value": renderer_name},
                {"name": "event_name", "type": str, "value": event_name},
                {"name": "renderable", "type": bool, "value": renderable},
            ]
        )

        # update config
        events_not_renderable = self._get_config_field("eventsnotrenderable")
        key = f"{renderer_name}{self.EVENT_SEPARATOR}{event_name}"

        if key in events_not_renderable and renderable:
            # enable event rendering
            events_not_renderable.remove(key)
        elif key not in events_not_renderable and not renderable:
            # disable event rendering
            events_not_renderable.append(key)
        if not self._set_config_field("eventsnotrenderable", events_not_renderable):
            raise CommandError("Unable to save configuration")

        # set event renderable status
        self.events_broker.set_event_renderable(event_name, renderer_name, renderable)

        return self.get_not_renderable_events()

    def get_not_renderable_events(self):
        """
        Return list of not renderable events

        Returns:
            list: list of events to not render::

                [
                    {
                        event (string): event name,
                        renderer (string): renderer name
                    },
                    ...
                ]

        """
        # split items to get renderer and event splitted
        events_not_renderable = []
        for item in self._get_config_field("eventsnotrenderable"):
            (renderer, event) = item.split(self.EVENT_SEPARATOR)
            events_not_renderable.append({"renderer": renderer, "event": event})

        return events_not_renderable

    def set_crash_report(self, enable):
        """
        Enable or disable crash report

        Args:
            enable (bool): True to enable crash report

        Raises:
            CommandError: if error occured
        """
        self._check_parameters([{"name": "enable", "type": bool, "value": enable}])

        # save config
        if not self._set_config_field("crashreport", enable):
            raise CommandError("Unable to save crash report value")

        # configure crash report
        self._configure_crash_report(enable)

    def backup_cleep_config(self):
        """
        Backup Cleep configuration files on filesystem

        Returns:
            bool: True if backup successful
        """
        self.logger.debug("Backup Cleep configuration")
        return self.cleep_backup.backup()

    def set_cleep_backup_delay(self, delay):
        """
        Set Cleep backup delay

        Args:
            delay (int): delay in minutes (5..60)
        """
        self._check_parameters(
            [
                {
                    "name": "delay",
                    "type": int,
                    "value": delay,
                    "validator": lambda val: 5 <= val <= 120,
                }
            ]
        )

        if self._set_config_field("cleepbackupdelay", delay):
            self.cleep_backup_delay = delay

    def _install_driver_terminated(self, driver_type, driver_name, success, message):
        """
        Callback when driver is installed

        Args:
            driver_type (string): driver type
            driver_name (string): driver name
            success (bool): True if install was successful, False otherwise
            message (string): error message
        """
        data = {
            "drivertype": driver_type,
            "drivername": driver_name,
            "installing": False,
            "success": success,
            "message": message,
        }
        self.logger.debug("Driver install terminated: %s", data)

        # send event
        self.driver_install_event.send(data)

        # reboot device if install succeed and required
        driver = success and self.drivers.get_driver(driver_type, driver_name)
        if driver and driver.require_reboot():
            self.reboot_device()

    def install_driver(self, driver_type, driver_name, force=False):
        """
        Install specified driver.
        If install succeed, device will reboot after a delay

        Args:
            driver_type (string): driver type
            driver_name (string): driver name
            force (bool, optional): force install (repair). Defaults to False.

        Raises:
            MissingParameter: if a parameter is missing
            InvalidParameter: if driver was not found
            CommandInfo: if driver already installed
        """
        self._check_parameters(
            [
                {"name": "driver_type", "type": str, "value": driver_type},
                {"name": "driver_name", "type": str, "value": driver_name},
                {"name": "force", "type": bool, "value": force},
            ]
        )

        # get driver
        driver = self.drivers.get_driver(driver_type, driver_name)
        if not driver:
            raise InvalidParameter("No driver found for specified parameters")

        if not force and driver.is_installed():
            raise CommandInfo("Driver is already installed")

        # launch installation (non blocking) and send event
        driver.install(self._install_driver_terminated, logger=self.logger)
        self.driver_install_event.send(
            {
                "drivertype": driver_type,
                "drivername": driver_name,
                "installing": True,
                "success": None,
                "message": None,
            }
        )

    def _uninstall_driver_terminated(self, driver_type, driver_name, success, message):
        """
        Callback when driver is uninstalled

        Args:
            driver_type (string): driver type
            driver_name (string): driver name
            success (bool): True if install was successful, False otherwise
            message (string): error message
        """
        data = {
            "drivertype": driver_type,
            "drivername": driver_name,
            "uninstalling": False,
            "success": success,
            "message": message,
        }
        self.logger.debug("Uninstall driver terminated: %s", data)

        # send event
        self.driver_uninstall_event.send(data)

        # reboot device if uninstall succeed
        driver = success and self.drivers.get_driver(driver_type, driver_name)
        if driver and driver.require_reboot():
            self.reboot_device()

    def uninstall_driver(self, driver_type, driver_name):
        """
        Uninstall specified driver.
        If uninstall succeed, device will reboot after a delay.

        Args:
            driver_type (string): driver type
            driver_name (string): driver name

        Raises:
            MissingParameter: if a parameter is missing
            InvalidParameter: if driver was not found
            CommandInfo: if driver is not installed
        """
        self._check_parameters(
            [
                {"name": "driver_type", "type": str, "value": driver_type},
                {"name": "driver_name", "type": str, "value": driver_name},
            ]
        )

        # get driver instance
        driver = self.drivers.get_driver(driver_type, driver_name)
        if not driver:
            raise InvalidParameter("No driver found for specified parameters")

        if not driver.is_installed():
            raise CommandInfo("Driver is not installed")

        # launch uninstallation (non blocking) and send event
        driver.uninstall(self._uninstall_driver_terminated, logger=self.logger)
        self.driver_uninstall_event.send(
            {
                "drivertype": driver_type,
                "drivername": driver_name,
                "uninstalling": True,
                "success": None,
                "message": None,
            }
        )

        return True

    def __apply_tweaks(self):
        """
        Apply all tweaks
        """
        power_led_enabled = self._get_config_field("enablepowerled", False)
        try:
            self.tweak_power_led(power_led_enabled)
        except Exception:
            self.logger.exception("Error applying power led tweak")

        activity_led_enabled = self._get_config_field("enableactivityled", False)
        try:
            self.tweak_activity_led(activity_led_enabled)
        except Exception:
            self.logger.exception("Error applying activity led tweak")

    def tweak_power_led(self, enable):
        """
        Tweak raspberry pi power led

        Note:
            Infos from https://www.jeffgeerling.com/blogs/jeff-geerling/controlling-pwr-act-leds-raspberry-pi

        Args:
            enable (bool): True to turn on led
        """
        if not os.path.exists("/sys/class/leds/led1"):
            self.logger.info("Power led not found on this device")
            return

        raspi = Tools.raspberry_pi_infos()
        off_value = "0" if raspi["model"].lower().find("zero") else "1"
        on_value = "1" if raspi["model"].lower().find("zero") else "0"
        echo_value = on_value if enable else off_value
        self.logger.debug("Tweaking power led with value %s", echo_value)
        console = Console()
        resp = console.command(f"echo {echo_value} > /sys/class/leds/led1/brightness")
        if resp["returncode"] != 0:
            raise CommandError("Error tweaking power led")

        # store led status
        self._set_config_field("enablepowerled", enable)

    def tweak_activity_led(self, enable):
        """
        Tweak raspberry pi activity led

        Note:
            Infos from https://www.jeffgeerling.com/blogs/jeff-geerling/controlling-pwr-act-leds-raspberry-pi

        Args:
            enable (bool): True to turn on led
        """
        if not os.path.exists("/sys/class/leds/led0"):
            self.logger.info("Activity led not found on this device")
            return

        raspi = Tools.raspberry_pi_infos()
        off_value = "0" if raspi["model"].lower().find("zero") else "1"
        on_value = "1" if raspi["model"].lower().find("zero") else "0"
        echo_value = on_value if enable else off_value
        self.logger.debug("Tweaking activity led with value %s", echo_value)
        console = Console()

        # update led status
        resp = console.command(f"echo {echo_value} > /sys/class/leds/led0/brightness")
        if resp["returncode"] != 0:
            raise CommandError("Error tweaking activity led")

        # restore default trigger mode to mmc0 activity if necessary
        if enable:
            resp = console.command("echo mmc0 > /sys/class/leds/led0/trigger")
            if resp["returncode"] != 0:
                raise CommandError("Error tweaking activity led trigger mode")

        # store led status
        self._set_config_field("enableactivityled", enable)
