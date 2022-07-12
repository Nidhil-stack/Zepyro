from bsp import board
from zdm import zdm

from components.dht11 import dht11
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



def floatToString(value, precision):                                                                        #convert float to string with given precision
    s = str(value)
    i = s.find('.')
    s1 = s[:i]
    s2 = s[i+1:]
    s2 = s2[:precision]
    return s1 + '.' + s2

def measureWindSpeed():
    global windSpeed
    i = 0
    oldWind = None                                                                                          #variable to store the last read value
    oldTime = None
    wind = hallSensor.hallSensor(33)
    while True:
        try:
            newWind = wind.read()
        except Exception as e:
            print(e)

        if newWind is None: continue

        if oldWind is 1 and newWind is 0:                                                                   #trigger the measurement on falling edge
            i = 0
            # print("ok")
            if oldTime is None:
                oldTime = time.millis()
            else:
                newTime = time.millis()
                windLock.acquire()
                windSpeed = 628/(newTime - oldTime)                                                         #calculate the wind speed using a lock for thread safety
                windLock.release()
                oldTime = newTime
        oldWind = newWind
        i+=1
        if i > 5000:
            i = 0
            windSpeed = 0
        sleep(5)

def httpSend():
    global measureBuffer
    while True:
        sleep(500)
        bufferLock.acquire()                                                                                #lock the buffer for thread safety
        if len(measureBuffer) < 10:
            bufferLock.release()
            continue
        httpBuffer=measureBuffer                                                                            #copy the buffer to a local variable
        measureBuffer.clear()
        bufferLock.release()                                                                                #unlock the buffer after clearing it
        try:
            conn = http.HTTP()                                                                              #create a new HTTP connection
            res = conn.post("http://192.168.108.54/post/index.php", body=json.dumps(httpBuffer))            #send the data to the server
            print("Sent")
        except Exception as e:
            print(e)
        if res.data != "OK":                                                                                #if the server returns an error, print it
            print("Error: " + res.data)
        conn.destroy()                                                                                      #destroy the connection
        httpBuffer.clear()                                                                                  #clear the copy buffer

def main():
    global measureBuffer
    global windSpeed

    try:                                                                                                    #try to initialize the bmp180 sensor
        bmp.init()
    except Exception as e:                                                                                  #if something goes wrong, print the error
        bmp = None
        print(e)

    oldHum, oldTemp, oldPressure, oldWindSpeed = None, None, None, None

    while True:

        hum, temp = dht11.read(dhtPin)                                                                      #read the humidity and temperature from the DHT11 sensor
        # temp = bmp.get_temp()
        pres =  bmp.get_pres()                                                                              #read the pressure from the BMP180 sensor

        windLock.acquire()
        wind_speed = windSpeed
        windLock.release()

        #print data to the console
        print("Temp:" + floatToString(temp, 1) + "C" + " Hum:" + floatToString(hum, 1) + "%" + " Pressure:" + floatToString(pres/1000, 1) + "kPa" + " WindSpeed:" + floatToString(wind_speed, 1) + "m/s")

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
        if oldWindSpeed is not wind_speed:
            lcd.setCursorPosition(7, 1)
            lcd.writeString("W: " + floatToString(wind_speed, 1) + "m/s")
            oldWindSpeed = wind_speed

        new = {"temp": temp, "hum": hum, "pres": pres, "windspeed": wind_speed}

        measureBuffer.append(new)
        bufferLock.release()

        try:
            agent.publish(new, "measurements")
        except Exception as e:
            print(e)

        sleep(2000)                                                                                             #DHT readings are pretty slow, so we wait a bit to avoid overloading the sensor




########################################################################################################################this code runs at the start of the program########################################################################################################################
isWifiConnected = False
try:                                                                                                            #try connecting to the wifi network
    wifi.configure(
        ssid = "",
        password="")
    wifi.start()
    ntp.sync_time()
    print(wifi.info())                                                                                          #print the wifi info
    isWifiConnected = True
except Exception as e:                                                                                          #if something goes wrong, print the error
        print("wifi exec",e)


windSpeed = 0                                                                                                   #initialize the wind speed to 0
measureBuffer = []                                                                                              #initialize the buffer for the measurements

bufferLock = threading.Lock()
windLock = threading.Lock()

windSpeedThread = threading.Thread(target=measureWindSpeed)                                                     #create a thread to measure the wind speed
httpThread = threading.Thread(target=httpSend)                                                                  #create a thread to send the measurements to the server
mainThread = threading.Thread(target=main)                                                                      #create a thread for the main function

lcd = lcd.LCD(I2C0)
dhtPin = D18
bmp = bmp180.BMP180(I2C0)

if isWifiConnected:
    agent = zdm.Agent()
    try:                                                                                                            #try to establish a connection to ZDM
        agent.start()
    except Exception as e:
        print(e)
else:
    print("Wifi not connected, agent not started")

windSpeedThread.start()                                                                                         #start all the threads
mainThread.start()
httpThread.start()
