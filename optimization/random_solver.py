import random
from objective import compute_run_cost, compute_mig_cost
from latency import estimate_aoi
from utils.logger import logger


def select_random_node(simulator, network, task_chain, user, alpha, beta, request_time):
    tasks = task_chain.tasks
    edge_nodes = network.get_edge_nodes()

    node_list = [random.choice(edge_nodes) for _ in tasks]

    sense, q_time, comp, res, migration = simulator.evaluate_step(
        node_list, task_chain, user, request_time
    )

    mig_delay = sum(t.migration_delay for t in tasks) if migration else 0.0
    aoi = estimate_aoi(sense, q_time, comp, res, migration, mig_delay)

    run_cost = compute_run_cost(node_list, task_chain)
    mig_cost = compute_mig_cost(task_chain) if migration else 0.0

    score = alpha * (run_cost + mig_cost) + beta * aoi
    metrics = {"aoi": aoi, "cost": run_cost + mig_cost, "migration": migration}

    return node_list, score, metrics
