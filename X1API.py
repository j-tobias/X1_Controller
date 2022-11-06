import requests
import json

from zmq import device
import Gira_Classes



class GiraControl:

    def __init__ (self, ip:str = None, client_id: str = 'de.GiraControl.defaultclient'):
        """
        This is creates an Object to handle and interacht with the Gira IoT API

        ip: str = IP-Adress of the Gira X1
        client_id: str = To ensure uniqueness client identifiers have to be URNs within the organization of the client (de.GiraControl.defaultclient)
        """

        #Check for valid inputs
        if type(ip) != str:
            raise ValueError(f'username has to be of type string but is {type(ip)}')
        
        if type(client_id) != str:
            raise ValueError(f'password has to be of type string but is {type(client_id)}')
        
        requests.packages.urllib3.disable_warnings()

        self.ip = ip
        self.token = None
        self.client_id = client_id
        self.uid = None
        self.uid_config = None
        self.device_list = []

    def availability_check (self) -> bool:
        """
        Checking if the Gira IoT REST API is available

        returns True for availability
        and Error Code Else
        """
        try:
            url = f'https://{self.ip}/api/v2'
            response = requests.get(url,verify=False)

            try:
                response.json()
                return response.json()
            except:
                if str(response).endswith('[200]>'):
                    return True
                else:
                    return response
        except Exception as e:
            return e

    def register_client (self, username:str, password:str) -> str:
        """
        This method connects your device with the API and returns the token
        
        - username = username for an registerd account on the X1
        - password = password for the chosen account
        
        if an error occours\n
        400 Bad Request  | missingContent | Body is empty/invalid.\n
        401 Unauthorized | invalidAuth    | Missing or invalid authentication.\n
        423 Locked       | locked         | The device is currently locked.\n
        """
        #Check for valid inputs
        if type(username) != str:
            raise ValueError(f'username has to be of type string but is {type(username)}')
        
        if type(password) != str:
            raise ValueError(f'password has to be of type string but is {type(password)}')

        try:
            body = '{"client":"de.homeandfuture.FristTestClient"}'
            url = f'https://{self.ip}/api/v2/clients'
            response = requests.post(url, body, auth=(username, password), verify=False)
            flag = True
        except Exception as e:
            response = e
            flag = False

        if flag:
            try:
                self.token = response.json()['token']
                return self.token
            except:
                return f'Something went wrong {response.text}'
        else:
            return f'Something went wrong {response}'

    def unregister_client (self, token: str = None) -> str:
        """
        This method deregisters this client from the X1

        Every time a new combination of username from the HTTP Basic Authorization header and the <client-identifier> is used,
        a new token will be generated. 
        Registering with the same username and the same <client-identifier> again without unregistering the token will yield the same token. 
        Multiple clients can be registered at the same time and the lifetime of a token is not limited. 
        The token will stay valid until the client is unregistered, the user is deleted or the username is changed. 
        The token will stay valid when the user’s password is changed. 
        A token that was invalidated due to a removed username will become valid again if the username is used again.
        """

        token = token or self.token

        if type(token) != str:
            raise ValueError(f'token is not of type string but of type {type(token)}')

        try:
            url = f'https://{self.ip}/api/v2/clients/{token}?token={token}'
            response = requests.delete(url, verify=False)
            flag = True
        except Exception as e:
            response = e
            flag = False

        if flag:
            if str(response).endswith('[204]>'):
                return "Client was successfully unregistered."
            elif str(response).endswith('[401]>'):
                return "The token cannot be found."
            elif str(response).endswith('[423]>'):
                return "The device is currently locked."
            elif str(response).endswith('[500]>'):
                return "Failed to remove client."
            else:
                return f'Something went wrong {response}'
        else:
            return f'Something went wrong {response}'

    def register_callbacks (self, serviceCallback:str, valueCallback:str, testCallbacks:bool = None):
        """
        I HAVE NEVER TESTED THIS METHOD
        IT'S JUST HERE FOR COMPLETENES
        """

        if testCallbacks == None:
            data = {
                    "serviceCallback": serviceCallback, 
                    "valueCallback": valueCallback
                    }
        else:
            data = {
                    "serviceCallback": serviceCallback, 
                    "valueCallback": valueCallback, 
                    "testCallbacks": testCallbacks
                    }

        try:
            url = f'https://{self.ip}/api/v2/clients/{self.token}/callbacks'
            response = requests.post(url, verify=False)
            return response
        except Exception as e:
            return e

    def get_uid (self):
        """
        This Method returns the Unique identifier of current configuration. 
        This identifier changes each time the configuration is changed 
        (e.g. GPA project download, configuration changes with the Gira Smart Home App).
        """

        try:
            url = f'https://{self.ip}/api/v2/uiconfig/uid?token={self.token}'
            response = requests.get(url, verify=False)
            flag = True
        except Exception as e:
            response = e
            flag = False

        if flag:
            try:
                self.uid = response.json()['uid']
                return self.uid
            except:
                return f'Something went wrong {response}'
        else:
            return f'Something went wrong {response}'

    def get_uid_config (self, filename:str = None):
        """
        This method loads the configuration currently on the X1

        filename: .JSON   -  the config can be saved to a file with specified filename (if left empty it wont be saved)
        """
        if filename != None and type(filename) != str:
            raise ValueError(f'filename has to be of type string but is {type(filename)}')

        try:
            url = f'https://{self.ip}/api/uiconfig?token={self.token}'
            response = requests.get(url, verify=False)
            flag = True
        except Exception as e:
            response = e
            flag = False

        if flag:
            try:
                self.uid_config = response.json()
            except:
                return f'Something went wrong {response}'
            
            if filename != None:
                with open(filename, mode='w') as f:
                    json.dump(response.json(),f,indent=5)
                return response.json()
            else:
                return response.json()
        else:
            return f'Something went wrong {response}'

    def get_devices (self)-> list:
        """
        This method returns a list of all devices as their own objects
        """
        devices_list = []

        #first let's get the uid Configuration
        if self.uid_config == None:
            self.get_uid_config()

        functions = self.uid_config['functions']
        for config in functions:
            
            #sorting all the Devices into their own Classes

            if config['channelType'] == "de.gira.schema.channels.KNX.Dimmer":
                devices_list.append(Gira_Classes.KNXDimmer(ip= self.ip, token=self.token, config=config))
            elif config['channelType'] == "de.gira.schema.channels.Sonos.Audio":
                pass
            elif config['channelType'] == "de.gira.schema.channels.Trigger":
                pass
            elif config['channelType'] == "de.gira.schema.channels.RA.RemoteAccess":
                pass
            elif config['channelType'] == "de.gira.schema.channels.Float":
                pass
            elif config['channelType'] == "de.gira.schema.channels.Binary":
                pass
            elif config['channelType'] == "de.gira.schema.channels.BlindWithPos":
                pass
            elif config['channelType'] == "de.gira.schema.channels.Switch":
                devices_list.append(Gira_Classes.Switch(ip= self.ip, token=self.token, config=config))
            elif config['channelType'] == "de.gira.schema.channels.FunctionScene":
                pass
            elif config['channelType'] == "de.gira.schema.channels.String":
                pass

        #updating the global variable
        self.device_list = devices_list
        return devices_list

    def get_device (self, displayName:str = None, uid:str = None)-> Gira_Classes.KNXDimmer:
        """
        returns the device with the DisplayName or the uid - only must be given
        uid > Displayname
        """
        #Value Checking
        if displayName == None and uid == None:
            raise ValueError('No values are given')
        
        if type(displayName) != str and displayName != None:
            raise ValueError(f'DisplayName has to be of type string but is {type(displayName)}')

        if type(uid) != str and uid != None:
            raise ValueError(f'uid has to be of type string but is {type(uid)}')

        #catching the devices if it hasen't been done yet
        if self.device_list == []:
            self.get_devices()

        if displayName != None and uid != None:
            for device in self.device_list:
                if device.uid == uid:
                    return device
        elif displayName == None and uid != None:
            for device in self.device_list:
                if device.uid == uid:
                    return device
        elif displayName != None and uid == None:
            for device in self.device_list:
                if device.displayName == displayName:
                    return device
