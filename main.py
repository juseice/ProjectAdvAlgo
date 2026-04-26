from environment import Simulator
from latency import estimate_aoi
from objective import compute_cost
from optimization.brute_solver import select_best_node
from optimization.random_solver import select_random_node
from optimization.dp_solver import solve_dp_offline
from utils.logger import logger
from utils.data_generator import generate_synthetic_dataset, save_dataset, load_dataset
from utils.visualization import plot_network_topology, plot_comparative_results
import os


ALPHA = 1.0  # cost weight
BETA = 1.0   # AoI weight


def run_online_solver(algo_name, solver_func, net, request_stream, alpha=ALPHA, beta=BETA):
    logger.info(f"\n========== {algo_name} ==========")
    sim = Simulator(net, dt_ttl=10.0)
    history = []

    for req in request_stream:
        evicted = sim.cleanup_expired_dts(req.trigger_time)
        for dt_id, node_ids, _ in evicted:
            logger.debug(f"  [Evicted] {dt_id} from nodes {node_ids}")

        node_list, score, _ = solver_func(
            sim, net, req.task_chain, req.user, alpha, beta, req.trigger_time
        )

        if node_list is not None:
            sense, queue, comp, res, mig = sim.commit_step(
                node_list, req.task_chain, req.user, req.trigger_time
            )
            mig_delay = sum(t.migration_delay for t in req.task_chain.tasks) if mig else 0.0
            aoi = estimate_aoi(sense, queue, comp, res, mig, mig_delay)
            cost = compute_cost(node_list, req.task_chain, mig)
            history.append({'req': req.id, 'aoi': aoi, 'cost': cost, 'migrated': mig})
            logger.info(
                f"  [Req {req.id:>3}] nodes={[n.id for n in node_list]} "
                f"AoI={aoi:.3f}  Cost={cost:.3f}  mig={mig}"
            )
        else:
            logger.warning(f"  [Req {req.id:>3}] No feasible deployment found")

    return history


def run_dp_real(net, request_stream, alpha=ALPHA, beta=BETA):
    logger.info(f"\n========== DP Real ==========")
    dp_plan = solve_dp_offline(net, request_stream, alpha, beta)
    if not dp_plan:
        logger.error("DP solve failed, returning empty history")
        return []

    sim = Simulator(net, dt_ttl=10.0)
    history = []

    for i, req in enumerate(request_stream):
        sim.cleanup_expired_dts(req.trigger_time)
        planned_node_ids = dp_plan[i]['node_ids']
        node_list = [net.get_node(nid) for nid in planned_node_ids]

        try:
            sense, queue, comp, res, mig = sim.commit_step(
                node_list, req.task_chain, req.user, req.trigger_time
            )
            mig_delay = sum(t.migration_delay for t in req.task_chain.tasks) if mig else 0.0
            aoi = estimate_aoi(sense, queue, comp, res, mig, mig_delay)
            cost = compute_cost(node_list, req.task_chain, mig)
            history.append({'req': req.id, 'aoi': aoi, 'cost': cost, 'migrated': mig})
            logger.info(
                f"  [Req {req.id:>3}] nodes={planned_node_ids} "
                f"AoI={aoi:.3f}  Cost={cost:.3f}  mig={mig}"
            )
        except RuntimeError as e:
            logger.error(f"  [Req {req.id:>3}] Commit failed: {e}")

    return history


def print_summary(name, history):
    if not history:
        print(f"  {name}: no results")
        return
    avg_aoi = sum(h['aoi'] for h in history) / len(history)
    avg_cost = sum(h['cost'] for h in history) / len(history)
    mig_count = sum(1 for h in history if h['migrated'])
    print(f"  {name:<22}  avg_AoI={avg_aoi:.4f}  avg_Cost={avg_cost:.4f}  migrations={mig_count}/{len(history)}")


def main():
    dataset_path = "data/dataset.pkl"

    if not os.path.exists(dataset_path):
        logger.info("Generating synthetic dataset...")
        dataset = generate_synthetic_dataset(
            num_edge_nodes=10,
            num_sensors=3,
            num_users=5,
            num_dt_services=4,
            total_requests=50,
            arrival_rate=0.2,
            seed=42
        )
        save_dataset(dataset, dataset_path)
    else:
        dataset = load_dataset(dataset_path)

    net = dataset['network']
    request_stream = dataset['request_stream']

    logger.info(f"Dataset: {len(network_nodes := net.get_edge_nodes())} edge nodes, {len(request_stream)} requests")

    # Network topology
    plot_network_topology(net)

    # 1. Random solver
    history_random = run_online_solver("Random Baseline", select_random_node, net, request_stream)

    # 2. Brute-force greedy solver
    history_brute = run_online_solver("Greedy Brute-Force", select_best_node, net, request_stream)

    # 3. DP Oracle (offline, no real simulator state)
    logger.info(f"\n========== DP Oracle ==========")
    dp_oracle = solve_dp_offline(net, request_stream, ALPHA, BETA)
    history_dp_oracle = [
        {'req': s['req'], 'aoi': s['aoi'], 'cost': s['cost'], 'migrated': s['migrated']}
        for s in dp_oracle
    ]

    # 4. DP Real (offline plan executed through real simulator)
    history_dp_real = run_dp_real(net, request_stream)

    # Summary
    print("\n========== Results Summary ==========")
    print_summary("Random",         history_random)
    print_summary("Greedy Brute",   history_brute)
    print_summary("DP Oracle",      history_dp_oracle)
    print_summary("DP Real",        history_dp_real)

    # Comparative visualization
    plot_comparative_results({
        'Random Baseline': history_random,
        'Greedy Best':     history_brute,
        'DP Ideal':        history_dp_oracle,
        'DP Real':         history_dp_real,
    })


if __name__ == "__main__":
    main()
