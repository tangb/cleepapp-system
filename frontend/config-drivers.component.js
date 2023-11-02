/**
 * Drivers
 * Display a list of available drivers and implements all possible actions.
 * You can display all drivers or filter them by type or name
 *
 * Directive example:
 * <drivers types="'...'" names="'...'" header="'...'"></drivers>
 * With:
 *  - types (string): comma separated list of types to filter on
 *  - names (string): comma separated list of names to filter on
 *  - header (string): header title of list (default "Drivers"). Set empty string to remove header
 */
angular.module('Cleep').component('configDrivers', {
    template: `
    <config-section ng-if="$ctrl.displayHeader" cl-title="{{ $ctrl.title }}" cl-icon="{{ $ctrl.icon }}"></config-section>
    <config-list cl-items="$ctrl.drivers" cl-empty="No driver installed"></config-list>
    `,
    bindings: {
        clTypes: '@?',
        clNames: '@?',
        clTitle: '@?',
        clIcon: '@?',
    },
    controller: function ($rootScope, cleepService, rpcService, confirmService, toastService) {
        const ctrl = this;
        ctrl.title = '';
        ctrl.types = [];
        ctrl.names = [];
        ctrl.drivers = [];
        ctrl.icon = '';
        ctrl.displayHeader = true;

        ctrl.$onInit = function () {
            ctrl.displayHeader = ctrl.clTitle ?? false;
            ctrl.title = ctrl.clTitle ?? 'Drivers';
            ctrl.icon = ctrl.clIcon ?? 'developer-board';
            ctrl.types = ctrl.clTypes?.split(',') || [];
            ctrl.names = ctrl.clNames?.split(',') || [];
        };

        ctrl.setDrivers = function (drivers) {
            if (ctrl.types.length > 0 || ctrl.names.length > 0) {
                drivers = drivers.filter(function(driver) {
                    return !(ctrl.types.indexOf(driver.drivertype) === -1 && ctrl.names.indexOf(driver.drivername) === -1);
                });
            }

            ctrl.drivers.splice(0, ctrl.drivers.length);
            for (const driver of drivers) {
                const loadingStatus = ctrl.getLoadingStatus(driver.processing);
                ctrl.drivers.push({
                    title: driver.drivername,
                    subtitle: loadingStatus,
                    icon: ctrl.getDriverIcon(driver.drivertype),
                    loading: !!loadingStatus,
                    clicks: [
                        {
                            disabled: driver.installed || driver.processing !== 0,
                            click: ctrl.install,
                            icon: 'plus-circle',
                            tooltip: 'Install driver',
                            meta: { driver },
                        },
                        {
                            disabled: !driver.installed || driver.processing !== 0,
                            click: ctrl.uninstall,
                            icon: 'minus-circle',
                            tooltip: 'Uninstall driver',
                            meta: { driver },
                        },
                        {
                            disabled: !driver.installed || driver.processing !== 0,
                            click: ctrl.repair,
                            icon: 'wrench',
                            tooltip: 'Repair driver',
                            meta: { driver },
                        },
                    ],
                });
            }
        };

        ctrl.getLoadingStatus = function (driverProcessing) {
            if (driverProcessing === 1) return 'Installing...';
            if (driverProcessing === 2) return 'Uninstalling...';
            return null;
        };

        ctrl.getDriverIcon = function (driverType) {
            if (driverType === 'audio') return 'volume-high';
            if (driverType === 'video') return 'video-outline';
            if (driverType === 'display') return 'monitor';
            if (driverType === 'electronic') return 'electric-switch';
            if (driverType === 'power') return 'power-plug-outline';
            if (driverType === 'positionning') return 'satellite-variant';
            if (driverType === 'homeautomation') return 'home-automation';
            return 'help-circle-outline';
        };

        ctrl.install = function(driver) {
            const content = 'Confirm "'+driver.drivername+'" driver installation ?<br>Depending on things to install, driver installation may take several minutes.<br><br>After installation device will reboot.';
            confirmService.open('Install driver', content, 'Install', 'Cancel')
                .then(function() {
                    const data = {
                        'driver_type': driver.drivertype,
                        'driver_name': driver.drivername,
                    };
                    rpcService.sendCommand('install_driver', 'system', data);
                });
        };

        ctrl.uninstall = function(driver) {
            const content = 'Confirm "'+driver.drivername+'" driver uninstallation ?<br><strong>Please note after driver uninstallation handled hardware should not work!</strong><br><br>After uninstallation device will reboot.';
            confirmService.open('Uninstall driver', content, 'Uninstall', 'Cancel')
                .then(function() {
                    const data = {
                        'driver_type': driver.drivertype,
                        'driver_name': driver.drivername,
                    };
                    rpcService.sendCommand('uninstall_driver', 'system', data);
                });
        };

        ctrl.repair = function(driver) {
            const content = 'This will reinstall "'+driver.drivername+'" driver. Do you confirm ?<br><br>After reinstall device will reboot.';
            confirmService.open('Repair driver', content, 'Reinstall', 'Cancel')
                .then(function() {
                    const data = {
                        'driver_type': driver.drivertype,
                        'driver_name': driver.drivername,
                        'force': true,
                    };
                    rpcService.sendCommand('install_driver', 'system', data);
                });
        };

        $rootScope.$watchCollection(
            () => cleepService.drivers,
            (newDrivers) => {
                if (newDrivers) {
                    ctrl.setDrivers(newDrivers);
                }
            }
        );

        $rootScope.$on('system.driver.install', function(event, uuid, params) {
            cleepService.reloadDrivers();
            if (params && params.success === true) {
                toastService.success('Driver installed successfully');
            } else if (params && params.success === false) {
                toastService.error('Error installing driver: "' + params.message + '"');
                console.error('Install driver failed:', params.message);
            }
        });

        $rootScope.$on('system.driver.uninstall', function(event, uuid, params) {
            cleepService.reloadDrivers();
            if (params && params.success === true) {
                toastService.success('Driver uninstalled successfully');
            } else if (params && params.success === false) {
                toastService.error('Error uninstalling driver: "' + params.message + '"');
                console.error('Uninstall driver failed:', params.message);
            }
        });
    },
});

