def compute_run_cost(node_list, task_chain):
    """C^run_{j,n} = sum_j node.cost * workload / compute_power"""
    return sum(
        node.cost * (task.workload / node.compute_power)
        for node, task in zip(node_list, task_chain.tasks)
    )


def compute_mig_cost(task_chain):
    """C^mig_j = sum_j task.deployment_cost  (charged only when z=1)"""
    return sum(task.deployment_cost for task in task_chain.tasks)


def compute_cost(node_list, task_chain, migration=False):
    """alpha-side cost: C^run + C^mig * z"""
    return compute_run_cost(node_list, task_chain) + (compute_mig_cost(task_chain) if migration else 0.0)
