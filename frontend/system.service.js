/**
 * System service
 * Handle system module requests
 */
angular
.module('Cleep')
.service('systemService', ['$rootScope', 'rpcService', 'cleepService', 'toastService', 'appToolbarService',
function($rootScope, rpcService, cleepService, toast, appToolbarService) {
    var self = this;
    self.restartButtonId = null;
    self.rebootButtonId = null;
    self.monitoring = false;
    
    /**
     * Get filesystem infos
     */
    self.getFilesystemInfos = function() {
        return rpcService.sendCommand('get_filesystem_infos', 'system', 30000);
    };

    /**
     * Set monitoring
     */
    self.setMonitoring = function(monitoring) {
        return rpcService.sendCommand('set_monitoring', 'system', {'monitoring': monitoring});
    };

    /**
     * Reboot device
     */
    self.reboot = function() {
        return rpcService.sendCommand('reboot_device', 'system');
    };

    /**
     * Poweroff device 
     */
    self.poweroff = function() {
        return rpcService.sendCommand('poweroff_device', 'system');
    };

    /**
     * Restart cleep
     */
    self.restart = function() {
        return rpcService.sendCommand('restart_cleep', 'system');
    };

    /**
     * Download logs
     */
    self.downloadLogs = function() {
        rpcService.download('download_logs', 'system');
    };

    /**
     * Get logs
     */
    self.getLogs = function() {
        return rpcService.sendCommand('get_logs', 'system');
    };

    /**
     * Clear logs
     */
    self.clearLogs = function() {
        return rpcService.sendCommand('clear_logs', 'system');
    };

    /**
     * Set module debug
     */
    self.setModuleDebug = function(module, debug) {
        return rpcService.sendCommand('set_module_debug', 'system', {'module_name':module, 'debug':debug});
    };

    /**
     * Set core debug
     */
    self.setCoreDebug = function(debug) {
        return rpcService.sendCommand('set_core_debug', 'system', {'debug':debug});
    };

    /**
     * Set trace
     */
    self.setTrace = function(trace) {
        return rpcService.sendCommand('set_trace', 'system', {'trace':trace})
            .then(function() {
                return cleepService.reloadModuleConfig('system');
            });
    };

    /**
     * Set hostname
     */
    self.setHostname = function(hostname) {
        return rpcService.sendCommand('set_hostname', 'system', {'hostname':hostname});
    };

    /**
     * Set event not rendered
     */
    self.setEventNotRendered = function(renderer, event, disabled) {
        return rpcService.sendCommand('set_event_not_rendered', 'system', {'renderer':renderer, 'event':event, 'disabled':disabled})
            .then(function(resp) {
                // overwrite system event_not_rendered config value
                cleepService.modules.system.config.eventsnotrendered = resp.data;
            });
    };

    /**
     * Enable/disable crash report
     */
    self.setCrashReport = function(enable) {
        return rpcService.sendCommand('set_crash_report', 'system', {'enable':enable});
    };

    /**
     * Set backup update time
     */
    self.setCleepBackupDelay = function(delay) {
        return rpcService.sendCommand('set_cleep_backup_delay', 'system', {'delay': delay});
    };

    /**
     * Make backup of cleep configuration files
     */
    self.backupCleepConfig = function() {
        return rpcService.sendCommand('backup_cleep_config', 'system', {});
    };

    /**
     * Watch for system config changes to add restart/reboot buttons if restart/reboot is needed
     */
    $rootScope.$watchCollection(
        function() {
            return cleepService.modules['system'];
        },
        function(newConfig) {
            if( newConfig && newConfig.config ) {
                // handle restart button
                if( !newConfig.config.needrestart && self.restartButtonId ) {
                    appToolbarService.removeButton(self.restartButtonId);
                    self.restartButtonId = null;
                } else if( newConfig.config.needrestart && !self.restartButtonId ) {
                    self.restartButtonId = appToolbarService.addButton('Restart to apply changes', 'restart', cleepService.restart, 'md-accent');
                }

                // handle reboot button
                if( !newConfig.config.needreboot && self.rebootButtonId ) {
                    appToolbarService.removeButton(self.rebootButtonId);
                    self.rebootButtonId = null;
                } else if( newConfig.config.needreboot && !self.rebootButtonId ) {
                    self.rebootButtonId = appToolbarService.addButton('Reboot to apply changes', 'restart', cleepService.reboot, 'md-accent');
                }

                // store monitoring flag to display or not monitor widget
                self.monitoring = newConfig.config.monitoring;
            }
        }
    );

    /**
     * Catch cpu monitoring event
     */
    $rootScope.$on('system.monitoring.cpu', function(event, uuid, params) {
        for( var i=0; i<cleepService.devices.length; i++ ) {
            if( cleepService.devices[i].type==='monitor' ) {
                cleepService.devices[i].cpu = params;
                break;
            }
        }
    });

    /**
     * Catch memory monitoring event
     */
    $rootScope.$on('system.monitoring.memory', function(event, uuid, params) {
        for( var i=0; i<cleepService.devices.length; i++ ) {
            if( cleepService.devices[i].type==='monitor' ) {
                cleepService.devices[i].memory = params;
                break;
            }
        }
    });

}]);
