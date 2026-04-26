def check_memory_constraint(node, task, task_chain_id, task_index, simulator):
    prev_info = simulator.dt_placements.get(task_chain_id)
    if prev_info:
        prev_node_ids = prev_info['node_ids']
        if task_index < len(prev_node_ids) and prev_node_ids[task_index] == node.id:
            return True
    return node.available_memory >= task.memory_requirement
