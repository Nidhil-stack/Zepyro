import gpio
import adc

class hallSensor(int):                                      #class to read the hall sensor and transform its analog value to a digital value
    def __init__(self, pin):                                #constructor, saves the gpio number and initializes the gpio pin as input
        self.pin = pin
        gpio.mode(self.pin, INPUT)

    def read(self):                                         #read the analog value of the hall sensor and returns a digital one
        value = adc.read(self.pin)                          #read the analog value

        if value > 2000:                                    #add some hysteresis to the value for stability reasons
            self.old = 1
            return 1
        else:
            if value < 1900:
                self.old = 0
                return 0
            else:
                return self.old                             #return the last value if the value is not stable
