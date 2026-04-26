def compute_task_delay(task, node):
    return task.workload / node.compute_power


def compute_chain_delay(task_chain, node):
    return sum(compute_task_delay(task, node) for task in task_chain.tasks)


def compute_chain_delay_distributed(task_chain, node_list):
    return sum(
        compute_task_delay(task, node)
        for task, node in zip(task_chain.tasks, node_list)
    )
