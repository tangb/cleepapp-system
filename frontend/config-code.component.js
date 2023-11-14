/**
 * config-code
 * Display content formatted with codemirror
 * You can add button to interact with code
 *
 * Component example:
 * <config-code cl-title="..." cl-buttons="..."></config-code>
 * With:
 *  - cl-title (string): toolbar title (default empty string)
 *  - cl-buttons (array): list of buttons to display on toolbar right side
 *      {
 *          label: button label,
 *          icon: button icon,
 *          style: button style (md-accent, md-raised...) (default "md-primary md-raised"),
 *          click: button click action,
 *          meta: button meta to pass as click parameters (optional),
 *      }
 *  - cl-config (dict): codemirror configuration. See https://codemirror.net/1/manual.html#configuration
 *  - cl-model (any): content displayed in code editor
 */
angular.module('Cleep').component('configCode', {
    template: `
    <config-base-viewer cl-buttons="$ctrl.clButtons" cl-title="$ctrl.clTitle">
        <div ui-codemirror ui-codemirror-opts="$ctrl.config" ng-model="$ctrl.clModel" class="codemirror-code">
    </config-base-viewer>
    `,
    bindings: {
        clTitle: '@?',
        clButtons: '<?',
        clConfig: '<?',
        clModel: '<',
    },
    controller: function ($rootScope, cleepService, rpcService, confirmService, toastService) {
        const ctrl = this;
        ctrl.config = {};
        ctrl.cmInstance = null;

        ctrl.$onChanges = function (changes) {
            if (changes.clConfig?.currentValue) {
                ctrl.prepareConfig(changes.clConfig.currentValue);
            }
            if (changes.clModel?.currentValue) {
                ctrl.refreshEditor();
            }
        };

        ctrl.prepareConfig = function (config) {
            const customOnLoad = config.onLoad;
            ctrl.config = {
                ...config,
                onLoad: (cmInstance) => {
                    ctrl.cmInstance = cmInstance;
                    cmInstance.focus();
                    (customOnLoad || angular.noop)(cmInstance);
                },
            };
        };

        ctrl.refreshEditor = function () {
            ctrl.cmInstance?.refresh();
        };
    },
});

