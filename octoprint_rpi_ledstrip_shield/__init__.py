# coding=utf-8
from __future__ import absolute_import

from subprocess import PIPE
import subprocess
import flask
import io
import octoprint.plugin
import Adafruit_PCA9685
from octoprint.util import RepeatedTimer


def interpolate(value, leftMin, leftMax, rightMin, rightMax):
    # Figure out how 'wide' each range is
    leftSpan = leftMax - leftMin
    rightSpan = rightMax - rightMin

    # Convert the left range into a 0-1 range (float)
    valueScaled = float(value - leftMin) / float(leftSpan)

    # Convert the 0-1 range into a value in the right range.
    return rightMin + (valueScaled * rightSpan)


class Shield:
    def __init__(self, logger, addr, redPin, greenPin, bluePin, whitePin, fanControl, readTemperatureCommand, minTemperature, maxTemperature):         
        self.address = addr
        self._logger = logger
        self.redPin = redPin
        self.greenPin = greenPin
        self.bluePin = bluePin
        self.whitePin = whitePin
        self.minTemperature = minTemperature
        self.maxTemperature = maxTemperature
        self.readTemperatureCommand = readTemperatureCommand
        self._checkTempTimer = None

        try:
            self.pca = Adafruit_PCA9685.PCA9685(addr)
            self.pca.set_pwm_freq(120)
        except:
            self._logger.error("Unable to connect to I2C device")

        if fanControl :
            self.startFanControl()
    
    def __del__(self):
        self.stopFanControl()

    def setRed(self, pct):
        self._logger.debug("Setting red led (%i) level to %s", self.redPin, pct)
        if self.redPin > -1:
            self.pca.set_pwm(self.redPin, 0, int(4095 * pct))

    def setGreen(self, pct):
        self._logger.debug("Setting green led (%i) level to %s", self.greenPin, pct)
        if self.greenPin > -1:
            self.pca.set_pwm(self.greenPin, 0, int(4095 * pct))

    def setBlue(self, pct):
        self._logger.debug("Setting blue led (%i) level to %s", self.bluePin, pct)
        if self.bluePin > -1:
            self.pca.set_pwm(self.bluePin, 0, int(4095 * pct))

    def setWhite(self, pct):
        self._logger.debug("Setting white led (%i) level to %s", self.whitePin, pct)
        if self.whitePin > -1:
            self.pca.set_pwm(self.whitePin, 0, int(4095 * pct))
    
    def startFanControl(self):
        self._logger.debug("Starting fan control")
        if self._checkTempTimer is None or not self._checkTempTimer.is_alive():
            self._logger.debug("Creating fan control thread")
            self._checkTempTimer = RepeatedTimer(1, self._adjustFanSpeed, run_first=True)
        if not self._checkTempTimer.is_alive():
            self._logger.debug("Starting fan control thread")
            self._checkTempTimer.start()
    
    def stopFanControl(self):
        if self._checkTempTimer is not None:
            self._logger.debug("Stopping fan control")
            self._checkTempTimer.cancel()
            self._checkTempTimer = None

    def _adjustFanSpeed(self):
        self._logger.debug("Adjusting fan")
        # TODO : invoke the measure temp command
        try:
            temp = float(subprocess.Popen(self.readTemperatureCommand, stdout=PIPE, shell=True).stdout.read())
        except:
            self._logger.error("Unable to read a float value from command. Please correct the command")
            return

        # here 700 is the lowest PWM for the fan to run.
        if temp < self.minTemperature:
            self._logger.debug("Turning off the fan")
            #self.pca.set_pwm(8, 0, 0)
        else:
            temp = min(temp, self.maxTemperature)
            pct = interpolate(temp, self.minTemperature, self.maxTemperature, 700, 4095)
            self._logger.debug("Setting fan to run at %f\% of max speed", pct)
            #self.pca.set_pwm(8, 0, pct)




def detectI2CDevices():
    #cmd = "i2cdetect -y 1"
    cmd = "cat ic2detectOutput"
    stdout = subprocess.Popen(cmd,stdout=PIPE, shell=True).stdout
    foundDevices = []
    firstLine = True
    for line in io.TextIOWrapper(stdout, encoding="utf-8"):
        if firstLine:
            firstLine = False
        else:
            line = line.split(" ")
            line = list(filter(lambda elt: elt.isdigit(), line[1:]))
            foundDevices += line
    
    return list(map(lambda elt : "0x" + elt, foundDevices))

class Rpi_ledstrip_shieldPlugin(
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.BlueprintPlugin,
    octoprint.plugin.TemplatePlugin
):

    def __init__(self):
        self.interactWithGcode = False
        self.controlFan = False
        self.pcaAddress = None
        self.shield = None


    def HandleM150(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        if self.interactWithGcode and self.shield and gcode and cmd.startswith("M150"):
            self._logger.debug("Must change light states")
            leds = {"R":0,"U":0,"B":0,"W":0}

            for val in cmd.split(" "):
                leds[val[0]] = float(min(max(int(val[1:]) / 255,0), 1))
            
            self.shield.setRed(leds["R"])
            self.shield.setBlue(leds["B"])
            self.shield.setGreen(leds["U"])
            self.shield.setWhite(leds["W"])



    ##~~ StartupPlugin mixin
    def on_startup(self, *args, **kwargs):
        self._logger.info("RPI LED Strip Shield starting up")


    ##~~ TemplatePlugin mixin
    def get_template_configs(self):
	    return [
			dict(type="settings", name="Shield Prusa LED", custom_bindings=True)
		]

    def on_after_startup(self):
        self._updateAfterSettingsChanged()

    ##~~ SettingsPlugin mixin

    def on_settings_save(self, data):
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self._updateAfterSettingsChanged()

    def on_settings_initialized(self):
        self._updateAfterSettingsChanged()

    def _updateAfterSettingsChanged(self):
        self._logger.debug("Plugin instance refreshed with new settings")
        self.interactWithGcode = self._settings.get_boolean(["catchM150"])
        self.measureTempCmd = self._settings.get(["measureTempcmd"])
        self.controlFan = self._settings.get_boolean(["controlFan"])
        self.pcaAddress = self._settings.get(["pcaAddress"])
        self.pins = {
            "red": self._settings.get_int(["redPin"]) if self._settings.get_boolean(["redPinEnabled"]) else -1,
            "blue": self._settings.get_int(["bluePin"]) if self._settings.get_boolean(["bluePinEnabled"]) else -1,
            "green": self._settings.get_int(["greenPin"]) if self._settings.get_boolean(["greenPinEnabled"]) else -1,
            "white": self._settings.get_int(["whitePin"]) if self._settings.get_boolean(["whitePinEnabled"]) else -1
        }
        
        self.temperatures = {
            "min": self._settings.get_int(["minTemperature"]),
            "max": self._settings.get_int(["maxTemperature"])
        }

        if self.pcaAddress is None:
            return

        if "0x" in self.pcaAddress :
            self.pcaAddress = int(self.pcaAddress, 16)
        else:
            self.pcaAddress = int(self.pcaAddress)
        if self.shield is None or self.shield.address != self.pcaAddress:
            self.shield = Shield(
                self._logger, 
                self.pcaAddress, 
                self.pins["red"], self.pins["green"], self.pins["blue"], self.pins["white"], 
                self.controlFan,
                self.measureTempCmd, self.temperatures["min"], self.temperatures["max"])
        else:
            self.shield.redPin = self.pins["red"]
            self.shield.greenPin = self.pins["green"]
            self.shield.bluePin = self.pins["blue"]
            self.shield.whitePin = self.pins["white"]
            self.shield.readTemperatureCommand = self.measureTempCmd
            self.shield.minTemperature = self.temperatures["min"]
            self.shield.maxTemperature = self.temperatures["max"]
            if self.controlFan:
                self.shield.startFanControl()
            else:
                self.shield.stopFanControl()


    def get_settings_defaults(self):
        self._logger.debug("Asking for defaults")

        return {
            # put your plugin's default settings here
            "pcaAddress": "0x40",
            "controlFan": True,
            "catchM150": True,
            "measureTempcmd": "printf %.2f \"$((100 * $(cat /sys/class/thermal/thermal_zone0/temp) / 1000))e-2\"",
            "maxTemperature": 75.0,
            "minTemperature": 30,
            "redPin":4,
            "bluePin":5,
            "greenPin":6,
            "whitePin":7,
            "redPinEnabled": False,
            "bluePinEnabled": False,
            "greenPinEnabled": False,
            "whitePinEnabled": False
        }


    ##~~ AssetPlugin mixin

    def get_assets(self):
        # Define your plugin's asset files to automatically include in the
        # core UI here.
        return {
            "js": ["js/rpi_ledstrip_shield.js"],
            "css": ["css/rpi_ledstrip_shield.css"],
            "less": ["less/rpi_ledstrip_shield.less"]
        }

    ##~~ Softwareupdate hook

    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
        # for details.
        return {
            "rpi_ledstrip_shield": {
                "displayName": "Rpi_ledstrip_shield Plugin",
                "displayVersion": self._plugin_version,

                # version check: github repository
                "type": "github_release",
                "user": "horfee",
                "repo": "RPI LED Strip Shield",
                "current": self._plugin_version,

                # update method: pip
                "pip": "https://github.com/horfee/RPI LED Strip Shield/archive/{target_version}.zip",
            }
        }
    
    @octoprint.plugin.BlueprintPlugin.route("/detectedAddresses", methods=["GET"])
    def getDetectedAddresses(self):
        return flask.jsonify(detectI2CDevices())

    
    

# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Rpi_ledstrip_shield Plugin"

# Starting with OctoPrint 1.4.0 OctoPrint will also support to run under Python 3 in addition to the deprecated
# Python 2. New plugins should make sure to run under both versions for now. Uncomment one of the following
# compatibility flags according to what Python versions your plugin supports!
#__plugin_pythoncompat__ = ">=2.7,<3" # only python 2
__plugin_pythoncompat__ = ">=3,<4" # only python 3
#__plugin_pythoncompat__ = ">=2.7,<4" # python 2 and 3

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = Rpi_ledstrip_shieldPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
        "octoprint.comm.protocol.gcode.queuing": __plugin_implementation__.HandleM150
    }
