import itertools
from objective import compute_run_cost, compute_mig_cost
from latency import estimate_aoi
from utils.logger import logger


def select_best_node(simulator, network, task_chain, user, alpha, beta, request_time):
    tasks = task_chain.tasks
    edge_nodes = network.get_edge_nodes()

    best_score = float('inf')
    best_node_list = None
    best_metrics = None

    for node_list in itertools.product(edge_nodes, repeat=len(tasks)):
        sense, q_time, comp, res, migration = simulator.evaluate_step(
            node_list, task_chain, user, request_time
        )

        mig_delay = sum(t.migration_delay for t in tasks) if migration else 0.0
        aoi = estimate_aoi(sense, q_time, comp, res, migration, mig_delay)

        run_cost = compute_run_cost(node_list, task_chain)
        mig_cost = compute_mig_cost(task_chain) if migration else 0.0

        # Phi per request: alpha*(C^run + C^mig*z) + beta*Delta
        score = alpha * (run_cost + mig_cost) + beta * aoi

        if score < best_score:
            best_score = score
            best_node_list = list(node_list)
            best_metrics = {"aoi": aoi, "cost": run_cost + mig_cost, "migration": migration}

    return best_node_list, best_score, best_metrics
