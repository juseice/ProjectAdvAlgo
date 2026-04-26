from latency.transmission import compute_transmission_delay
from latency.sensing import compute_sensing_delay


class Simulator:
    def __init__(self, network, dt_ttl=10.0):
        self.network = network
        self.dt_ttl = dt_ttl
        self.node_available_time = {node.id: 0.0 for node in network.get_edge_nodes()}
        self.dt_placements = {}
        self.dt_last_access = {}
        self.dt_history_aoi = {}

    def get_dt_placement(self, task_chain_id):
        info = self.dt_placements.get(task_chain_id)
        return info['node_ids'] if info else None

    def get_dt_last_aoi(self, task_chain_id):
        return self.dt_history_aoi.get(task_chain_id, 0.0)

    def get_node_available_memory(self, node_id):
        node = self.network.get_node(node_id)
        return node.available_memory if node else 0.0

    def cleanup_expired_dts(self, current_time):
        expired_dts = []
        for dt_id, last_time in self.dt_last_access.items():
            if current_time - last_time > self.dt_ttl:
                expired_dts.append(dt_id)

        evicted_info = []
        for dt_id in expired_dts:
            info = self.dt_placements[dt_id]
            for node_id, mem_req in zip(info['node_ids'], info['memories']):
                node = self.network.get_node(node_id)
                node.available_memory += mem_req
            del self.dt_placements[dt_id]
            del self.dt_last_access[dt_id]
            evicted_info.append((dt_id, info['node_ids'], info['memories']))

        return evicted_info

    def _compute_chain_latency(self, node_list, task_chain, user, request_time):
        tasks = task_chain.tasks
        sensor_id = task_chain.sensor_id
        sensor = self.network.get_node(sensor_id)
        raw_data_size = sensor.data_size

        sense_delay = compute_sensing_delay(
            self.network, sensor_id, node_list[0].id, raw_data_size
        )
        current_time = request_time + sense_delay

        queue_delays = []
        compute_times = []
        inter_delays = []

        for i, (task, node) in enumerate(zip(tasks, node_list)):
            start_time = max(current_time, self.node_available_time[node.id])
            queue_delays.append(start_time - current_time)

            comp = task.workload / node.compute_power
            compute_times.append(comp)
            finish_time = start_time + comp

            if i < len(tasks) - 1:
                next_node = node_list[i + 1]
                if node.id != next_node.id:
                    out_size = task.output_data_size
                    path = self.network.get_path(node.id, next_node.id, out_size)
                    bw = self.network.get_path_bandwidth(path) if path else 0
                    inter = compute_transmission_delay(out_size, bw) if bw > 0 else float('inf')
                else:
                    inter = 0.0
                inter_delays.append(inter)
                current_time = finish_time + inter
            else:
                current_time = finish_time

        result_size = 1.0
        path_down = self.network.get_path(node_list[-1].id, user.id, result_size)
        bw_down = self.network.get_path_bandwidth(path_down) if path_down else 0
        response_delay = (
            compute_transmission_delay(result_size, bw_down) if bw_down > 0 else float('inf')
        )

        return sense_delay, queue_delays, compute_times, inter_delays, response_delay

    def evaluate_step(self, node_list, task_chain, user, request_time):
        sense_delay, queue_delays, compute_times, inter_delays, response_delay = \
            self._compute_chain_latency(node_list, task_chain, user, request_time)

        prev_info = self.dt_placements.get(task_chain.id)
        prev_node_ids = prev_info['node_ids'] if prev_info else None
        new_node_ids = [n.id for n in node_list]
        is_migrated = 1 if (prev_node_ids != new_node_ids) else 0

        return (
            sense_delay,
            sum(queue_delays),
            sum(compute_times) + sum(inter_delays),
            response_delay,
            is_migrated,
        )

    def commit_step(self, node_list, task_chain, user, request_time):
        tasks = task_chain.tasks

        sense_delay, queue_delays, compute_times, inter_delays, response_delay = \
            self._compute_chain_latency(node_list, task_chain, user, request_time)

        sensor_id = task_chain.sensor_id
        sense_delay_val = sense_delay
        current_time = request_time + sense_delay_val

        for i, (task, node) in enumerate(zip(tasks, node_list)):
            start_time = max(current_time, self.node_available_time[node.id])
            finish_time = start_time + compute_times[i]
            self.node_available_time[node.id] = finish_time
            current_time = finish_time + (inter_delays[i] if i < len(inter_delays) else 0)

        prev_info = self.dt_placements.get(task_chain.id)
        prev_node_ids = prev_info['node_ids'] if prev_info else None
        new_node_ids = [n.id for n in node_list]
        is_migrated = 1 if (prev_node_ids != new_node_ids) else 0

        if is_migrated:
            if prev_info is not None:
                for prev_node_id, mem in zip(prev_info['node_ids'], prev_info['memories']):
                    prev_node = self.network.get_node(prev_node_id)
                    prev_node.available_memory += mem

            new_memories = []
            for task, node in zip(tasks, node_list):
                node.available_memory -= task.memory_requirement
                new_memories.append(task.memory_requirement)

            self.dt_placements[task_chain.id] = {
                'node_ids': new_node_ids,
                'memories': new_memories,
            }

        self.dt_last_access[task_chain.id] = request_time
        real_aoi = (
            sense_delay
            + sum(queue_delays)
            + sum(compute_times)
            + sum(inter_delays)
            + response_delay
        )
        self.dt_history_aoi[task_chain.id] = real_aoi

        return (
            sense_delay,
            sum(queue_delays),
            sum(compute_times) + sum(inter_delays),
            response_delay,
            is_migrated,
        )
