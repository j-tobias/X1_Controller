import requests
import json
from typing import Any


#NOTES
#O MEANS OPTIONAL AND DOES NOT HAVE TO OCCOUR IN THE CONFIG FILE
#LENGTH OF DATAPOINTSLIST HAS TO BE CHECKED FIRST 
#ELSE THE PROGRAM COULD RUN INTO INDEX ERRORS OF THE DATAPOINTSLIST

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

        self.Shift_exist = False
        self.Brightness_exist = False

        for datapoint in datapoints:

            if datapoint['name'] == "OnOff":
                # M | RWE | BINARY[1,0] - Toggle to trun light on or of - 
                self.OnOff_uid = datapoint['uid']
                self.OnOff_value = None           

            if datapoint['name'] == "Shift":
                # O | -W- | PERCENTAGEE[0,0.01,...,0.99,1]
                self.Shift_uid = datapoint['uid']
                self.Shift_value = None
                self.Shift_exist = True

            if datapoint['name'] == "Brightness":
                # O | RWE | PERCENT[0,...,100]
                self.Brightness_uid = datapoint['uid']
                self.Brightness_value = None
                self.Brightness_exist = True            


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

                if self.Shift_exist:
                    self.Shift_value = values[1]['value']
                if self.Brightness_exist:
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
        works only if Brightness exists
        """

        try:
            #self.set_value_(self.OnOff_uid, 1)
            return self.set_value_(self.Brightness_uid, percent)
        except:
            return False

class Switch:

    def __init__ (self, ip, token, config):
        """
        This is a KNX Switch
        """
        requests.packages.urllib3.disable_warnings()
        #Important values for PUT,GET,POST,...
        self.ip = ip
        self.token = token
        
        #Values Defining the Dimmer in the Network
        self.channelType = "de.gira.schema.channels.Switch"
        self.displayName = config['displayName']
        self.functionType = config['functionType']
        self.uid = config['uid']

        datapoints = config['dataPoints']

        #M/O: Whether the data point is Mandatory (always required) or Optional
        #R/W/E: Whether the data point can support Reading/Writing/Eventing. When a data point


        # M | RWE | BINARY[1,0] - Toggle to trun light on or of - 
        self.OnOff_uid = datapoints[0]['uid']
        self.OnOff_value = None

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

    def set_value_ (self, uid: str, value: int):
        """
        Sets 1 value to one specific uid/Datapoint
        either 1 or 0
        """
        if value != 0 and value != 1:
            raise ValueError(f'Value is not 1 or 0 instead it is {value}')

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

    def update_values (self):
        """
        This method updates the Switch values to the current status
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
                return True
            else:
                return f'Something went wrong {response}'
        else:
            return f'Something went wrong {response}'

class BlindWithPos:
    
    def __init__ (self, ip, token, config):
        """
        This is a KNX Blind with Position
        """
        requests.packages.urllib3.disable_warnings()
        #Important values for PUT,GET,POST,...
        self.ip = ip
        self.token = token
        
        #Values Defining the Dimmer in the Network
        self.channelType = "de.gira.schema.channels.BlindWithPos"
        self.displayName = config['displayName']
        self.functionType = config['functionType']
        self.uid = config['uid']

        datapoints = config['dataPoints']

        #M/O: Whether the data point is Mandatory (always required) or Optional
        #R/W/E: Whether the data point can support Reading/Writing/Eventing. When a data point

        self.Position_exist = False
        self.Slat_Position_exist = False

        for datapoint in datapoints:

            if datapoint['name'] == "Step-Up-Down":
                # M | -W- | BINARY[1,0] - ? - 
                self.Step_Up_Down_uid = datapoint['uid']
                self.Step_Up_Down_value = None         

            if datapoint['name'] == "Up-Down":
                # M | -W- | BINARY[1,0] - ? -
                self.Up_Down_uid = datapoint['uid']
                self.Up_Down_value = None

            if datapoint['name'] == "Position":
                # O | RWE | PERCENT[0,...,100]
                self.Position_uid = datapoint['uid']
                self.Position_value = None
                self.Position_exist = True 

            if datapoint['name'] == "Slat-Position":
                # O | RWE | PERCENT[0,...,100]
                self.Slat_Position_uid = datapoint['uid']
                self.Slat_Position_value = None
                self.Slat_Position_exist = True

    def update_values (self):
        """
        This method updates the Blind with Position values to the current status
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

                for datapoint in values:
                    uid = datapoint['uid']
                    value = datapoint['value']

                    if uid == self.Step_Up_Down_uid:
                        self.Step_Up_Down_value = value
                    elif uid == self.Up_Down_uid:
                        self.Step_Up_Down_value = value
                    
                    if self.Position_exist:
                        if uid == self.Position_uid:
                            self.Position_value = value
                    
                    if self.Slat_Position_exist:
                        if uid == self.Slat_Position_uid:
                            self.Slat_Position_value = value


                return True
            else:
                return f'Something went wrong {response}'
        else:
            return f'Something went wrong {response}'


        
class DimmerRGBW:
    pass

class DimmerWhite:
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
