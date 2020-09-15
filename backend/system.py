#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
from datetime import datetime
import time
import uuid
from zipfile import ZipFile, ZIP_DEFLATED
from tempfile import NamedTemporaryFile
import psutil
from cleep.exception import InvalidParameter, MissingParameter, CommandError
from cleep.core import CleepModule
from cleep.libs.internals.task import Task
from cleep.libs.internals.console import Console
from cleep.libs.configs.fstab import Fstab
from cleep.libs.configs.cleepconf import CleepConf
from cleep.libs.configs.modulesjson import ModulesJson
import cleep.libs.internals.tools as Tools
from cleep import __version__ as VERSION
from cleep.libs.internals.cleepbackup import CleepBackup


__all__ = ['System']


class System(CleepModule):
    """
    Helps controlling the system device (halt, reboot) and monitoring it
    """
    MODULE_AUTHOR = 'Cleep'
    MODULE_VERSION = '1.1.0'
    MODULE_CATEGORY = 'APPLICATION'
    MODULE_PRICE = 0
    MODULE_DEPS = []
    MODULE_DESCRIPTION = 'Helps updating, controlling and monitoring the device'
    MODULE_LONGDESCRIPTION = 'Application that helps you to configure your system'
    MODULE_TAGS = ['troubleshoot', 'locale', 'events', 'monitoring', 'log', 'renderer', 'driver']
    MODULE_COUNTRY = ''
    MODULE_URLINFO = 'https://github.com/tangb/cleepmod-system'
    MODULE_URLHELP = None
    MODULE_URLBUGS = 'https://github.com/tangb/cleepmod-system/issues'
    MODULE_URLSITE = None

    MODULE_CONFIG_FILE = 'system.conf'

    DEFAULT_CONFIG = {
        'monitoring': False,
        'device_uuid': str(uuid.uuid4()),
        'ssl': False,
        'auth': False,
        'rpcport': 80,
        'eventsnotrendered': [],
        'crashreport': True,
        'cleepbackupdelay': 15,
        'needreboot': False,
        'latestversion': None,
    }

    MONITORING_CPU_DELAY = 60.0 #1 minute
    MONITORING_MEMORY_DELAY = 300.0 #5 minutes
    MONITORING_DISKS_DELAY = 21600 #6 hours

    THRESHOLD_MEMORY = 80.0
    THRESHOLD_DISK_SYSTEM = 80.0
    THRESHOLD_DISK_EXTERNAL = 90.0

    CLEEP_GITHUB_OWNER = 'tangb'
    CLEEP_GITHUB_REPO = 'cleep'

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects
            debug_enabled (bool): flag to set debug level to logger
        """
        CleepModule.__init__(self, bootstrap, debug_enabled)

        # members
        self.events_broker = bootstrap['events_broker']
        self.log_file = bootstrap['log_file']
        self.__monitor_cpu_uuid = None
        self.__monitor_memory_uuid = None
        self.__monitoring_cpu_task = None
        self.__monitoring_memory_task = None
        self.__monitoring_disks_task = None
        self.__process = None
        self.__need_restart = False
        self.modules_json = ModulesJson(self.cleep_filesystem)
        self.__updating_modules = []
        self.__modules = {}
        self.__cleep_update = {
            'package': {
                'url': None
            },
            'checksum': {
                'url': None
            }
        }
        self.cleep_update_pending = False
        self.cleep_backup = CleepBackup(self.cleep_filesystem, self.crash_report)
        self.cleep_backup_delay = None
        self.cleep_conf = CleepConf(self.cleep_filesystem)
        self.drivers = bootstrap['drivers']

        # events
        self.system_system_halt = self._get_event('system.system.halt')
        self.system_system_reboot = self._get_event('system.system.reboot')
        self.system_system_restart = self._get_event('system.system.restart')
        self.system_need_restart = self._get_event('system.system.needrestart')
        self.system_monitoring_cpu = self._get_event('system.monitoring.cp')
        self.system_monitoring_memory = self._get_event('system.monitoring.memory')
        self.system_alert_memory = self._get_event('system.alert.memory')
        self.system_alert_disk = self._get_event('system.alert.disk')
        # self.system_module_install = self._get_event('system.module.install')
        # self.system_module_uninstall = self._get_event('system.module.uninstall')
        # self.system_module_update = self._get_event('system.module.update')
        # self.system_cleep_update = self._get_event('system.cleep.update')
        self.system_driver_install = self._get_event('system.driver.install')
        self.system_driver_uninstall = self._get_event('system.driver.uninstall')

    def _configure(self):
        """
        Configure module
        """
        # set members
        self.cleep_backup_delay = self._get_config_field('cleepbackupdelay')

        # configure crash report
        self.__configure_crash_report(self._get_config_field('crashreport'))

        # init first cpu percent for current process
        self.__process = psutil.Process(os.getpid())
        self.__process.cpu_percent()

        # add devices if they are not already added
        if self._get_device_count() < 3:
            self.logger.debug('Add default devices (device count=%d)' % self._get_device_count())

            # add fake monitor device (used to have a device on dashboard)
            monitor = {
                'type': 'monitor',
                'name': 'System monitor'
            }
            self._add_device(monitor)

            # add monitor cpu device (used to save cpu data into database and has no widget)
            monitor = {
                'type': 'monitorcp',
                'name': 'Cpu monitor'
            }
            self._add_device(monitor)

            # add monitor memory device (used to save cpu data into database and has no widget)
            monitor = {
                'type': 'monitormemory',
                'name': 'Memory monitor'
            }
            self._add_device(monitor)

        # store device uuids for events
        devices = self.get_module_devices()
        for device_uuid in devices:
            if devices[device_uuid]['type'] == 'monitorcp':
                self.__monitor_cpu_uuid = device_uuid
            elif devices[device_uuid]['type'] == 'monitormemory':
                self.__monitor_memory_uuid = device_uuid

    def _on_start(self):
        """
        Application started
        """
        # launch monitoring thread
        self.__start_monitoring_threads()

    def _custom_stop(self):
        """
        Stop module
        """
        # stop monitoring task
        self.__stop_monitoring_threads()

    def __configure_crash_report(self, enable):
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
            self.logger.info('Crash report is disabled')

    def get_module_config(self):
        """
        Return full module configuration

        Returns:
            dict: configuration
        """
        config = self._get_config()

        out = {}
        out['monitoring'] = self.get_monitoring()
        out['uptime'] = self.get_uptime()
        out['needrestart'] = self.__need_restart
        out['needreboot'] = config['needreboot']
        out['crashreport'] = config['crashreport']
        out['version'] = VERSION
        out['eventsnotrendered'] = self.get_events_not_rendered()
        out['debug'] = {
            'system': self.cleep_conf.is_system_debugged(),
            'trace': self.cleep_conf.is_trace_enabled()
        }
        out['cleepbackupdelay'] = self.cleep_backup_delay
        out['latestversion'] = config['latestversion']
        # out['ssl'] = TODO
        # out['rpcport'] = TODO

        return out

    def get_module_devices(self):
        """
        Return system devices

        Returns:
            dict: devices
        """
        devices = super(System, self).get_module_devices()

        for device_uuid in devices:
            if devices[device_uuid]['type'] == 'monitor':
                data = {}
                data['uptime'] = self.get_uptime()
                data['cp'] = self.get_cpu_usage()
                data['memory'] = self.get_memory_usage()
                devices[device_uuid].update(data)

        return devices

    def event_received(self, event):
        """
        Watch for specific event

        Args:
            event (MessageRequest): event data
        """
        # handle restart event
        if event['event'].endswith('system.needrestart'):
            self.__need_restart = True

        # handle reboot event
        elif event['event'].endswith('system.needreboot'):
            self._set_config_field('needreboot', True)

        if event['event'] == 'parameters.time.now':
            # backup configuration
            if not event['params']['minute'] % self.cleep_backup_delay:
                self.backup_cleep_config()

    def set_monitoring(self, monitoring):
        """
        Set monitoring flag

        Params:
            monitoring (bool): monitoring flag
        """
        if monitoring is None:
            raise MissingParameter('Monitoring parameter missing')

        if not self._set_config_field('monitoring', monitoring):
            raise CommandError('Unable to save configuration')

    def get_monitoring(self):
        """
        Return monitoring configuration

        Returns:
            dict: monitoring configuration
        """
        return self._get_config_field('monitoring')

    def reboot_system(self, delay=5.0):
        """
        Reboot system
        """
        # backup configuration
        self.backup_cleep_config()

        # send event
        self.system_system_reboot.send({
            'delay': delay
        })

        # and reboot system
        console = Console()
        console.command_delayed('reboot', delay)

    def halt_system(self, delay=5.0):
        """
        Halt system
        """
        # backup configuration
        self.backup_cleep_config()

        # send event
        self.system_system_halt.send({
            'delay': delay
        })

        # and reboot system
        console = Console()
        console.command_delayed('halt', delay)

    def restart(self, delay=3.0):
        """
        Restart Cleep
        """
        # backup configuration
        self.backup_cleep_config()

        # send event
        self.system_system_restart.send({
            'delay': delay
        })

        # and restart cleep
        console = Console()
        console.command_delayed('/etc/cleep/cleephelper.sh restart', delay)

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
            'total': system.total,
            # 'totalhr': Tools.hr_bytes(system.total),
            'available': system.available,
            'availablehr': Tools.hr_bytes(system.available),
            # 'used_percent': system.percent,
            'cleep': cleep,
            # 'cleephr': Tools.hr_bytes(cleep),
            # 'others': system.total - system.available - cleep
        }

    def get_cpu_usage(self):
        """
        Return system cpu usage

        Returns:
            dict: cpu usage::

                {
                    system (float): system cpu usage percentage
                    cleep (float): cleep cpu usage percentage
                }

        """
        system = psutil.cpu_percent()
        if system > 100.0:
            system = 100.0
        cleep = self.__process.cpu_percent()
        if cleep > 100.0:
            cleep = 100.0
        return {
            'system': system,
            'cleep': cleep
        }

    def get_uptime(self):
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
        return {
            'uptime': uptime,
            'uptimehr': Tools.hr_uptime(uptime)
        }

    def __start_monitoring_threads(self):
        """
        Start monitoring threads
        """
        self.__monitoring_cpu_task = Task(self.MONITORING_CPU_DELAY, self.__monitoring_cpu_thread, self.logger)
        self.__monitoring_cpu_task.start()
        self.__monitoring_memory_task = Task(self.MONITORING_MEMORY_DELAY, self.__monitoring_memory_thread, self.logger)
        self.__monitoring_memory_task.start()
        self.__monitoring_disks_task = Task(self.MONITORING_DISKS_DELAY, self.__monitoring_disks_thread, self.logger)
        self.__monitoring_disks_task.start()

    def __stop_monitoring_threads(self):
        """
        Stop monitoring threads
        """
        if self.__monitoring_cpu_task is not None:
            self.__monitoring_cpu_task.stop()
        if self.__monitoring_memory_task is not None:
            self.__monitoring_memory_task.stop()
        if self.__monitoring_disks_task is not None:
            self.__monitoring_disks_task.stop()

    def __monitoring_cpu_thread(self):
        """
        Read cpu usage
        """
        config = self._get_config()

        # send event if monitoring activated
        if config['monitoring']:
            self.system_monitoring_cpu.send(params=self.get_cpu_usage(), device_id=self.__monitor_cpu_uuid)

    def __monitoring_memory_thread(self):
        """
        Read memory usage
        Send alert if threshold reached
        """
        config = self._get_config()
        memory = self.get_memory_usage()

        # detect memory leak
        percent = (float(memory['total'])-float(memory['available']))/float(memory['total'])*100.0
        if percent >= self.THRESHOLD_MEMORY:
            self.system_alert_memory.send(params={'percent':percent, 'threshold':self.THRESHOLD_MEMORY})

        # send event if monitoring activated
        if config['monitoring']:
            self.system_monitoring_memory.send(params=memory, device_id=self.__monitor_memory_uuid)

    def __monitoring_disks_thread(self):
        """
        Read disks usage
        Only used to send alert when threshold reached
        """
        disks = self.get_filesystem_infos()
        for disk in disks:
            if not disk['mounted']:
                continue

            if disk['mountpoint'] == '/' and disk['percent'] >= self.THRESHOLD_DISK_SYSTEM:
                self.system_alert_disk.send(params={
                    'percent': disk['percent'],
                    'threshold': self.THRESHOLD_DISK_SYSTEM,
                    'mountpoint': disk['mountpoint']
                })

            elif disk['mountpoint'] not in ('/', '/boot') and disk['percent'] >= self.THRESHOLD_DISK_EXTERNAL:
                self.system_alert_disk.send(params={
                    'percent': disk['percent'],
                    'threshold': self.THRESHOLD_DISK_EXTERNAL,
                    'mountpoint': disk['mountpoint']
                })

    def get_filesystem_infos(self):
        """
        Return filesystem infos (all values are in octets)

        Returns:
            list: list of devices available with some informations::
                [
                    {
                        'device': <device path /dev/XXX (string)>
                        'uuid': <device uuid like found in blkid (string)>,
                        'system': <system partition (bool)>,
                        'mountpoint': <mountpoint (string)>
                        'mounted': <partition is mounted (bool)>,
                        'mounttype': <partition type (string)>,
                        'options': <mountpoint options (string)>,
                        'total': <partition total space in octets (number)>,
                        'used': <partition used space in octets (number)>,
                        'free': <partition free space in octets (number)>,
                        'percent': <partition used space in percentage (number)>
                    },
                    ...
                ]
        """
        # get mounted partitions and all devices
        fstab = Fstab(self.cleep_filesystem)
        mounted_partitions = fstab.get_mountpoints()
        self.logger.debug('mounted_partitions=%s' % mounted_partitions)
        all_devices = fstab.get_all_devices()
        self.logger.debug('all_devices=%s' % all_devices)

        # build output
        fsinfos = []
        for device in all_devices:
            # check if partition is mounted
            mounted = {'mounted':False, 'mountpoint':'', 'mounttype':'-', 'options':'', 'uuid':None}
            system = False
            for partition in mounted_partitions:
                if mounted_partitions[partition]['device'] == device:
                    mounted['mounted'] = True
                    mounted['mountpoint'] = mounted_partitions[partition]['mountpoint']
                    mounted['device'] = mounted_partitions[partition]['device']
                    mounted['uuid'] = mounted_partitions[partition]['uuid']
                    mounted['mounttype'] = mounted_partitions[partition]['mounttype']
                    mounted['options'] = mounted_partitions[partition]['options']
                    if mounted_partitions[partition]['mountpoint'] in ('/', '/boot'):
                        system = True

            # get mounted partition usage
            usage = {'total':0, 'used':0, 'free':0, 'percent':0.0}
            if mounted['mounted']:
                sdiskusage = psutil.disk_usage(mounted['mountpoint'])
                self.logger.debug('diskusage for %s: %s' % (device, sdiskusage))
                usage['total'] = sdiskusage.total
                usage['used'] = sdiskusage.used
                usage['free'] = sdiskusage.free
                usage['percent'] = sdiskusage.percent

            # fill infos
            fsinfos.append({
                'device': device,
                'uuid': mounted['uuid'],
                'system': system,
                'mountpoint': mounted['mountpoint'],
                'mounted': mounted['mounted'],
                'mounttype': mounted['mounttype'],
                'options': mounted['options'],
                'total': usage['total'],
                'used': usage['used'],
                'free': usage['free'],
                'percent': usage['percent']
            })

        self.logger.debug('Filesystem infos: %s' % fsinfos)
        return fsinfos

    def download_logs(self):
        """
        Download logs file

        Returns:
            string: script full path

        Raises:
            Exception: if error occured
        """
        if os.path.exists(self.log_file):
            # log file exists

            # zip it
            file_descriptor = NamedTemporaryFile(delete=False)
            log_filename = file_descriptor.name
            self.logger.debug('Zipped log filename: %s' % log_filename)
            archive = ZipFile(file_descriptor, 'w', ZIP_DEFLATED)
            archive.write(self.log_file, 'cleep.log')
            archive.close()

            now = datetime.now()
            filename = 'cleep_%d%02d%02d_%02d%02d%02d.zip' % (now.year, now.month, now.day, now.hour, now.minute, now.second)

            return {
                'filepath': log_filename,
                'filename': filename
            }

        # file doesn't exist, raise exception
        raise Exception('Logs file doesn\'t exist')

    def get_logs(self):
        """
        Return logs file content
        """
        lines = []
        if os.path.exists(self.log_file):
            lines = self.cleep_filesystem.read_data(self.log_file)

        return lines

    def clear_logs(self):
        """
        Clear logs

        Returns:
            bool: True if operation succeed, False otherwise
        """
        if os.path.exists(self.log_file):
            return self.cleep_filesystem.write_data(self.log_file, '')

        return False

    def set_trace(self, trace):
        """
        Set trace (full debug)

        Args:
            trace (bool): enable trace
        """
        if trace is None:
            raise MissingParameter('Parameter "trace" is missing')

        # save log level in conf file
        if trace:
            self.cleep_conf.enable_trace()
        else:
            self.cleep_conf.disable_trace()

        # send event cleep needs to be restarted
        self.__need_restart = True
        self.system_need_restart.send()

    def set_system_debug(self, debug):
        """
        Set debug on all system modules

        Args:
            debug (bool): enable debug
        """
        if debug is None:
            raise MissingParameter('Parameter "debug" is missing')

        if debug:
            self.events_broker.logger.setLevel(logging.DEBUG)
            self.cleep_filesystem.logger.setLevel(logging.DEBUG)

            self.cleep_conf.enable_system_debug()
        else:
            self.events_broker.logger.setLevel(logging.INFO)
            self.cleep_filesystem.logger.setLevel(logging.INFO)

            self.cleep_conf.disable_system_debug()

    def set_module_debug(self, module, debug):
        """
        Set module debug flag

        Args:
            module (string): module name
            debug (bool): enable debug
        """
        if module is None or len(module) == 0:
            raise MissingParameter('Parameter "module" is missing')
        if debug is None:
            raise MissingParameter('Parameter "debug" is missing')

        # save log level in conf file
        if debug:
            self.cleep_conf.enable_module_debug(module)
        else:
            self.cleep_conf.disable_module_debug(module)

        # set debug on module
        if module == 'rpc':
            # specific command for rpcserver
            resp = self.send_command('set_rpc_debug', 'inventory', {'debug':debug})
        else:
            resp = self.send_command('set_debug', module, {'debug':debug})

        # process command response
        if not resp:
            self.logger.error('No response')
            raise CommandError('No response from "%s" module' % module)
        if resp['error']:
            self.logger.error('Unable to set debug on module %s: %s' % (module, resp['message']))
            raise CommandError('Update debug failed')

    def __update_events_not_rendered_in_factory(self):
        """
        Update events factory with list of events to not render
        """
        self.events_broker.update_events_not_rendered(self.get_events_not_rendered())

    def set_event_not_rendered(self, renderer, event, disabled):
        """
        Set event not rendered

        Args:
            renderer (string): renderer name
            event (string): event name
            value (bool): enable/disable value

        Return:
            list: list of events not rendered
        """
        if renderer is None or len(renderer) == 0:
            raise MissingParameter('Renderer parameter is missing')
        if event is None or len(event) == 0:
            raise MissingParameter('Event parameter is missing')
        if disabled is None:
            raise MissingParameter('Disabled parameter is missing')
        if not isinstance(disabled, bool):
            raise InvalidParameter('Disabled parameter is invalid, must be bool')

        events_not_rendered = self._get_config_field('eventsnotrendered')
        key = '%s__%s' % (renderer, event)
        if key in events_not_rendered and not disabled:
            # enable renderer event
            events_not_rendered.remove(key)
        else:
            # disable renderer event
            events_not_rendered.append(key)
        if not self._set_config_field('eventsnotrendered', events_not_rendered):
            raise CommandError('Unable to save configuration')

        # configure events factory with new events to not render
        self.__update_events_not_rendered_in_factory()

        return self.get_events_not_rendered()

    def get_events_not_rendered(self):
        """
        Return list of not rendered events

        Return:
            list: list of events to not render::
                [
                    {
                        event (string): event name,
                        renderer (string): renderer name
                    },
                    ...
                ]
        """
        config = self._get_config()

        # split items to get renderer and event splitted
        events_not_rendered = []
        for item in config['eventsnotrendered']:
            (renderer, event) = item.split('__')
            events_not_rendered.append({
                'renderer': renderer,
                'event': event
            })

        return events_not_rendered

    def set_crash_report(self, enable):
        """
        Enable or disable crash report

        Args:
            enable (bool): True to enable crash report

        Returns:
            bool: True if crash report status updated

        Raises:
            CommandError if error occured
        """
        if enable is None:
            raise MissingParameter('Parameter "enable" is missing')

        # save config
        if not self._set_config_field('crashreport', enable):
            raise CommandError('Unable to save crash report value')

        # configure crash report
        self.__configure_crash_report(enable)

        return True

    def backup_cleep_config(self):
        """
        Backup Cleep configuration files on filesystem

        Returns:
            bool: True if backup successful
        """
        self.logger.debug('Backup Cleep configuration')
        return self.cleep_backup.backup()

    def set_cleep_backup_delay(self, delay):
        """
        Set Cleep backup delay

        Args:
            minute (int): delay in minutes (5..60)
        """
        # check params
        if delay is None:
            raise MissingParameter('Parameter "delay" must be specified')
        if delay < 5 or delay > 60:
            raise MissingParameter('Parameter "delay" must be 0..60')

        res = self._set_config_field('cleepbackupdelay', delay)
        if res:
            self.cleep_backup_delay = delay

        return res

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
            'drivertype': driver_type,
            'drivername': driver_name,
            'installing': False,
            'success': success,
            'message': message,
        }
        self.logger.debug('Driver install terminated: %s' % data)

        # send event
        self.system_driver_install.send(data)

        # reboot device if install succeed
        if success:
            self.reboot_system()

    def install_driver(self, driver_type, driver_name, force=False):
        """
        Install specified driver.
        If install succeed, device will reboot after a delay

        Args:
            driver_type (string): driver type
            driver_name (string): driver name
            force (bool): force install (repair)

        Raises:
            MissingParameter: if a parameter is missing
            InvalidParameter: if driver was not found
            CommandError: if command failed
        """
        # check parameters
        if driver_type is None or len(driver_type) == 0:
            raise MissingParameter('Parameter "driver_type" is missing')
        if driver_name is None or len(driver_name) == 0:
            raise MissingParameter('Parameter "driver_name" is missing')

        # get driver
        driver = self.drivers.get_driver(driver_type, driver_name)
        if not driver:
            raise InvalidParameter('No driver found for specified parameters')

        if not force and driver.is_installed():
            raise CommandError('Driver is already installed')

        # launch installation (non blocking) and send event
        driver.install(self._install_driver_terminated, logger=self.logger)
        self.system_driver_install.send({
            'drivertype': driver_type,
            'drivername': driver_name,
            'installing': True,
            'success': None,
            'message': None,
        })

        return True

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
            'drivertype': driver_type,
            'drivername': driver_name,
            'uninstalling': False,
            'success': success,
            'message': message,
        }
        self.logger.debug('Uninstall driver terminated: %s' % data)

        # send event
        self.system_driver_uninstall.send(data)

        # reboot device if uninstall succeed
        if success:
            self.reboot_system()

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
            CommandError: if command failed
        """
        # check parameters
        if driver_type is None or len(driver_type) == 0:
            raise MissingParameter('Parameter "driver_type" is missing')
        if driver_name is None or len(driver_name) == 0:
            raise MissingParameter('Parameter "driver_name" is missing')

        # get driver
        driver = self.drivers.get_driver(driver_type, driver_name)
        if not driver:
            raise InvalidParameter('No driver found for specified parameters')

        if not driver.is_installed():
            raise CommandError('Driver is not installed')

        # launch uninstallation (non blocking) and send event
        driver.uninstall(self._uninstall_driver_terminated, logger=self.logger)
        self.system_driver_uninstall.send({
            'drivertype': driver_type,
            'drivername': driver_name,
            'uninstalling': True,
            'success': None,
            'message': None,
        })

        return True


