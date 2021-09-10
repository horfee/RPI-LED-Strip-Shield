/*
 * View model for RPI LED Strip Shield
 *
 * Author: horfee
 * License: AGPLv3
 */
$(function() {
    function Rpi_ledstrip_shieldViewModel(parameters) {
        var self = this;
        self.settings = parameters[0];


        var url = OctoPrint.getBlueprintUrl("rpi_ledstrip_shield") + "/detectedAddresses";
        
        self.addresses = ko.observableArray([]);

        self.refreshAddresses = function() {
            console.log("coucou");
            OctoPrint.get(url).done((response) =>{
                self.addresses.removeAll();
                self.addresses.push(null);
                self.addresses.push.apply(self.addresses, response);
                  
                console.log(response);
            });
        }

        self.onBeforeBinding = function() {
            self.addresses.push("");
            self.addresses.push(self.settings.settings.plugins.rpi_ledstrip_shield.pcaAddress());
        }

    }

    /* view model class, parameters for constructor, container to bind to
     * Please see http://docs.octoprint.org/en/master/plugins/viewmodels.html#registering-custom-viewmodels for more details
     * and a full list of the available options.
     */
    OCTOPRINT_VIEWMODELS.push({
        construct: Rpi_ledstrip_shieldViewModel,
        // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...
        dependencies: [ "settingsViewModel" ],
        // Elements to bind to, e.g. #settings_plugin_rpi_ledstrip_shield, #tab_plugin_rpi_ledstrip_shield, ...
        elements: [ "#settings_plugin_rpi_ledstrip_shield" ]
    });
});
