import gpio
import adc

class hallSensor(int):
    def __init__(self, pin):
        self.pin = pin
        gpio.mode(self.pin, INPUT)

    def read(self):
        value = adc.read(self.pin)

        if value > 2000:
            self.old = 1
            return 1
        else:
            if value < 1900:
                self.old = 0
                return 0
            else:
                return self.old
