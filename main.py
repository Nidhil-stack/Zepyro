# from bsp import board
from zdm import zdm

from components.dht11 import DHT11
from components.bmp180 import bmp180

from protocols import ntp
from protocols import http

from networking import wifi

from libs.lcd import lcd
from libs.hallSensor import hallSensor

import mcu
import json
import adc
import gpio
import threading
import time



def floatToString(value, precision):                                               #convert float to string with given precision
    s = str(value)
    i = s.find('.')
    s1 = s[:i]
    s2 = s[i+1:]
    s2 = s2[:precision]
    return s1 + '.' + s2

def measureWindSpeed():
    global windSpeed
    i = 0                                      #global variable to be able to read it from the main thread
    oldWind = None
    oldTime = None
    wind = hallSensor.hallSensor(33)                                       #we define the Hall Effect Sensor on analog pin 15
    while True:
        try:
            newWind = wind.read()
        except Exception as e:
            print(e)                                   #read the Hall Effect Sensor
        if newWind is None: continue
        if oldWind is 1 and newWind is 0:
            i = 0
            # print("ok")                       #we trigger the wind speed measurement on the falling edge of the Hall Effect Sensor
            if oldTime is None:
                oldTime = time.millis()
            else:
                newTime = time.millis()
                windSpeed = 628/(newTime - oldTime)            #calculate the wind speed
                oldTime = newTime
        oldWind = newWind
        i+=1
        if i > 5000:
            i = 0
            windSpeed = 0
        sleep(5)

def httpSend():
    global measureBuffer
    #bufferLock.acquire()
    # bufferLock.release()
    # connectionLock.acquire()
    conn = http.HTTP()
    res = conn.post("http://192.168.108.54/post/index.php", body=json.dumps(measureBuffer))
    if res.data != "OK":
        print("Error: " + res.data)
        raise Exception("Query Error")
    conn.destroy()
    measureBuffer.clear()
    # connectionLock.release()

def newMeasure(time, temperature, humidity, pressure, wind_speed):
    new = {
    "time": time,
    "temp": temperature,
    "hum": humidity,
    "pres": pressure,
    "windspeed": wind_speed
    }
    return new

def main():
    global measureBuffer
    global windSpeed

    try:                                                            #try to initialize the bmp180 sensor
        bmp.init()
    except Exception as e:                                          #if something goes wrong, print the error
        bmp = None
        print(e)

    oldHum, oldTemp, oldPressure, oldWindSpeed = None, None, None, None

    while True:

        hum =40.3;
        temp = bmp.get_temp()                #read the dht11 sensor
        pres =  bmp.get_pres()                                             #read the pressure sensor
        #print data in the console
        print("Temp: " + floatToString(temp, 1) + "C" + " Hum: " + floatToString(hum, 1) + "%" + " Pressure: " + floatToString(pres/1000, 1) + "kPa" + " WindSpeed: " + floatToString(windSpeed, 1) + "m/s")

        #if there is new data, print it on the LCD
        if oldTemp is not temp:
            lcd.setCursorPosition(0, 0)
            lcd.writeString("T: " + floatToString(temp, 1) + "C")
            oldTemp = temp
        if oldPressure is not pres:
            lcd.setCursorPosition(9, 0)
            lcd.writeString("P: " + floatToString(pres/1000, 1) + "kPa")
            oldPressure = pres
        if oldHum is not hum:
            lcd.setCursorPosition(0, 1)
            lcd.writeString("H: " + str(int(hum)) + "%")
            oldHum = hum
        if oldWindSpeed is not windSpeed:
            lcd.setCursorPosition(7, 1)
            lcd.writeString("W: " + floatToString(windSpeed, 1) + "m/s")
            oldWindSpeed = windSpeed
        new = newMeasure(ntp.get_time(unix_timestamp=True), temp, hum, pres, windSpeed)
        measureBuffer.append(new)
        print(new)
        connectionLock.acquire()
        agent.publish(new, "measurements")
        connectionLock.release()
        if len(measureBuffer) > 9:
            try:
                httpSend()
                print("data sent!")
            except Exception as e:
                print(e)

        sleep(2000)                                                #DHT readings are pretty slow, so we wait a bit to avoid overloading the sensor


#try connecting to the wifi network
try:
    wifi.configure(
        ssid = "Nick",
        password="ciao1234")
    wifi.start()
    ntp.sync_time()
    print(wifi.info())
except Exception as e:
        print("wifi exec",e)


windSpeed = 0                                                       #initialize the wind speed to 0
measureBuffer = []                                                  #initialize the buffer for the measurements

# bufferLock = threading.Lock()                                       #lock for the buffer
# connectionLock = threading.Lock()                                   #lock for the connection

windSpeedThread = threading.Thread(target=measureWindSpeed)
httpThread = threading.Thread(target=httpSend)                                #start the thread for sending the measurements
mainThread = threading.Thread(target=main)                                    #start the thread for the main loop

lcd = lcd.LCD(I2C0)
dhtPin = D18
bmp = bmp180.BMP180(I2C0)
agent = zdm.Agent()
agent.start()

windSpeedThread.start()
mainThread.start()
