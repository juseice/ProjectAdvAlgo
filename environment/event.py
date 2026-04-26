import random
from core.request import Request


def generate_poisson_requests(users, task_chains, arrival_rate=1.0, total_requests=20, seed=None):
    if seed is not None:
        random.seed(seed)

    requests = []
    current_time = 0.0

    for i in range(1, total_requests + 1):
        inter_arrival_time = random.expovariate(arrival_rate)
        current_time += inter_arrival_time

        user = random.choice(users)
        dt = random.choice(task_chains)

        req = Request(
            req_id=i,
            trigger_time=current_time,
            user=user,
            task_chain=dt
        )
        requests.append(req)

    return requests
