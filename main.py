from components.dht11 import DHT11
from components.bmp180 import bmp180
from components.lcd import lcd

from libs.hallSensor import hallSensor

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
    wind = hallSensor.hallSensor(15)                                       #we define the Hall Effect Sensor on analog pin 15
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
        sleep(1)


dhtPin = D18
bmp = bmp180.BMP180(I2C0)
lcd = lcd.LCD(I2C0)

try:                                                            #try to initialize the bmp180 sensor
    bmp.init()
except Exception as e:                                          #if something goes wrong, print the error and
    bmp = None
    print(e)

oldHum, oldTemp, oldPressure, oldWindSpeed = None, None, None, None #initialize variables for the lcd update
windSpeed = 0                                                       #initialize the wind speed to 0

thread(measureWindSpeed)                                            #start the thread for measuring the wind speed

# main loop
while True:

    hum = 0;
    temp = bmp.get_temp()                #read the dht11 sensor
    pressure =  bmp.get_pres()                                             #read the pressure sensor
    #print data in the console
    print("Temp: " + floatToString(temp, 1) + "C" + " Hum: " + floatToString(hum, 1) + "%" + " Pressure: " + floatToString(pressure/1000, 1) + "kPa" + " WindSpeed: " + floatToString(windSpeed, 1) + "m/s")

    #if there is new data, print it on the LCD
    if oldTemp is not temp:
        lcd.setCursorPosition(0, 0)
        lcd.writeString("T: " + floatToString(temp, 1) + "C")
        oldTemp = temp
    if oldPressure is not pressure:
        lcd.setCursorPosition(9, 0)
        lcd.writeString("P: " + floatToString(pressure/1000, 1) + "kPa")
        oldPressure = pressure
    if oldHum is not hum:
        lcd.setCursorPosition(0, 1)
        lcd.writeString("H: " + str(int(hum)) + "%")
        oldHum = hum
    if oldWindSpeed is not windSpeed:
        lcd.setCursorPosition(7, 1)
        lcd.writeString("W: " + floatToString(windSpeed, 1) + "m/s")
        oldWindSpeed = windSpeed

    sleep(2000)                                                #DHT readings are pretty slow, so we wait a bit to avoid overloading the sensor
