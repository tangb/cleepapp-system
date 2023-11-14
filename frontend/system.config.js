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
        self.debugOptions = [];
        self.debugs = [];
        self.renderings = [];
        self.backupDelays = [
            { value: 5, label: "every 5 minutes" },
            { value: 10, label: "every 10 minutes" },
            { value: 15, label: "every 15 minutes" },
            { value: 30, label: "every 30 minutes" },
            { value: 60, label: "every 60 minutes" },
        ];
        self.codeButtons = [];
        self.logs = '';
        self.editorConfig = {
            lineWrapping: true,
            lineNumbers: true,
            tabSize: 2,
            readOnly: true,
            mode: "cleeplog",
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
        self.updateMonitoring = function(value) {
            systemService.setMonitoring(value)
                .then(() => {
                    cleepService.reloadModuleConfig('system');
                    toast.success('Monitoring updated');
                });
        };

        /**
         * Save tweak LED
         */
        self.updateTweakLed = function(value, meta) {
            if (meta === 'activity') {
                systemService.tweakActivityLed(value)
                    .then(() => {
                        cleepService.reloadModuleConfig('system');
                        toast.success('Activity LED tweaked');
                    });
            } else if (meta === 'power') {
                systemService.tweakPowerLed(value)
                    .then(() => {
                        cleepService.reloadModuleConfig('system');
                        toast.success('Power LED tweaked');
                    });
            }
        };

        /**
         * Save crash report
         */
        self.updateCrashReport = function(value) {
            systemService.setCrashReport(value)
                .then(() => {
                    cleepService.reloadModuleConfig('system');

                    const msg = self.config.crashreport ? 'Crash report enabled' : 'Crash report disabled';
                    toast.success(msg);
                });
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
        self.updateRendering = function(value, current) {
            systemService.setEventRenderable(current.renderer, current.event, !value);
        };

        /**
         * Is event not renderable ?
         * @param renderer: renderer name
         * @param event: event name
         * @return: true if event is not rendered, false otherwise
         */
        self._isEventNotRenderable = function(renderer, event) {
            for (let i=0; i<self.config.eventsnotrenderable.length; i++) {
                if (self.config.eventsnotrenderable[i].renderer === renderer && self.config.eventsnotrenderable[i].event === event) {
                    return true;
                }
            }

            return false;
        };

        /**
         * Search event handled by specified profile
         */
        self._searchProfileEvents = function(profile, events) {
            const matches = [];
            for (const [eventName, event] of Object.entries(events)) {
                for (const profileName of event.profiles) {
                    if (profileName === profile) {
                        matches.push(eventName);
                    }
                }
            }

            return matches;
        }

        /**
         * Init useable renderings list
         * @param events: list of events
         * @param renderers: list of renderers
         */
        self._initRenderings = function(events, renderers) {
            // prepare renderings list
            // for each renderer search handled events via profile matching
            for (const [rendererName, profiles] of Object.entries(renderers)) {
                for(const profile of profiles) {
                    const eventNames = self._searchProfileEvents(profile, events);

                    for (const eventName of eventNames) {
                        const title = 'Disable "' + eventName + '" event handled by "' + rendererName + '" application';
                        self.renderings.push({
                            title,
                            selected: self._isEventNotRenderable(rendererName, eventName),
                            renderer: rendererName,
                            event: eventName,
                        });
                    }
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
                    // self.refreshEditor();
                });
        };

        /**
         * Module debug changed
         */
        self.moduleDebugChanged = function(appDebugs) {
            const requests = [];
            for (const option of self.debugOptions) {
                const app = option.value;
                if (option.debug && !appDebugs.includes(app)) {
                    // app debug disabled
                    requests.push(systemService.setModuleDebug(app, false));
                }

                if (!option.debug && appDebugs.includes(app)) {
                    // app debug enabled
                    requests.push(systemService.setModuleDebug(app, true));
                }
            }
            Promise.allSettled(requests);
        };

        /**
         * Core debug changed
         */
        self.coreDebugChanged = function(value) {
            systemService.setCoreDebug(value);
        };

        /**
         * Trace changed
         */
        self.traceChanged = function(value) {
            systemService.setTrace(value)
                .then(function() {
                    const msg = value ? 'Trace enabled' : 'Trace disabled';
                    toast.success('' + msg +'. Please restart application');
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

                    const apps = Object.keys(resps[2].data).sort();
                    for (const app of apps) {
                        const debug = resps[2].data[app].debug;

                        self.debugOptions.push({
                            label: app,
                            value: app,
                            debug,
                        });
                        if (debug) {
                            self.debugs.push(app);
                        }
                    }
                });

            self.codeButtons = [
                { label: 'Refresh logs', icon: 'refresh', click: self.getLogs },
                { label: 'Download logs', icon: 'download', click: self.downloadLogs },
            ];
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
        controllerAs: '$ctrl',
    };
}]);

