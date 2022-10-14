import requests
import json
from typing import Any




#Objects for Every Kind of channelType need to be created
class KNXDimmer:
    
    def __init__ (self, ip, token, config):
        """
        This is a KNX Dimmer
        """
        requests.packages.urllib3.disable_warnings()
        #Important values for PUT,GET,POST,...
        self.ip = ip
        self.token = token
        
        #Values Defining the Dimmer in the Network
        self.channelType = "de.gira.schema.channels.KNX.Dimmer"
        self.displayName = config['displayName']
        self.functionType = config['functionType']
        self.uid = config['uid']

        datapoints = config['dataPoints']

        #M/O: Whether the data point is Mandatory (always required) or Optional
        #R/W/E: Whether the data point can support Reading/Writing/Eventing. When a data point


        # M | RWE | BINARY[1,0] - Toggle to trun light on or of - 
        self.OnOff_uid = datapoints[0]['uid']
        self.OnOff_value = None
        # O | -W- | PERCENTAGEE[0,0.01,...,0.99,1]
        self.Shift_uid = datapoints[1]['uid']
        self.Shift_value = None
        # O | RWE | PERCENT[0,...,100]
        self.Brightness_uid = datapoints[2]['uid']
        self.Brightness_value = None

    def update_values (self):
        """
        This method updates the Dimmer values to the current status
        """
        try:
            url = f'https://{self.ip}/api/values/{self.uid}?token={self.token}'
            response = requests.get(url, verify=False)
            flag = True
        except Exception as e:
            response = e
            flag = False
        
        if flag:
            if str(response).endswith('[200]>'):
                values = response.json()['values']
                self.OnOff_value = values[0]['value']
                self.Shift_value = values[1]['value']
                self.Brightness_value = values[2]['value']
                return True
            else:
                return f'Something went wrong {response}'
        else:
            return f'Something went wrong {response}'

    def toggle(self):
        """
        toggles the OnOff
        """
        if self.update_values() == True:
            if self.OnOff_value == '1':
                flag = self.set_value_(self.OnOff_uid,0)
                return flag
            else:
                flag = self.set_value_(self.OnOff_uid,1)
                return flag
        else:
            return f'Values could not be updated'

    def set_value_ (self, uid: str, value: Any):
        """
        Sets 1 value to one specific uid/Datapoint
        """

        try:
            url = f'https://{self.ip}/api/values/{uid}?token={self.token}'
            body = { "value" : value }
            response = requests.put(url, json=body, verify=False)
            flag = True
        except Exception as e:
            response = e
            flag = False

        if flag:
            if str(response).endswith('[200]>'):
                return f'Everything went right'
            else:
                return f'Something went wrong {response}'
        else:
            return f'Something went wrong {response}'   

    def dimm_to (self, percent:float):
        """
        Dimms the Light to the given percentage
        """

        try:
            #self.set_value_(self.OnOff_uid, 1)
            return self.set_value_(self.Brightness_uid, percent)
        except:
            return False

class Switch:
    pass

class DimmerRGBW:
    pass

class DimmerWhite:
    pass

class BlindWithPos:
    pass

class Trigger:
    pass

class SceneSet:
    pass

class SceneControl:
    pass

class RoomTemperatureSwitchable:
    pass

class KNXHeatingCoolingSwitchable:
    pass

class KNXFanCoil:
    pass

class AudioWithPlaylist:
    pass

class SonosAudio:
    pass

class Camera:
    pass

class Link:
    pass

class Binary:
    pass

class DWord:
    pass

class String:
    pass

class Byte:
    pass

class Percent:
    pass

class Temperature:
    pass
