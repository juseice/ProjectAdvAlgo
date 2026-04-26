def check_bandwidth_constraint(network, source_id, target_id, data_size, required_bandwidth):
    path = network.get_path(source_id, target_id, data_size)
    if not path:
        return False
    bottleneck_bw = network.get_path_bandwidth(path)
    return bottleneck_bw >= required_bandwidth
