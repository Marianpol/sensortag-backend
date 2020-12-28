import os
import sys
import threading
import subprocess
from datetime         import datetime
from flask            import Flask, request, jsonify, make_response
from flask_sockets    import Sockets
from bluepy.btle      import BTLEException
from bluepy.sensortag import SensorTag
from db               import Database

SENSORTAG_ADDRESS = ""
app = Flask(__name__)

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

    def getData(self, db=False):
        readings = {}
        try:
            readings = self.getReadings()
        except:
            try:
                self.reconnect()
                readings = self.getReadings()
            except:
                readings['exception'] = 'Could not connect to the SensorTag'
            
        readings['time'] = str(datetime.now())[:-7]
        
        if db:
            if len(readings) >= 6:
                outsideTemp = [
                    readings["irSensorAmbientTemp"],
                    readings["humiditySensorAmbientTemp"],
                    readings["barometerSensorAmbientTemp"]
                ]
                avgTemp = round(sum(outsideTemp) / len(outsideTemp),2)
                avgTempStr = str(avgTemp)
                readingsString = ('('
                        + str(readings["pressure"]) + ','
                        + str(readings["humidity"]) + ','
                        + str(readings["irTargetTemp"]) + ','
                        + avgTempStr + ",'"+ readings['time'] + "')")
                
                return readingsString
            
            return False
                    
        return readings
    
    def reconnect(self):
        print('Reconnect')
        self.tag.connect(self.tagAddress, 'random')
        
def getDeviceAddressFromFile():
    try:
        with open('deviceAddress.txt', 'r') as file:
            return file.read()
    except:
        pass

def runApp():
    appOutput = subprocess.Popen(["npm", "start"], cwd="./website")

sensorTag = ''

@app.before_request
def initInstance():
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

@app.route('/api/history', methods=["POST", "OPTIONS"])
def getHistory():
    content = {}
    if request.method == 'POST':
        content = request.get_json()
        fromDate = content['from']
        toDate = content['to']
        query = """SELECT pressure,
            humidity,
            target_temp,
            temperature,
            currentdate FROM readings
            WHERE DATE(currentdate) BETWEEN""" + " '" + fromDate + "'" + " AND " + "'" + toDate + "';"
        
        SensorTagDB = Database('SensorTag_DB')
        result = SensorTagDB.readTable(query)
        res = make_response(jsonify(result), 200)
        res.headers['Access-Control-Allow-Origin'] = '*'
        return res
               
    res = make_response(jsonify({}), 200)
    res.headers['Access-Control-Allow-Origin'] = '*'
    res.headers['Access-Control-Allow-Headers'] = '*'
    return res



def createInstance():
    global sensorTag
    SENSORTAG_ADDRESS = getDeviceAddressFromFile()
    
    if SENSORTAG_ADDRESS:
        sensorTag = SensorTagDevice(SENSORTAG_ADDRESS)
    
createInstance()

def pushReadings():
    if sensorTag:
        threading.Timer(60, pushReadings).start()

        readings = sensorTag.getData(True)
        if readings:
            SensorTagDB = Database('SensorTag_DB')
            SensorTagDB.writeReading(readings)
            result = SensorTagDB.readTable('select * from readings')
            print(readings)
    else:
        createInstance()
    
pushReadings()
runApp()

if __name__ == "__main__":
    app.run(host="0.0.0.0",port=int(os.getenv('PORT', 3001)))
