import os
import sys
from datetime         import datetime
from flask            import Flask, jsonify
from bluepy.btle      import BTLEException
from bluepy.sensortag import SensorTag

SENSORTAG_ADDRESS = "34:B1:F7:D5:0C:46"

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
        
        return jsonify(readings)
    
    def reconnect(self):
        self.tag.connect(self.tagAddress, self.tag.addrType)

app = Flask(__name__)

#sensorTag = 0

@app.before_first_request
def createInstance():
    global sensorTag
    sensorTag = SensorTagDevice(SENSORTAG_ADDRESS)
    
    #if not sensorTag:
        #try:
            #sensorTag = SensorTagDevice(SENSORTAG_ADDRESS)
        #except:
            #print('Could not connect to the SensorTag')    

@app.route('/', methods=["GET"])
def home():
    return sensorTag.getData()
    #if sensorTag:
        #return  sensorTag.getData()
    #return jsonify({'exception': 'Could not connect to the SensorTag'})

if __name__ == "__main__":
    app.run(host="0.0.0.0",port=int(os.getenv('PORT', 4444)))
