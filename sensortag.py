import os
import sys
from datetime         import datetime
from flask            import Flask, request, jsonify, make_response
from flask_sockets    import Sockets
from bluepy.btle      import BTLEException
from bluepy.sensortag import SensorTag

SENSORTAG_ADDRESS = ""

class SensorTagDevice:
    def __init__(self, sensorTagAddress):
        self.tag = SensorTag(sensorTagAddress)
        self.tagAddress = sensorTagAddress
        
    def enableSensors(self):
        self.tag.IRtemperature.enable()
        self.tag.humidity.enable()
        self.tag.barometer.enable()
        
    def disableSensors(self):
        self.tag.IRtemperature.disable()
        self.tag.humidity.disable()
        self.tag.barometer.disable()

    def getReadings(self):
        self.enableSensors()
        
        readings = {}
        readings["irSensorAmbientTemp"], readings["irTargetTemp"] = self.tag.IRtemperature.read()
        readings["humiditySensorAmbientTemp"], readings["humidity"] = self.tag.humidity.read()
        readings["barometerSensorAmbientTemp"], readings["pressure"] = self.tag.barometer.read()
        
        readings = {key: round(value, 2) for key, value in readings.items()}
        
        return readings

    def getData(self):
        readings = {}
        try:
            readings = self.getReadings()
        except:
            try:
                self.reconnect()
                readings = self.getReadings()
            except:
                readings['exception'] = 'Could not connect to the SensorTag'
            
        readings['time'] = str(datetime.now())[:-5]
        
        return readings
    
    def reconnect(self):
        print('Reconnect')
        self.tag.connect(self.tagAddress, 'random')
        
def getDeviceAddressFromFile():
    with open('deviceAddress.txt', 'r') as file:
        return file.read()

app = Flask(__name__)

sensorTag = ''

@app.before_request
def createInstance():
    global SENSORTAG_ADDRESS
    global sensorTag
    if request.endpoint == 'live':
        if SENSORTAG_ADDRESS:
            try:
                sensorTag = SensorTagDevice(SENSORTAG_ADDRESS)           
            except:
                pass
        else:
            SENSORTAG_ADDRESS = getDeviceAddressFromFile()
            try:
                sensorTag = SensorTagDevice(SENSORTAG_ADDRESS)           
            except:
                pass
    
    #if not sensorTag:
        #try:
            #sensorTag = SensorTagDevice(SENSORTAG_ADDRESS)
        #except:
            #print('Could not connect to the SensorTag')    

@app.route('/api/live', methods=["GET", "OPTIONS"])
def live():
    if request.method == "OPTIONS":
        res = make_response(jsonify({}), 200)
        res.headers['Access-Control-Allow-Origin'] = '*'
        res.headers['Access-Control-Allow-Headers'] = '*'
        return res
    
    readings = sensorTag.getData() 
    res = make_response(jsonify(readings), 200)
    res.headers['Access-Control-Allow-Origin'] = '*'
    return res

@app.route('/api/getDeviceAddress', methods=["GET"])
def getDeviceAddress():
    deviceAddress = {
        'address': getDeviceAddressFromFile()
    }
    
    res = make_response(jsonify(deviceAddress), 200)
    res.headers['Access-Control-Allow-Origin'] = '*'
    return res

@app.route('/api/getDevices', methods=["GET"])
def getDevices():
    devices = {}
    stream = os.popen('sudo timeout -s SIGINT 5s hcitool lescan')
    output = stream.read()
    
    devicesList = output.split('\n')[1:]
    for device in devicesList:
        deviceName = device.split(' ', 1)
        if len(deviceName) > 1:
            devices[deviceName[0]] = deviceName[1]
    if not devices:
        devices['00:00:00:00:00:00'] = 'Could not find any bluetooth device'
        
    res = make_response(jsonify(devices), 200)
    res.headers['Access-Control-Allow-Origin'] = '*'
    return res

@app.route('/api/setDeviceAddress', methods=["POST", "OPTIONS"])
def setDeviceAddress():
    global SENSORTAG_ADDRESS
    content = {}
    if request.method == 'POST':
        content = request.get_json()
        SENSORTAG_ADDRESS = content['address']
        
        with open('deviceAddress.txt', 'w') as file:
            file.write(content['address'])
        
    res = make_response(jsonify({}), 200)
    res.headers['Access-Control-Allow-Origin'] = '*'
    res.headers['Access-Control-Allow-Headers'] = '*'
    return res

@app.route('/live')
def socketSystem(ws):
    while True:
        message = ws.receive()
        if message == "update":
            readings = sensorTag.getData() 
            res = make_response(jsonify(readings), 200)
            res.headers['Access-Control-Allow-Origin'] = '*'
            ws.send(res)
        else:
            ws.send(message)

if __name__ == "__main__":
    app.run(host="0.0.0.0",port=int(os.getenv('PORT', 3001)))
