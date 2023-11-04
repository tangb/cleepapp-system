# cleepmod-system [![Coverage Status](https://coveralls.io/repos/github/tangb/cleepapp-system/badge.svg?branch=master)](https://coveralls.io/github/tangb/cleepapp-system?branch=master)

![system](https://github.com/CleepDevice/cleepapp-system/raw/master/resources/system.jpg)

System application for Cleep.

This application groups some useful features to manage your device.

## Drivers panel

This panel displays all installed drivers. It offers possibility to reinstall driver in case of problem.

You can also uninstall them (without uninstalling the driver application)

## Backup panel

SD-card is the weakness of the raspberry. To reduce SD-card corruption, Cleep runs by default on a read-only filesystem.
All configuration is stored in versatile memory and cleared each time device restarts.

The backup feature writes data on SD-card after some delay and allows you to trigger manually a backup.

## Renderings panel

This panel displays all events with associated renderers and gives you a way to disable it.

It is useful when you install a renderer and a service and you don't want to render service event on the renderer.
For example you installed a screen app and a weather service app and you don't want to render weather data on the screen.
 
## Advanced options panel

Options in this panel allows you to restart or poweroff properly the device.
Properly means Cleep configuration will be saved before action.

It also allows you to restart Cleep application.

Crash report is an option to send data to our server to report fatal errors. It doesn't send private informations.
This feature allows Cleep team to know a problem occured and help to improve the application in further releases.

Monitoring option enables device CPU and memory monitoring and adds a widget on device dashboard. CPU and memory charts are also generated.

## Troubleshoot

This panel is used to watch Cleep logs to investigate on a problem.

It also offers possibilty to enable debug on installed applications or on core modules.

