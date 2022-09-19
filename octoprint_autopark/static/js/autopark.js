/*
 * View model for OctoPrint-AutoPark
 *
 * Author: Kestin Goforth
 * License: AGPLv3
 */
$(function () {
    function AutoParkViewModel(parameters) {
        const PLUGIN_ID = "autopark";

        var self = this;

        self.settingsView = parameters[0];
        self.printerProfiles = parameters[1];

        self.units = {
            speed: ko.observableArray([
                // speed * value = mm/m
                {text: "mm/s", value: 60, title: "Millimeters per second"},
                {text: "mm/m", value: 1, title: "Millimeters per minute"}
            ])
        };

        self.profileMode = ko.observable();
        self.selectedProfiles = ko.observableArray([]);
        self.parkAfterPause = ko.observable();
        self.parkAfterDone = ko.observable();
        self.parkAfterFail = ko.observable();
        self.homeBeforeUnpark = ko.observable();
        self.parkLocation = ko.observable();
        self.parkPosX = ko.observable();
        self.parkPosY = ko.observable();
        self.parkLiftZ = ko.observable();
        self.parkSpeed = ko.observable();
        self.parkSpeedXY = ko.observable();
        self.parkSpeedZ = ko.observable();
        self.parkSpeedXY_unit = ko.observable();
        self.parkSpeedZ_unit = ko.observable();

        self.lastSpeedXY = undefined;
        self.parkSpeedXY_unit.subscribe(
            function (newUnit) {
                self.lastSpeedXY = newUnit;
            },
            null,
            "beforeChange"
        );
        self.parkSpeedXY_unit.subscribe(function (newUnit) {
            if (self.lastSpeedXY)
                self.parkSpeedXY((self.parkSpeedXY() * self.lastSpeedXY) / newUnit);
        });

        self.lastSpeedZ = undefined;
        self.parkSpeedZ_unit.subscribe(
            function (newUnit) {
                self.lastSpeedZ = newUnit;
            },
            null,
            "beforeChange"
        );
        self.parkSpeedZ_unit.subscribe(function (newUnit) {
            if (self.lastSpeedZ)
                self.parkSpeedZ((self.parkSpeedZ() * self.lastSpeedZ) / newUnit);
        });

        self.onBeforeBinding = function () {
            self._writeSettings(self.settingsView.settings.plugins.autopark, self);
        };

        self.onSettingsBeforeSave = function () {
            self._writeSettings(self, self.settingsView.settings.plugins.autopark);
        };

        self._writeSettings = function (source, target) {
            target.profileMode(source.profileMode());
            target.selectedProfiles(source.selectedProfiles());
            target.parkAfterPause(source.parkAfterPause());
            target.parkAfterDone(source.parkAfterDone());
            target.parkAfterFail(source.parkAfterFail());
            target.homeBeforeUnpark(source.homeBeforeUnpark());
            target.parkLocation(source.parkLocation());
            target.parkPosX(source.parkPosX());
            target.parkPosY(source.parkPosY());
            target.parkLiftZ(source.parkLiftZ());
            target.parkSpeed(source.parkSpeed());
            target.parkSpeedXY(source.parkSpeedXY());
            target.parkSpeedZ(source.parkSpeedZ());
            target.parkSpeedXY_unit(source.parkSpeedXY_unit());
            target.parkSpeedZ_unit(source.parkSpeedZ_unit());
        };

        self.onDataUpdaterPluginMessage = function (plugin, data) {
            if (plugin != PLUGIN_ID) {
                return;
            }

            if (data.notify) {
                new PNotify(data.notify);
            }
        };

        self._bindTitle = function (option, item) {
            ko.applyBindingsToNode(option, {attr: {title: item.title}}, item);
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: AutoParkViewModel,
        dependencies: ["settingsViewModel", "printerProfilesViewModel"],
        elements: ["#settings_plugin_autopark"]
    });
});
