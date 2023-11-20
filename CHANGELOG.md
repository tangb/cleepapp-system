# Changelog

## [UNRELEASED]
### Fixed
- Fix documentation

### Changed
- Move monitoring widget to desc.json file
- Migrate drivers directive to config-drivers component
- Add new config-code component
- Update config to new Cleep components
- Improve monitoring (show/hide widgets, disable tasks)

## [2.2.0] - 2023-03-09
### Fixed
- Led state is not properly restored after a reboot

### Changed
- Restore original activity led trigger mode to default mode (mmc0) when enabled again
- Force option added to reboot and halt device functions

## [2.1.2] - 2022-01-25
### Fixed
- Move system python dependencies from core

### Added
- Codemirror CSS from core moved to system app

## [2.1.1] - 2021-07-27

### Fixed
* Fix LED tweak on raspi zero and oldest raspi (first version)

## [2.1.0] - 2021-05-18

* Implement power and activity leds tweaking

## [2.0.3] - 2021-05-11

* Backend: fix needrestart event issue

## [2.0.2] - 2021-05-04

* Backend: remove filesystem expansion feature. Performed with cleep-iso
* Backend: reboot after driver install/uninstall only if required
* Frontend: reload config after changes

## [2.0.1] - 2021-04-12

* Simplify function parameters checking
* Fix tests
* Improve code quality (lint)

## [2.0.0] - 2020-12-13

* Migrate to Python3
* Update after core changes
* Clean and optimize code
* Add unit tests
* Move Cleep and App updates to dedicated update app

## [1.1.0] - 2019-09-30

* Update after core update
* Improve layout
* Fix issues in front and back
* Add driver config tab

## [1.0.3] - 2019-02-25

* Improve install/uninstall/update module process stability

## [1.0.2] - 2018-10-20

* Check only released CleepOs version during update check
* Improve CleepOs update adding specific dialog with changes and new version available
* Disable by default auto application and CleepOs update
* Some other small improvements

## [1.0.1] - 2018-10-14

* Fix small issues

## [1.0.0] - 2018-10-08

* First official release

