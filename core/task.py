from core.basic_object import BasicObject


class Task(BasicObject):
    def __init__(self, id, workload, deployment_cost, memory_requirement, output_data_size=0.0, migration_delay=0.0):
        super().__init__(id)
        self.workload = workload
        self.deployment_cost = deployment_cost   # C^mig per task
        self.memory_requirement = memory_requirement
        self.output_data_size = output_data_size
        self.migration_delay = migration_delay   # D^mig per task


class TaskChain(BasicObject):
    def __init__(self, id, tasks, sensor_id, required_bandwidth=2.0):
        super().__init__(id)
        self.tasks = tasks
        self.sensor_id = sensor_id
        self.required_bandwidth = required_bandwidth
