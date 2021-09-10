# RPI LED Strip Shield

This plugin is used to handle the RPI LEDStrip Shield, designed here :https://github.com/horfee/RPI-LED-Strip-Shield-Board
It controls a fan according to SoC temperature, and a 4 channels led strip (Red Green Blue White typically)
You may control only 1 channel if needed.

## Setup

Install via the bundled [Plugin Manager](https://docs.octoprint.org/en/master/bundledplugins/pluginmanager.html)
or manually using this URL:

    https://github.com/horfee/RPI-LED-Strip-Shield/archive/master.zip


## Configuration

In the settings section you can define the pin number associated to each color (the pin numbers are written on the board : it's a number from 4 to 7).
You can also define the thresholds used to control the fan speed.

You can also choose to interact with gcode, on M150 command : this command can turn on/off leds, with the four channels : M150 RXXX UXXX BXXX WXXX (R: red, U: green, B: blue, W: white, XXX: from 0 to 255)

The main advantage of the board is it powers up the raspberry pi, the led strip and the fan, and can be connected directly to the Prusa 24V power supply, consuming around 5-10watts. No extra wire, no additional electronics (like pca9685, etc.) needed to use this board.