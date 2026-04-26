import itertools
from utils.logger import logger
from latency.sensing import compute_sensing_delay
from latency.transmission import compute_transmission_delay


def solve_dp_offline(network, request_stream, alpha, beta):
    """
    DP-ODA: minimizes Phi = sum_{j,n} [ alpha*(C^run + C^mig*z) + beta*Delta ]

    State at each step: tuple of node IDs, one per task in the chain.
    z_{j,n} = 1  iff placement tuple changes from step n-1 to n.
    Delta_{j,q} = D^base_{j,q} + z_{j,n} * D^mig_j
    """
    N = len(request_stream)
    if N == 0:
        return []

    nodes = network.get_edge_nodes()

    def get_base_metrics(req, node_list):
        """Return (aoi_base, run_cost, mig_cost_total, mig_delay_total) for a placement."""
        tasks = req.task_chain.tasks
        sensor_id = req.task_chain.sensor_id
        sensor = network.get_node(sensor_id)

        path_up = network.get_path(sensor_id, node_list[0].id, sensor.data_size)
        path_down = network.get_path(node_list[-1].id, req.user.id, 1.0)

        bw_up = network.get_path_bandwidth(path_up) if path_up else 1.0
        sense_delay = compute_sensing_delay(network, sensor_id, node_list[0].id, sensor.data_size)

        total_comp = 0.0
        total_inter = 0.0
        run_cost = 0.0

        for i, (task, node) in enumerate(zip(tasks, node_list)):
            comp = task.workload / node.compute_power
            total_comp += comp
            run_cost += node.cost * comp

            if i < len(tasks) - 1:
                next_node = node_list[i + 1]
                if node.id != next_node.id:
                    out_size = task.output_data_size
                    path_inter = network.get_path(node.id, next_node.id, out_size)
                    bw_inter = network.get_path_bandwidth(path_inter) if path_inter else 1.0
                    total_inter += compute_transmission_delay(out_size, bw_inter)

        bw_down = network.get_path_bandwidth(path_down) if path_down else 1.0
        res_delay = compute_transmission_delay(1.0, bw_down)

        aoi_base = sense_delay + total_comp + total_inter + res_delay
        mig_cost = sum(t.deployment_cost for t in tasks)
        mig_delay = sum(t.migration_delay for t in tasks)

        return aoi_base, run_cost, mig_cost, mig_delay

    # Phase 1: Pre-compute base metrics for every (request, placement) pair
    logger.info("  >> Pre-computation pass...")
    metrics_cache = [{} for _ in range(N)]

    for n in range(N):
        req_n = request_stream[n]
        n_tasks = len(req_n.task_chain.tasks)
        for node_list in itertools.product(nodes, repeat=n_tasks):
            key = tuple(node.id for node in node_list)
            metrics_cache[n][key] = get_base_metrics(req_n, node_list)

    n_states = len(metrics_cache[0])
    logger.info(f"     States per step: {n_states}")
    logger.info("  >> Forward DP pass...")

    # Phase 2: Forward DP
    # dp_table[n][key] = minimum cumulative Phi from step 0..n
    dp_table = [{} for _ in range(N)]
    pre_placement = [{} for _ in range(N)]
    metrics_record = [{} for _ in range(N)]   # (aoi, total_cost, is_mig)

    # Initialise step 0 — first placement always counts as migration (fresh deploy)
    for key, (aoi_base, run_cost, mig_cost, mig_delay) in metrics_cache[0].items():
        aoi = aoi_base + mig_delay          # z=1 at step 0
        step_cost = run_cost + mig_cost
        dp_table[0][key] = alpha * step_cost + beta * aoi
        pre_placement[0][key] = None
        metrics_record[0][key] = (aoi, step_cost, True)

    for n in range(1, N):
        for key, (aoi_base, run_cost, mig_cost, mig_delay) in metrics_cache[n].items():
            best_cum = float('inf')
            best_pre = None
            best_aoi = None
            best_step_cost = None
            best_is_mig = False

            for prev_key, prev_cum in dp_table[n - 1].items():
                if prev_cum == float('inf'):
                    continue

                z = 1 if key != prev_key else 0
                aoi = aoi_base + z * mig_delay
                step_cost = run_cost + z * mig_cost
                cum = prev_cum + alpha * step_cost + beta * aoi

                if cum < best_cum:
                    best_cum = cum
                    best_pre = prev_key
                    best_aoi = aoi
                    best_step_cost = step_cost
                    best_is_mig = bool(z)

            dp_table[n][key] = best_cum
            pre_placement[n][key] = best_pre
            metrics_record[n][key] = (best_aoi, best_step_cost, best_is_mig)

    # Phase 3: Backward traceback
    opt_last_key = min(dp_table[N - 1], key=lambda k: dp_table[N - 1][k])
    if dp_table[N - 1][opt_last_key] == float('inf'):
        logger.error("  >> DP solve failed: no feasible path found!")
        return []

    opt_path = []
    curr_key = opt_last_key
    for n in range(N - 1, -1, -1):
        aoi, cost, mig = metrics_record[n][curr_key]
        opt_path.append({
            'req': request_stream[n].id,
            'node_ids': list(curr_key),
            'aoi': aoi,
            'cost': cost,
            'migrated': mig,
        })
        curr_key = pre_placement[n][curr_key]

    opt_path.reverse()
    return opt_path
