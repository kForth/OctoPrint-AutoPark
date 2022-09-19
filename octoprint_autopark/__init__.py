import octoprint.plugins
from octoprint.events import Events


class ProfileMode:
    ALL = "all"
    SELECT = "select"


class ParkLocation:
    CENTER = "center"
    MIN_MIN = "min"
    MAX_MAX = "max"
    MIN_MAX = "min_max"
    MAX_MIN = "max_min"
    CUSTOM = "custom"


class ParkSpeed:
    AUTO = "auto"
    CUSTOM = "custom"


class AutoParkPlugin(
    octoprint.plugin.EventHandlerPlugin,
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.TemplatePlugin,
):
    def __init__(self):
        super().__init__()

        defaults = self.get_settings_defaults()
        self._profileMode = defaults["profileMode"]
        self._selectedProfiles = defaults["selectedProfiles"]
        self._parkAfterPause = defaults["parkAfterPause"]
        self._parkAfterDone = defaults["parkAfterDone"]
        self._parkAfterFail = defaults["parkAfterFail"]
        self._homeBeforeUnpark = defaults["homeBeforeUnpark"]
        self._parkLocation = defaults["parkLocation"]
        self._parkSpeed = defaults["parkSpeed"]
        self._parkPosX = defaults["parkPosX"]
        self._parkPosY = defaults["parkPosY"]
        self._parkLiftZ = defaults["parkLiftZ"]
        self._parkSpeedXY = defaults["parkSpeedXY"]
        self._parkSpeedZ = defaults["parkSpeedZ"]
        self._parkSpeedXY_unit = defaults["parkSpeedXY_unit"]
        self._parkSpeedZ_unit = defaults["parkSpeedZ_unit"]

        self.pausePosX = None
        self.pausePosY = None
        self.pausePosZ = None

    def set_pause_pos(self, x, y, z, *a, **k):
        self.pausePosX = x
        self.pausePosY = y
        self.pausePosZ = z

    def reset_pause_pos(self):
        self.pausePosX = None
        self.pausePosY = None
        self.pausePosZ = None

    def get_park_pos(self):
        if self._parkLocation == ParkLocation.CUSTOM:
            return self._parkPosX, self._parkPosY
        else:
            profile = self._printer_profile_manager.get_current()
            if self._parkLocation == ParkLocation.CENTER:
                return profile["volume"]["width"] / 2, profile["volume"]["depth"] / 2
            elif self._parkLocation == ParkLocation.MIN_MIN:
                return 0, 0
            elif self._parkLocation == ParkLocation.MIN_MAX:
                return 0, profile["volume"]["depth"]
            elif self._parkLocation == ParkLocation.MAX_MIN:
                return profile["volume"]["width"], 0
            elif self._parkLocation == ParkLocation.MAX_MAX:
                return profile["volume"]["width"], profile["volume"]["depth"]
            else:
                self._logger.error("Invalid Park Location = %s", self._parkLocation)
                return 0, 0

    def get_park_speeds(self):
        if self._parkSpeed == ParkSpeed.AUTO:
            profile = self._printer_profile_manager.get_current()
            return (
                min(profile["axes"]["x"]["speed"], profile["axes"]["y"]["speed"]),
                profile["axes"]["z"]["speed"],
            )
        else:
            return (
                self._parkSpeedXY * self._parkSpeedXY_unit,
                self._parkSpeedZ * self._parkSpeedZ_unit,
            )

    def park(self, event, payload):
        self.set_pause_pos(**payload["position"])
        if any([e is None for e in [self.pausePosX, self.pausePosY, self.pausePosY]]):
            text = ["Unable to park because some of the pause position is invalid!"]
            if self.pausePosX is None:
                text += ["X is None!"]
            if self.pausePosY is None:
                text += ["Y is None!"]
            if self.pausePosZ is None:
                text += ["Z is None!"]
            self._logger.error(" ".join(text))
            self._notify("error", "Unable to Park!", "\n".join(text))
            return False
        self._logger.info("Parking Print Head on %s", event)
        parkX, parkY = self.get_park_pos()
        speedXY, speedZ = self.get_park_speeds()

        self._printer.jog({"z": self._parkLiftZ}, True, speedZ)
        self._printer.jog({"x": parkX, "y": parkY}, False, speedXY)
        self._printer.commands("M400")
        return True

    def unpark(self, event, payload):
        if any([e is None for e in [self.pausePosX, self.pausePosY, self.pausePosY]]):
            self._logger.error(
                "Unable to unpark because some of the pause position is invalid! [%s, %s, %s]",
                self.pausePosX,
                self.pausePosY,
                self.pausePosZ,
            )
            self._event_bus.fire(
                "Error",
                {
                    "error": "\nUnable to unpark the print head, the stored position is invalid!"
                },
            )
            self._printer.cancel_print()
            return False
        self._logger.info("Unparking Print Head on %s", event)

        speedXY, speedZ = self.get_park_speeds()

        if self._homeBeforeUnpark:
            self._printer.home(["x", "y"])
        self._printer.jog({"x": self.pausePosX, "y": self.pausePosY}, False, speedXY)
        self._printer.jog({"z": self.pausePosZ}, False, speedZ)
        self._printer.commands("M400")
        self.reset_pause_pos()
        return True

    def _notify(self, type, title, text):
        self._plugin_manager.send_plugin_message(
            self._identifier, {"notify": {"type": type, "title": title, "text": text}}
        )

    def _enabled_for_current_profile(self):
        if self._profileMode == ProfileMode.ALL:
            return True
        profile = self._printer_profile_manager.get_current()
        if not profile:
            return False
        profile_id = profile.get("id", False)
        if not profile_id:
            return False
        return profile_id in self._selectedProfiles

    ##~~ SettingsPlugin mixin

    def get_settings_defaults(self):
        return {
            "profileMode": ProfileMode.ALL,
            "selectedProfiles": [],
            "parkAfterPause": True,
            "parkAfterDone": True,
            "parkAfterFail": True,
            "homeBeforeUnpark": False,
            "parkLocation": ParkLocation.CENTER,
            "parkSpeed": ParkSpeed.AUTO,
            "parkPosX": 0,  # mm
            "parkPosY": 0,  # mm
            "parkLiftZ": 5,  # mm
            "parkSpeedXY": 100,  # mm/s
            "parkSpeedZ": 20,  # mm/s
            "parkSpeedXY_unit": 60,  # mm/s to mm/m
            "parkSpeedZ_unit": 60,  # mm/s to mm/m
        }

    def on_settings_save(self, data):
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self.read_settings()

    def read_settings(self):
        self._profileMode = self._settings.get(["profileMode"])
        self._selectedProfiles = self._settings.get(["selectedProfiles"])
        self._parkAfterPause = self._settings.get_boolean(["parkAfterPause"])
        self._parkAfterDone = self._settings.get_boolean(["parkAfterDone"])
        self._parkAfterFail = self._settings.get_boolean(["parkAfterFail"])
        self._homeBeforeUnpark = self._settings.get_boolean(["homeBeforeUnpark"])
        self._parkLocation = self._settings.get(["parkLocation"])
        self._parkSpeed = self._settings.get(["parkSpeed"])
        self._parkPosX = self._settings.get(["parkPosX"])
        self._parkPosY = self._settings.get(["parkPosY"])
        self._parkLiftZ = self._settings.get(["parkLiftZ"])
        self._parkSpeedXY = self._settings.get(["parkSpeedXY"])
        self._parkSpeedZ = self._settings.get(["parkSpeedZ"])
        self._parkSpeedXY_unit = self._settings.get(["parkSpeedXY_unit"])
        self._parkSpeedZ_unit = self._settings.get(["parkSpeedZ_unit"])

    ##~~ AssetPlugin mixin
    def get_assets(self):
        return {
            "css": ["css/autopark.css"],
            "js": ["js/autopark.js"],
            "less": ["less/autopark.less"],
        }

    ##~~ TemplatePlugin mixin

    def get_template_configs(self):
        return [
            {
                "type": "settings",
                "name": "AutoPark Plugin",
                "template": "autopark_settings.jinja2",
                "custom_bindings": True,
            }
        ]

    # ~~ EventHandlerPlugin hook

    def on_event(self, event, payload):
        if event not in (
            Events.PRINT_PAUSED,
            Events.PRINT_RESUMED,
            Events.PRINT_DONE,
            Events.PRINT_FAILED,
        ):
            return

        if not self._enabled_for_current_profile():
            return
        if not (self._parkAfterPause or self._parkAfterDone or self._parkAfterFail):
            return

        if event == Events.PRINT_DONE:
            if self._parkAfterDone:
                self.park(event, payload)

        elif event == Events.PRINT_FAILED:
            if self._parkAfterFail:
                self.park(event, payload)

        elif self._parkAfterPause:
            if event == Events.PRINT_PAUSED:
                self.park(event, payload)

            elif event == Events.PRINT_RESUMED:
                self.unpark(event, payload)

        return True

    ## SoftwareUpdate Hook

    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
        # for details.
        return {
            "autopark": {
                "displayName": "AutoPark Plugin",
                "displayVersion": self._plugin_version,
                # version check: github repository
                "type": "github_release",
                "user": "kforth",
                "repo": "OctoPrint-AutoPark",
                "current": self._plugin_version,
                "stable_branch": {
                    "name": "Stable",
                    "branch": "main",
                    "commitish": ["main"],
                },
                # update method: pip
                "pip": "https://github.com/kforth/OctoPrint-AutoPark/archive/{target_version}.zip",
            }
        }


__plugin_name__ = "AutoPark Plugin"
__plugin_version__ = "0.1.0"
__plugin_description__ = (
    "Automatically park the print head when a print pauses or finishes."
)
__plugin_pythoncompat__ = ">=3,<4"
__plugin_implementation__ = AutoParkPlugin()
__plugin_hooks__ = {
    "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
}
