/**
 * System config component
 * Handle system configuration
 */
angular
.module('Cleep')
.directive('systemConfigComponent', ['$rootScope', '$timeout', '$q', 'toastService', 'systemService', 'cleepService', 'confirmService', '$location',
function($rootScope, $timeout, $q, toast, systemService, cleepService, confirm, $location) {
    var systemController = ['$scope', function($scope) {
        var self = this;
        self.config = {};
        self.systemService = systemService;
        self.tabIndex = 'drivers';
        self.needRestart = false;
        self.debugs = {};
        self.renderings = [];

        self.codemirrorInstance = null;
        self.codemirrorOptions = {
            lineWrapping: true,
            lineNumbers: true,
            tabSize: 2,
            readOnly: true,
            mode: "cleeplog",
            onLoad: function(cmInstance) {
                self.codemirrorInstance = cmInstance;
                cmInstance.focus();
            }
        };

        /**************
         * Backup tab
         **************/

        /**
         * Trigger configuration backup
         */
        self.backupConfiguration = function() {
            systemService.backupCleepConfig()
                .then(function() {
                    cleepService.reloadModuleConfig('system');
                    toast.success('Configuration backuped');
                });
        };

        /**
         * Set backup config delay
         */
        self.setBackupDelay = function() {
            systemService.setCleepBackupDelay(Number(self.config.cleepbackupdelay))
                .then(function() {
                    cleepService.reloadModuleConfig('system');
                    toast.success('Delay saved');
                });
        };

        /**
         * Set filesystem protection
         */
        self.setFilesystemProtection = function() {
            //TODO
        };

        /**************
         * Advanced tab
         **************/

        /**
         * Save monitoring
         */
        self.updateMonitoring = function(fromCheckbox) {
            if( !fromCheckbox ) {
                // row clicked, we need to update flag
                self.config.monitoring = !self.config.monitoring;
            }

            // delay update to make sure model value is updated
            systemService.setMonitoring(self.config.monitoring)
                .then(function(resp) {
                    cleepService.reloadModuleConfig('system');
                    toast.success('Monitoring updated');
                });
        };

        /**
         * Save crash report
         */
        self.updateCrashReport = function(fromCheckbox) {
            if( !fromCheckbox ) {
                // row clicked, we need to update flag
                self.config.crashreport = !self.config.crashreport;
            }

            //delay update to make sure model value is updated
            $timeout(function() {
                systemService.setCrashReport(self.config.crashreport)
                    .then(function(resp) {
                        cleepService.reloadModuleConfig('system');

                        // user message
                        if( self.config.crashreport ) {
                            toast.success('Crash report enabled');
                        } else {
                            toast.success('Crash report disabled');
                        }
                    });
            }, 250);
        };


        /**
         * Reboot device
         */
        self.reboot = function() {
            confirm.open('Confirm device reboot?', null, 'Reboot device')
                .then(function() {
                    return systemService.reboot();
                })
                .then(function() {
                    toast.success('Device will reboot in few seconds');
                });
        };

        /**
         * Poweroff device
         */
        self.poweroff = function() {
            confirm.open('Confirm device shutdown?', null, 'Poweroff device')
                .then(function() {
                    systemService.poweroff();
                })
                .then(function() {
                    toast.success('Device will shutdown in few seconds');
                });
        };

        /**
         * Restart cleep
         */
        self.restart = function() {
            confirm.open('Confirm application restart?', null, 'Restart Cleep')
                .then(function() {
                    systemService.restart();
                })
                .then(function() {
                    toast.success('Cleep will restart in few seconds');
                });
        };

        
        /************
         * Renderings
         ************/

        /**
         * Update renderings
         */
        self.updateRendering = function(rendering) {
            systemService.setEventRenderable(rendering.renderer, rendering.event, !rendering.disabled);
        };

        /**
         * Is event not renderable ?
         * @param renderer: renderer name
         * @param event: event name
         * @return: true if event is not rendered, false otherwise
         */
        self._isEventNotRenderable = function(renderer, event) {
            for (var i=0; i<self.config.eventsnotrenderable.length; i++) {
                if (self.config.eventsnotrenderable[i].renderer === renderer && self.config.eventsnotrenderable[i].event === event) {
                    return true;
                }
            }

            return false;
        };

        /**
         * Search event handled by specified profile
         */
        self._searchProfileEvent = function(profile, events) {
            for (var eventName in events) {
                for (var profileName in events[eventName].profiles) {
                    if (profileName === profile) {
                        return eventName;
                    }
                }
            }

            return null;
        }

        /**
         * Init useable renderings list
         * @param events: list of events
         * @param renderers: list of renderers
         */
        self._initRenderings = function(events, renderers) {
            // prepare renderings list
            // for each renderer search handled events via profile matching
            for(var renderer in renderers) {
                for(var profile in renderers[renderer]) {
                    var eventName = self._searchProfileEvent(profile, events);
                    if(!eventName) {
                        console.warn('Profile "'+profile+'" has no event!');
                        continue;
                    }

                    self.renderings.push({
                        'renderer': renderer,
                        'event': eventName,
                        'disabled': self._isEventNotRenderable(renderer, eventName),
                    });
                }
            }
        };

        /******************
         * Troubleshoot tab
         ******************/

        /**
         * Download logs
         */
        self.downloadLogs = function() {
            systemService.downloadLogs();
        };

        /**
         * Get logs
         */
        self.getLogs = function() {
            systemService.getLogs()
                .then(function(resp) {
                    self.logs = resp.data.join('');
                    self.refreshEditor();
                });
        };

        /**
         * Refresh editor
         */
        self.refreshEditor = function() {
            self.codemirrorInstance.refresh();
        };

        /**
         * Module debug changed
         */
        self.moduleDebugChanged = function(module) {
            systemService.setModuleDebug(module, self.debugs[module].debug);
        };

        /**
         * Core debug changed
         */
        self.coreDebugChanged = function() {
            $timeout(function() {
                systemService.setCoreDebug(self.config.debug.core);
            }, 250);
        };

        /**
         * Trace changed
         */
        self.traceChanged = function() {
            systemService.setTrace(self.config.debug.trace)
                .then(function() {
                    var message = 'Trace enabled';
                    if( !self.config.debug.trace )
                        message = 'Trace disabled';
                        
                    toast.success('' + message +'. Please restart application');
                });
        };

        /**
         * Init controller
         */
        self.$onInit = function() {
            // get preselected tab index
            if( $location.search().tab ) {
                self.tabIndex = $location.search().tab;
            }

            // load all needed stuff
            $q.all([cleepService.getEvents(), cleepService.getRenderers(), cleepService.getModulesDebug()])
                .then(function(resps) {
                    self._initRenderings(resps[0], resps[1]);
                    self.debugs = resps[2].data;
                });
        };

        /** 
         * Watch configuration changes
         */
        $rootScope.$watch(
            function() {
                return cleepService.modules['system'].config;
            },  
            function(newVal, oldVal) {
                if( newVal && Object.keys(newVal).length ) { 
                    Object.assign(self.config, newVal);
                }   
            }   
        );

    }];

    return {
        templateUrl: 'system.config.html',
        replace: true,
        scope: true,
        controller: systemController,
        controllerAs: 'systemCtl',
    };
}]);

