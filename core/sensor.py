from core.node import Node


class Sensor(Node):
    def __init__(self, id, data_size, period=1.0):
        super().__init__(id)
        self.data_size = data_size
        self.period = period
        self.last_generation_time = 0

    def generate_update(self, current_time):
        self.last_generation_time = current_time
        return current_time
