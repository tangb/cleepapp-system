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
from cleep.exception import InvalidParameter, MissingParameter, CommandError, CommandInfo
from cleep.core import CleepModule
from cleep.libs.internals.task import Task
from cleep.libs.internals.console import Console
from cleep.libs.configs.fstab import Fstab
from cleep.libs.configs.cleepconf import CleepConf
from cleep.libs.internals.install import Install
from cleep.libs.internals.installcleep import InstallCleep
from cleep.libs.configs.modulesjson import ModulesJson
import cleep.libs.internals.tools as Tools
from cleep.libs.internals.cleepgithub import CleepGithub
from cleep import __version__ as VERSION
from cleep.libs.internals.cleepbackup import CleepBackup


__all__ = [u'System']


class System(CleepModule):
    """
    Helps controlling the system device (halt, reboot) and monitoring it
    """
    MODULE_AUTHOR = u'Cleep'
    MODULE_VERSION = u'1.1.0'
    MODULE_CATEGORY = u'APPLICATION'
    MODULE_PRICE = 0
    MODULE_DEPS = []
    MODULE_DESCRIPTION = u'Helps updating, controlling and monitoring the device'
    MODULE_LONGDESCRIPTION = u'Application that helps you to configure your system'
    MODULE_TAGS = [u'troubleshoot', u'locale', u'events', u'monitoring', u'update', u'log']
    MODULE_COUNTRY = u''
    MODULE_URLINFO = u'https://github.com/tangb/cleepmod-system'
    MODULE_URLHELP = None
    MODULE_URLBUGS = u'https://github.com/tangb/cleepmod-system/issues'
    MODULE_URLSITE = None

    MODULE_CONFIG_FILE = u'system.conf'

    DEFAULT_CONFIG = {
        u'monitoring': False,
        u'device_uuid': str(uuid.uuid4()),
        u'ssl': False,
        u'auth': False,
        u'rpcport': 80,
        u'eventsnotrendered': [],
        u'crashreport': True,

        u'lastcheckcleep': None,
        u'lastcheckmodules': None,
        u'cleepupdateenabled': False,
        u'modulesupdateenabled': False,
        u'cleepupdateavailable': None,
        u'modulesupdateavailable': False,
        u'lastcleepupdate': {
            u'status': None,
            u'time': 0,
            u'stdout': [],
            u'stderr': []
        },
        u'lastmodulesprocessing' : {},
        u'cleepbackupdelay': 15,
        u'needreboot': False,
        u'latestversion': None,
        u'cleepupdatechangelog': None,
    }

    MONITORING_CPU_DELAY = 60.0 #1 minute
    MONITORING_MEMORY_DELAY = 300.0 #5 minutes
    MONITORING_DISKS_DELAY = 21600 #6 hours

    THRESHOLD_MEMORY = 80.0
    THRESHOLD_DISK_SYSTEM = 80.0
    THRESHOLD_DISK_EXTERNAL = 90.0

    CLEEP_GITHUB_OWNER = u'tangb'
    CLEEP_GITHUB_REPO = u'cleep'

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects
            debug_enabled (bool): flag to set debug level to logger
        """
        CleepModule.__init__(self, bootstrap, debug_enabled)

        # members
        self.events_broker = bootstrap[u'events_broker']
        self.log_file = bootstrap[u'log_file']
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
            u'package': {
                'url': None
            },
            u'checksum': {
                'url': None
            }
        }
        self.cleep_update_pending = False
        self.cleep_backup = CleepBackup(self.cleep_filesystem, self.crash_report)
        self.cleep_backup_delay = None
        self.cleep_conf = CleepConf(self.cleep_filesystem)
        self.drivers = bootstrap[u'drivers']

        # events
        self.system_system_halt = self._get_event(u'system.system.halt')
        self.system_system_reboot = self._get_event(u'system.system.reboot')
        self.system_system_restart = self._get_event(u'system.system.restart')
        self.system_need_restart = self._get_event(u'system.system.needrestart')
        self.system_monitoring_cpu = self._get_event(u'system.monitoring.cpu')
        self.system_monitoring_memory = self._get_event(u'system.monitoring.memory')
        self.system_alert_memory = self._get_event(u'system.alert.memory')
        self.system_alert_disk = self._get_event(u'system.alert.disk')
        self.system_module_install = self._get_event(u'system.module.install')
        self.system_module_uninstall = self._get_event(u'system.module.uninstall')
        self.system_module_update = self._get_event(u'system.module.update')
        self.system_cleep_update = self._get_event(u'system.cleep.update')
        self.system_driver_install = self._get_event(u'system.driver.install')
        self.system_driver_uninstall = self._get_event(u'system.driver.uninstall')

    def _configure(self):
        """
        Configure module
        """
        # set members
        self.cleep_backup_delay = self._get_config_field(u'cleepbackupdelay')

        # configure crash report
        self.__configure_crash_report(self._get_config_field(u'crashreport'))

        # init first cpu percent for current process
        self.__process = psutil.Process(os.getpid())
        self.__process.cpu_percent()

        # add devices if they are not already added
        if self._get_device_count() < 3:
            self.logger.debug(u'Add default devices (device count=%d)' % self._get_device_count())

            # add fake monitor device (used to have a device on dashboard)
            monitor = {
                u'type': u'monitor',
                u'name': u'System monitor'
            }
            self._add_device(monitor)

            # add monitor cpu device (used to save cpu data into database and has no widget)
            monitor = {
                u'type': u'monitorcpu',
                u'name': u'Cpu monitor'
            }
            self._add_device(monitor)

            # add monitor memory device (used to save cpu data into database and has no widget)
            monitor = {
                u'type': u'monitormemory',
                u'name': u'Memory monitor'
            }
            self._add_device(monitor)

        # store device uuids for events
        devices = self.get_module_devices()
        for device_uuid in devices:
            if devices[device_uuid][u'type'] == u'monitorcpu':
                self.__monitor_cpu_uuid = uuid
            elif devices[device_uuid][u'type'] == u'monitormemory':
                self.__monitor_memory_uuid = uuid

        # launch monitoring thread
        self.__start_monitoring_threads()

        # download modules.json file if not exists
        if not self.modules_json.exists():
            self.logger.info(u'Download latest modules.json file from Cleep repository')
            self.modules_json.update()

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
            self.logger.info(u'Crash report is disabled')

    def get_module_config(self):
        """
        Return full module configuration

        Returns:
            dict: configuration
        """
        config = self._get_config()

        out = {}
        out[u'monitoring'] = self.get_monitoring()
        out[u'uptime'] = self.get_uptime()
        out[u'needrestart'] = self.__need_restart
        out[u'needreboot'] = config[u'needreboot']
        out[u'crashreport'] = config[u'crashreport']
        out[u'version'] = VERSION
        out[u'eventsnotrendered'] = self.get_events_not_rendered()
        out[u'debug'] = {
            u'system': self.cleep_conf.is_system_debugged(),
            u'trace': self.cleep_conf.is_trace_enabled()
        }
        out[u'cleepbackupdelay'] = self.cleep_backup_delay
        out[u'latestversion'] = config[u'latestversion']
        # out[u'ssl'] = TODO
        # out[u'rpcport'] = TODO

        # update related values
        out[u'lastcheckcleep'] = config[u'lastcheckcleep']
        out[u'lastcheckmodules'] = config[u'lastcheckmodules']
        out[u'cleepupdateenabled'] = config[u'cleepupdateenabled']
        out[u'modulesupdateenabled'] = config[u'modulesupdateenabled']
        out[u'cleepupdateavailable'] = config[u'cleepupdateavailable']
        out[u'cleepupdatechangelog'] = config[u'cleepupdatechangelog']
        out[u'modulesupdateavailable'] = config[u'modulesupdateavailable']
        out[u'lastcleepupdate'] = config[u'lastcleepupdate']
        out[u'lastmodulesprocessing'] = list(config[u'lastmodulesprocessing'].keys())
        out[u'cleepupdatepending'] = self.cleep_update_pending

        return out

    def get_module_devices(self):
        """
        Return system devices

        Returns:
            dict: devices
        """
        devices = super(System, self).get_module_devices()

        for device_uuid in devices:
            if devices[device_uuid][u'type'] == u'monitor':
                data = {}
                data[u'uptime'] = self.get_uptime()
                data[u'cpu'] = self.get_cpu_usage()
                data[u'memory'] = self.get_memory_usage()
                devices[device_uuid].update(data)

        return devices

    def event_received(self, event):
        """
        Watch for specific event

        Args:
            event (MessageRequest): event data
        """
        # handle restart event
        if event[u'event'].endswith('system.needrestart'):
            self.__need_restart = True

        # handle reboot event
        elif event[u'event'].endswith('system.needreboot'):
            self._set_config_field(u'needreboot', True)

        if event[u'event'] == u'parameters.time.now':
            # update
            if event[u'params'][u'hour'] == 12 and event[u'params'][u'minute'] == 0:
                # check updates at noon
                self.check_cleep_updates()
                self.check_modules_updates()

                # and perform updates if allowed (do not update cleepos and modules at the same time)
                config = self._get_config()
                if config[u'cleepupdateenabled'] is True and self.cleep_update_pending is False and config[u'cleepupdateavailable'] is not None:
                    self.update_cleep()
                elif config[u'modulesupdateenabled'] is True:
                    # TODO update modules that need to be updated
                    pass

            # backup
            if not event[u'params'][u'minute'] % self.cleep_backup_delay:
                self.backup_cleep_config()

    def get_last_module_processing(self, module):
        """
        Return last module processing

        Args:
            module (string): module name

        Returns:
            dict: last module processing::
                {
                    status (int): last processing status (see install lib)
                    process (list): process log messages
                    stdout (list): scripts outputs
                    stderr (list): scripts errors
                    time (int): processing time
                }
        """

        config = self._get_config()
        return config[u'lastmodulesprocessing'][module] if module in config[u'lastmodulesprocessing'] else None

    def set_monitoring(self, monitoring):
        """
        Set monitoring flag

        Params:
            monitoring (bool): monitoring flag
        """
        if monitoring is None:
            raise MissingParameter(u'Monitoring parameter missing')

        if not self._set_config_field(u'monitoring', monitoring):
            raise CommandError(u'Unable to save configuration')

    def get_monitoring(self):
        """
        Return monitoring configuration

        Returns:
            dict: monitoring configuration
        """
        return self._get_config_field(u'monitoring')

    def reboot_system(self, delay=5.0):
        """
        Reboot system
        """
        # backup configuration
        self.backup_cleep_config()

        # send event
        self.system_system_reboot.send({
            u'delay': delay
        })

        # and reboot system
        console = Console()
        console.command_delayed(u'reboot', delay)

    def halt_system(self, delay=5.0):
        """
        Halt system
        """
        # backup configuration
        self.backup_cleep_config()

        # send event
        self.system_system_halt.send({
            u'delay': delay
        })

        # and reboot system
        console = Console()
        console.command_delayed(u'halt', delay)

    def restart(self, delay=3.0):
        """
        Restart Cleep
        """
        # backup configuration
        self.backup_cleep_config()

        # send event
        self.system_system_restart.send({
            u'delay': delay
        })

        # and restart cleep
        console = Console()
        console.command_delayed(u'/etc/cleep/cleephelper.sh restart', delay)

    def __get_module_infos(self, module):
        """
        Return module infos from modules.json file

        Args:
            module (string): module name

        Return:
            dict: module infos
        """
        # get infos from inventory
        resp = self.send_command('get_module_infos', u'inventory', {'module': module})
        if resp[u'error']:
            self.logger.error(u'Unable to get module infos: %s' % resp[u'message'])
            raise CommandError('Unable to install module "%s"' % module)
        if resp['data'] is None:
            self.logger.error(u'Module "%s" not found in modules list' % module)
            raise CommandError(u'Module "%s" not found in installable modules list' % module)

        return resp[u'data']

    def __update_last_module_processing(self, status):
        """
        Update last module processing in config

        Args:
            status (dict): last status as returned by installmodule lib
        """
        # get config
        lastmodulesprocessing = self._get_config_field(u'lastmodulesprocessing')

        # update last module processing
        if status[u'status'] == Install.STATUS_ERROR:
            # save last status when error
            lastmodulesprocessing[status[u'module']] = {
                u'status': status[u'status'],
                u'time': int(time.time()),
                u'stdout': status[u'stdout'],
                u'stderr': status[u'stderr'],
                u'process': status[u'process']
            }

        elif status[u'status'] == Install.STATUS_DONE and status[u'module'] in lastmodulesprocessing:
            # clear existing status when done
            del lastmodulesprocessing[status[u'module']]

        # save config
        self._set_config_field(u'lastmodulesprocessing', lastmodulesprocessing)

    def __module_install_callback(self, status):
        """
        Module install callback

        Args:
            status (dict): process status {stdout (list), stderr (list), status (int), module (string)}
        """
        self.logger.debug(u'Module install callback status: %s' % status)

        # send process status
        self.system_module_install.send(params=status)

        # save last module processing
        self.__update_last_module_processing(status)

        # handle end of process to trigger restart
        if status[u'status'] == Install.STATUS_DONE:
            # need to restart
            self.__need_restart = True

            # update cleep.conf
            self.cleep_conf.install_module(status[u'module'])

        # lock filesystem
        if self.cleep_filesystem:
            self.cleep_filesystem.disable_write(True, True)

    def install_module(self, module):
        """
        Install specified module

        Params:
            module (string): module name to install

        Returns:
            bool: True if module installed
        """
        # check params
        if module is None or len(module) == 0:
            raise MissingParameter(u'Parameter "module" is missing')

        # get module infos
        infos = self.__get_module_infos(module)
        self.logger.debug(u'Module to install infos: %s' % infos)

        # lock filesystem
        if self.cleep_filesystem:
            self.cleep_filesystem.enable_write(True, True)

        # install module dependencies
        for dep in infos[u'deps']:
            self.install_module(dep)

        # launch module installation (non blocking)
        install = Install(self.cleep_filesystem, self.crash_report, self.__module_install_callback)
        install.install_module(module, infos)

        return True

    def __module_uninstall_callback(self, status):
        """
        Module uninstall callback

        Args:
            status (dict): process status {stdout (list), stderr (list), status (int), module (string)}
        """
        self.logger.debug(u'Module uninstall callback status: %s' % status)

        # send process status to ui
        self.system_module_uninstall.send(params=status)

        # save last module processing
        self.__update_last_module_processing(status)

        # handle end of process to trigger restart
        if status[u'status'] == Install.STATUS_DONE:
            self.__need_restart = True

            # update cleep.conf
            self.cleep_conf.uninstall_module(status[u'module'])

        # lock filesystem
        if self.cleep_filesystem:
            self.cleep_filesystem.disable_write(True, True)

    def uninstall_module(self, module, force=False):
        """
        Uninstall specified module

        Params:
            module (string): module name to install
            force (bool): uninstall module and continue if error occured

        Returns:
            bool: True if module uninstalled
        """
        # check params
        if module is None or len(module) == 0:
            raise MissingParameter(u'Parameter "module" is missing')

        # get module infos
        infos = self.__get_module_infos(module)
        self.logger.debug(u'Module to uninstall infos: %s' % infos)

        # unlock filesystem
        if self.cleep_filesystem:
            self.cleep_filesystem.enable_write(True, True)

        # resolve module dependencies
        modules_to_uninstall = self.__dependencies_to_uninstall(module)
        self.logger.debug(u'List of modules supposed to be uninstalled with %s: %s' % (module, modules_to_uninstall))
        for module_to_uninstall in modules_to_uninstall[:]:
            dep_infos = self.__get_module_infos(module_to_uninstall)
            for dependsof in dep_infos[u'dependsof']:
                if dependsof not in modules_to_uninstall:
                    # do not uninstall this module because it has other dependency
                    self.logger.debug(
                        'Do not remove module "%s" which is still needed by "%s" module' % (module_to_uninstall, dependsof)
                    )
                    modules_to_uninstall.remove(module_to_uninstall)
                    break

        # uninstall module + dependencies
        self.logger.info(u'Module %s uninstall will remove %s' % (module, modules_to_uninstall))
        for module_name in modules_to_uninstall:
            install = Install(self.cleep_filesystem, self.crash_report, self.__module_uninstall_callback)
            install.uninstall_module(module_name, infos, force)

        return True

    def __dependencies_to_uninstall(self, dependency):
        deps_to_uninstall = [dependency]

        infos = self.__get_module_infos(dependency)
        for dep in infos[u'deps']:
            deps = self.__dependencies_to_uninstall(dep)
            deps_to_uninstall = list(set(deps) | set(deps_to_uninstall))

        return deps_to_uninstall

    def __module_update_callback(self, status):
        """
        Module update callback

        Args:
            status (dict): process status {stdout (list), stderr (list), status (int), module (string)}
        """
        self.logger.debug(u'Module update callback status: %s' % status)

        # send process status to ui
        self.system_module_update.send(params=status)

        # save last module processing
        self.__update_last_module_processing(status)

        # handle end of process to trigger restart
        if status[u'status'] == Install.STATUS_DONE:
            self.__need_restart = True

            # update cleep.conf adding module to updated ones
            self.cleep_conf.update_module(status[u'module'])

        # lock filesystem
        if self.cleep_filesystem:
            self.cleep_filesystem.disable_write(True, True)

    def update_module(self, module):
        """
        Update specified module

        Params:
            module (string): module name to install

        Returns:
            bool: True if module uninstalled
        """
        # check params
        if module is None or len(module) == 0:
            raise MissingParameter(u'Parameter "module" is missing')

        # get module infos
        infos = self.__get_module_infos(module)
        self.logger.debug(u'Module to update infos: %s' % infos)

        # unlock filesystem
        if self.cleep_filesystem:
            self.cleep_filesystem.enable_write(True, True)

        # update module dependencies
        # TODO handle dependencies updates

        # launch module update
        install = Install(self.cleep_filesystem, self.crash_report, self.__module_update_callback)
        install.update_module(module, infos)

        return True

    def set_automatic_update(self, cleep_update_enabled, modules_update_enabled):
        """
        Set automatic update values

        Args:
            cleep_update_enabled (bool): enable cleep automatic update
            modules_update_enabled (bool): enable modules automatic update
        """
        if not isinstance(cleep_update_enabled, bool):
            raise InvalidParameter('Parameter "cleep_update_enabled" is invalid')
        if not isinstance(modules_update_enabled, bool):
            raise InvalidParameter('Parameter "modules_update_enabled" is invalid')

        return self._update_config({
            u'cleepupdateenabled': cleep_update_enabled,
            u'modulesupdateenabled': modules_update_enabled
        })

    def __get_modules(self):
        """
        Get modules from inventory if necessary

        Return:
            dict: modules dict as returned by inventory
        """
        if len(self.__modules) == 0:
            # retrieve modules from inventory
            resp = self.send_command(u'get_modules', u'inventory')
            if not resp or resp[u'error']:
                raise CommandError(u'Unable to get modules list from inventory')
            self.__modules = resp[u'data']

            # iterate over modules
            modules_to_delete = []
            for module in self.__modules:
                # locked module needs to be removed from list (system module updated by cleep)
                # like not installed modules
                if self.__modules[module][u'core'] or not self.__modules[module][u'installed']:
                    modules_to_delete.append(module)

                # append updatable/updating flags
                self.__modules[module][u'updatable'] = None
                self.__modules[module][u'updating'] = module in self.__updating_modules

            # remove system modules
            for module in modules_to_delete:
                self.__modules.pop(module)

        return self.__modules

    def check_modules_updates(self):
        """
        Check for modules updates.

        Return:
            dict: last update infos::
                {
                    modulesupdateavailable (bool): True if update available
                    lastcheckmodules (int): last modules update check timestamp
                    moduleslistupdated (bool): True if new modules available (it needs to reload all configuration)
                }
        """
        # get modules list from inventory
        modules = self.__get_modules()
        modules_json = self.modules_json.get_json()
        modules_count_before_update = 0
        if modules_json and u'list' in modules_json:
            modules_count_before_update = len(modules_json[u'list'])
        self.logger.debug(u'modules_count_before_update=%s' % modules_count_before_update)

        # update latest modules.json file
        file_updated = False
        try:
            file_updated = self.modules_json.update()
            self.logger.debug(u'file_updated=%s' % file_updated)
        except:
            # invalid modules.json
            self.logger.error(u'Invalid modules.json file downloaded, unable to update modules')
            self.crash_report.manual_report('Invalid modules.json file downloaded')
            raise CommandError(u'Invalid modules file downloaded')

        # check if new modules.json file version available
        modules_list_updated = False
        if file_updated:
            # update modules.json
            modules_json = self.modules_json.get_json()

            # check if modules count changed
            if modules_count_before_update != len(modules_json[u'list']):
                modules_list_updated = True

            # reload modules list in inventory
            self.logger.debug(u'Reloading modules in inventory')
            self.send_command(u'reload_modules', u'inventory', {}, 10.0)

        # check for modules updates available
        update_available = False
        for module in modules:
            try:
                current_version = modules[module][u'version']
                if module in modules_json[u'list']:
                    new_version = modules_json[u'list'][module][u'version']
                    if Tools.compare_versions(current_version, new_version):
                        # new version available for current module
                        self.logger.info(
                            'New version available for module "%s" (%s->%s)' % (module, current_version, new_version)
                        )
                        modules[module][u'updatable'] = True
                        update_available = True

                    else:
                        self.logger.debug(
                            'No new version available for module "%s" (%s->%s)' % (module, current_version, new_version)
                        )
            except Exception:
                self.logger.exception(u'Invalid "%s" module description in modules.json' % module)

        # update config
        config = {
            u'modulesupdateavailable': update_available,
            u'lastcheckmodules': int(time.time())
        }
        self._update_config(config)

        return {
            u'modulesupdateavailable': update_available,
            u'moduleslistupdated': modules_list_updated,
            u'lastcheckmodules': config[u'lastcheckmodules']
        }

    def check_cleep_updates(self):
        """
        Check for available cleep updates

        Returns:
            dict: last update infos::

                {
                    cleepupdateavailable (string): available version, None if no update available
                    cleepupdatechangelog (string): update changelog if new version available
                    lastcheckcleep (int): last cleep update check timestamp
                }

        """
        # init
        update_available = None
        update_changelog = u''
        self.__cleep_update[u'package'] = None
        self.__cleep_update[u'checksum'] = None

        try:
            # get beta release if GITHUB_TOKEN env variable registered
            github_token = None
            only_released = True
            if u'GITHUB_TOKEN' in os.environ:
                github_token = os.environ[u'GITHUB_TOKEN']
                only_released = False # used to get beta release

            github = CleepGithub(github_token)
            releases = github.get_releases(
                self.CLEEP_GITHUB_OWNER,
                self.CLEEP_GITHUB_REPO,
                only_latest=True,
                only_released=only_released
            )
            if len(releases) == 1:
                # get latest version available
                version = github.get_release_version(releases[0])
                self._set_config_field('latestversion', version)
                update_changelog = github.get_release_changelog(releases[0])
                self.logger.debug(u'Update changelog: %s' % update_changelog)

                self.logger.info('Cleep version status: %s(latest) - %s(installed)' % (version, VERSION))
                if version != VERSION:
                    # new version available, trigger update
                    assets = github.get_release_assets_infos(releases[0])

                    # search for deb file
                    for asset in assets:
                        if asset[u'name'].startswith(u'cleep_') and asset[u'name'].endswith('.zip'):
                            self.logger.debug(u'Found Cleep package asset: %s' % asset)
                            self.__cleep_update[u'package'] = asset
                            break

                    # search for checksum file
                    if self.__cleep_update[u'package'] is not None:
                        package_name = os.path.splitext(self.__cleep_update[u'package'][u'name'])[0]
                        checksum_name = u'%s.%s' % (package_name, u'sha256')
                        self.logger.debug(u'Checksum filename to search: %s' % checksum_name)
                        for asset in assets:
                            if asset[u'name'] == checksum_name:
                                self.logger.debug(u'Found checksum asset: %s' % asset)
                                self.__cleep_update[u'checksum'] = asset
                                break

                    if self.__cleep_update[u'package'] and self.__cleep_update[u'checksum']:
                        self.logger.info(u'Archive and checksum files found, can trigger update')
                        self.logger.debug(u'cleep_update: %s' % self.__cleep_update)
                        update_available = version

                else:
                    # already up-to-date
                    update_changelog = u''

            else:
                # no release found
                self.logger.warning(u'No release found during check')

        except:
            self.logger.exception(u'Error occured during updates checking:')
            self.crash_report.report_exception()
            raise Exception(u'Error occured during cleep update check')

        # update config
        config = {
            u'cleepupdateavailable': update_available,
            u'cleepupdatechangelog': update_changelog,
            u'lastcheckcleep': int(time.time())
        }
        self._update_config(config)

        return config

    def __update_cleep_callback(self, status):
        """
        Cleep update callback

        Args:
            status (dict): update status
        """
        self.logger.debug(u'Cleep update callback status: %s' % status)

        # send process status (only status)
        self.system_cleep_update.send(params={u'status':status[u'status']})

        # save final status when update terminated (successfully or not)
        if status[u'status'] >= InstallCleep.STATUS_UPDATED:
            self.logger.debug(u'Store update result in config file')
            stdout = []
            stderr = []

            # prescript
            try:
                if status[u'prescript'][u'returncode'] is not None:
                    stdout += [u'Pre-script output:']
                    if len(status[u'prescript'][u'stdout']) > 0:
                        stdout += [u' '*4 + line for line in status[u'prescript'][u'stdout']]
                    else:
                        stdout += [u' '*4 + u'No output']
                    stdout += [u'', u'Pre-script return code: %s' % status[u'prescript'][u'returncode']]
                    stderr += [u'Pre-script errors']
                    if len(status[u'prescript'][u'stderr']) > 0:
                        stderr += [u' '*4 + line for line in status[u'prescript'][u'stderr']]
                    else:
                        stderr += [u' '*4 + u'No error']
                else:
                    stdout += [u'No pre-script found']
            except Exception:
                self.logger.exception(u'Error saving prescript output:')
                self.crash_report.report_exception()

            # deb
            try:
                if status[u'deb'][u'returncode'] is not None:
                    stdout += [u'', u'Package output:']
                    if len(status[u'deb'][u'stdout']) > 0:
                        stdout += [u' '*4 + line for line in status[u'deb'][u'stdout']]
                    else:
                        stdout += [u' '*4 + u'No output']
                    stdout += [u'', u'Package return code: %s' % status[u'deb'][u'returncode']]
                    # stderr merge to stdout because dpkg and pip put some info on stderr
                else:
                    stdout += [u'', u'No package found']
            except Exception:
                self.logger.exception(u'Error saving deb output:')
                self.crash_report.report_exception()

            # postscript
            try:
                if status[u'postscript'][u'returncode'] is not None:
                    stdout += [u'', u'Post-script output:']
                    if len(status[u'postscript'][u'stdout']) > 0:
                        stdout += [u' '*4 + line for line in status[u'postscript'][u'stdout']]
                    else:
                        stdout += [u' '*4 + u'No output']
                    stdout += [u'', u'Post-script return code: %s' % status[u'postscript'][u'returncode']]
                    stderr += [u'', u'Post-script errors:']
                    if len(status[u'postscript'][u'stderr']) > 0:
                        stderr += [u' '*4 + line for line in status[u'postscript'][u'stderr']]
                    else:
                        stderr += [u' '*4 + u'No error']
                else:
                    stdout += [u'', u'No post-script found']
            except Exception:
                self.logger.exception(u'Error saving postscript output:')
                self.crash_report.report_exception()

            # save update status
            self._update_config({
                u'cleepupdateavailable': None,
                u'lastcleepupdate': {
                    u'status': status[u'status'],
                    u'time': int(time.time()),
                    u'stdout': stdout,
                    u'stderr': stderr
                }
            })

            # lock filesystem
            if self.cleep_filesystem:
                self.cleep_filesystem.disable_write(True, True)

        # handle end of successful process to trigger restart
        if status[u'status'] == InstallCleep.STATUS_UPDATED:
            # need to restart
            self.restart(delay=1.0)

    def update_cleep(self):
        """
        Update Cleep
        """
        # check params
        if not self.__cleep_update[u'package'] or not self.__cleep_update[u'checksum']:
            # user trigger cleep update and there is no update infos. Check again
            self.logger.debug('Cleep update trigger while there is no update infos, check again')
            res = self.check_cleep_updates()
            if not res[u'cleepupdateavailable']:
                # there is really no update available
                raise CommandInfo(u'No cleep update available')
            self.logger.debug('Finally an update is available, process it')

        # unlock filesystem
        if self.cleep_filesystem:
            self.cleep_filesystem.enable_write(True, True)

        # launch install
        package_url = self.__cleep_update[u'package'][u'url']
        checksum_url = self.__cleep_update[u'checksum'][u'url']
        self.logger.trace(u'Update Cleep: package_url=%s checksum_url=%s' % (package_url, checksum_url))
        update = InstallCleep(package_url, checksum_url, self.__update_cleep_callback, self.cleep_filesystem, self.crash_report)
        update.start()

        return True

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
            u'total': system.total,
            # u'totalhr': Tools.hr_bytes(system.total),
            u'available': system.available,
            u'availablehr': Tools.hr_bytes(system.available),
            # u'used_percent': system.percent,
            u'cleep': cleep,
            # u'cleephr': Tools.hr_bytes(cleep),
            # u'others': system.total - system.available - cleep
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
            u'system': system,
            u'cleep': cleep
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
            u'uptime': uptime,
            u'uptimehr': Tools.hr_uptime(uptime)
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
        if config[u'monitoring']:
            self.system_monitoring_cpu.send(params=self.get_cpu_usage(), device_id=self.__monitor_cpu_uuid)

    def __monitoring_memory_thread(self):
        """
        Read memory usage
        Send alert if threshold reached
        """
        config = self._get_config()
        memory = self.get_memory_usage()

        # detect memory leak
        percent = (float(memory[u'total'])-float(memory[u'available']))/float(memory[u'total'])*100.0
        if percent >= self.THRESHOLD_MEMORY:
            self.system_alert_memory.send(params={u'percent':percent, u'threshold':self.THRESHOLD_MEMORY})

        # send event if monitoring activated
        if config[u'monitoring']:
            self.system_monitoring_memory.send(params=memory, device_id=self.__monitor_memory_uuid)

    def __monitoring_disks_thread(self):
        """
        Read disks usage
        Only used to send alert when threshold reached
        """
        disks = self.get_filesystem_infos()
        for disk in disks:
            if not disk[u'mounted']:
                continue

            if disk[u'mountpoint'] == u'/' and disk[u'percent'] >= self.THRESHOLD_DISK_SYSTEM:
                self.system_alert_disk.send(
                    params={u'percent':disk[u'percent'], u'threshold':self.THRESHOLD_DISK_SYSTEM, u'mountpoint':disk[u'mountpoint']}
                )

            elif disk[u'mountpoint'] not in (u'/', u'/boot') and disk[u'percent'] >= self.THRESHOLD_DISK_EXTERNAL:
                self.system_alert_disk.send(
                    params={u'percent':disk[u'percent'], u'threshold':self.THRESHOLD_DISK_EXTERNAL, u'mountpoint':disk[u'mountpoint']}
                )

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
        self.logger.debug(u'mounted_partitions=%s' % mounted_partitions)
        all_devices = fstab.get_all_devices()
        self.logger.debug(u'all_devices=%s' % all_devices)

        # build output
        fsinfos = []
        for device in all_devices:
            # check if partition is mounted
            mounted = {u'mounted':False, u'mountpoint':u'', u'mounttype':'-', u'options':'', u'uuid':None}
            system = False
            for partition in mounted_partitions:
                if mounted_partitions[partition][u'device'] == device:
                    mounted[u'mounted'] = True
                    mounted[u'mountpoint'] = mounted_partitions[partition][u'mountpoint']
                    mounted[u'device'] = mounted_partitions[partition][u'device']
                    mounted[u'uuid'] = mounted_partitions[partition][u'uuid']
                    mounted[u'mounttype'] = mounted_partitions[partition][u'mounttype']
                    mounted[u'options'] = mounted_partitions[partition][u'options']
                    if mounted_partitions[partition][u'mountpoint'] in (u'/', u'/boot'):
                        system = True

            # get mounted partition usage
            usage = {u'total':0, u'used':0, u'free':0, u'percent':0.0}
            if mounted[u'mounted']:
                sdiskusage = psutil.disk_usage(mounted[u'mountpoint'])
                self.logger.debug(u'diskusage for %s: %s' % (device, sdiskusage))
                usage[u'total'] = sdiskusage.total
                usage[u'used'] = sdiskusage.used
                usage[u'free'] = sdiskusage.free
                usage[u'percent'] = sdiskusage.percent

            # fill infos
            fsinfos.append({
                u'device': device,
                u'uuid': mounted[u'uuid'],
                u'system': system,
                u'mountpoint': mounted[u'mountpoint'],
                u'mounted': mounted[u'mounted'],
                u'mounttype': mounted[u'mounttype'],
                u'options': mounted[u'options'],
                u'total': usage[u'total'],
                u'used': usage[u'used'],
                u'free': usage[u'free'],
                u'percent': usage[u'percent']
            })

        self.logger.debug(u'Filesystem infos: %s' % fsinfos)
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
            self.logger.debug(u'Zipped log filename: %s' % log_filename)
            archive = ZipFile(file_descriptor, u'w', ZIP_DEFLATED)
            archive.write(self.log_file, u'cleep.log')
            archive.close()

            now = datetime.now()
            filename = u'cleep_%d%02d%02d_%02d%02d%02d.zip' % (now.year, now.month, now.day, now.hour, now.minute, now.second)

            return {
                u'filepath': log_filename,
                u'filename': filename
            }

        # file doesn't exist, raise exception
        raise Exception(u'Logs file doesn\'t exist')

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
            return self.cleep_filesystem.write_data(self.log_file, u'')

        return False

    def set_trace(self, trace):
        """
        Set trace (full debug)

        Args:
            trace (bool): enable trace
        """
        if trace is None:
            raise MissingParameter(u'Parameter "trace" is missing')

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
            raise MissingParameter(u'Parameter "debug" is missing')

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
            raise MissingParameter(u'Parameter "module" is missing')
        if debug is None:
            raise MissingParameter(u'Parameter "debug" is missing')

        # save log level in conf file
        if debug:
            self.cleep_conf.enable_module_debug(module)
        else:
            self.cleep_conf.disable_module_debug(module)

        # set debug on module
        if module == u'rpc':
            # specific command for rpcserver
            resp = self.send_command(u'set_rpc_debug', u'inventory', {u'debug':debug})
        else:
            resp = self.send_command(u'set_debug', module, {u'debug':debug})

        # process command response
        if not resp:
            self.logger.error(u'No response')
            raise CommandError(u'No response from "%s" module' % module)
        if resp[u'error']:
            self.logger.error(u'Unable to set debug on module %s: %s' % (module, resp[u'message']))
            raise CommandError(u'Update debug failed')

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
            raise MissingParameter(u'Renderer parameter is missing')
        if event is None or len(event) == 0:
            raise MissingParameter(u'Event parameter is missing')
        if disabled is None:
            raise MissingParameter(u'Disabled parameter is missing')
        if not isinstance(disabled, bool):
            raise InvalidParameter(u'Disabled parameter is invalid, must be bool')

        events_not_rendered = self._get_config_field(u'eventsnotrendered')
        key = '%s__%s' % (renderer, event)
        if key in events_not_rendered and not disabled:
            # enable renderer event
            events_not_rendered.remove(key)
        else:
            # disable renderer event
            events_not_rendered.append(key)
        if not self._set_config_field(u'eventsnotrendered', events_not_rendered):
            raise CommandError(u'Unable to save configuration')

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
        for item in config[u'eventsnotrendered']:
            (renderer, event) = item.split(u'__')
            events_not_rendered.append({
                u'renderer': renderer,
                u'event': event
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
            raise MissingParameter(u'Parameter "enable" is missing')

        # save config
        if not self._set_config_field(u'crashreport', enable):
            raise CommandError(u'Unable to save crash report value')

        # configure crash report
        self.__configure_crash_report(enable)

        return True

    def backup_cleep_config(self):
        """
        Backup Cleep configuration files on filesystem

        Returns:
            bool: True if backup successful
        """
        self.logger.debug(u'Backup Cleep configuration')
        return self.cleep_backup.backup()

    def set_cleep_backup_delay(self, delay):
        """
        Set Cleep backup delay

        Args:
            minute (int): delay in minutes (5..60)
        """
        # check params
        if delay is None:
            raise MissingParameter(u'Parameter "delay" must be specified')
        if delay < 5 or delay > 60:
            raise MissingParameter(u'Parameter "delay" must be 0..60')

        res = self._set_config_field(u'cleepbackupdelay', delay)
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
            u'drivertype': driver_type,
            u'drivername': driver_name,
            u'installing': False,
            u'success': success,
            u'message': message,
        }
        self.logger.debug(u'Driver install terminated: %s' % data)

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
            raise MissingParameter(u'Parameter "driver_type" is missing')
        if driver_name is None or len(driver_name) == 0:
            raise MissingParameter(u'Parameter "driver_name" is missing')

        # get driver
        driver = self.drivers.get_driver(driver_type, driver_name)
        if not driver:
            raise InvalidParameter(u'No driver found for specified parameters')

        if not force and driver.is_installed():
            raise CommandError(u'Driver is already installed')

        # launch installation (non blocking) and send event
        driver.install(self._install_driver_terminated, logger=self.logger)
        self.system_driver_install.send({
            u'drivertype': driver_type,
            u'drivername': driver_name,
            u'installing': True,
            u'success': None,
            u'message': None,
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
            u'drivertype': driver_type,
            u'drivername': driver_name,
            u'uninstalling': False,
            u'success': success,
            u'message': message,
        }
        self.logger.debug(u'Uninstall driver terminated: %s' % data)

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
            raise MissingParameter(u'Parameter "driver_type" is missing')
        if driver_name is None or len(driver_name) == 0:
            raise MissingParameter(u'Parameter "driver_name" is missing')

        # get driver
        driver = self.drivers.get_driver(driver_type, driver_name)
        if not driver:
            raise InvalidParameter(u'No driver found for specified parameters')

        if not driver.is_installed():
            raise CommandError(u'Driver is not installed')

        # launch uninstallation (non blocking) and send event
        driver.uninstall(self._uninstall_driver_terminated, logger=self.logger)
        self.system_driver_uninstall.send({
            u'drivertype': driver_type,
            u'drivername': driver_name,
            u'uninstalling': True,
            u'success': None,
            u'message': None,
        })

        return True


