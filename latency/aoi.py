def estimate_aoi(sense_delay, queue_delay, compute_delay, response_delay,
                 migration=False, migration_delay=0.0):
    """
    Delta_{j,q} = D^base_{j,q} + z_{j,n} * D^mig_j
    D^base = sense + queue + compute + response
    """
    base = sense_delay + queue_delay + compute_delay + response_delay
    return base + (migration_delay if migration else 0.0)


def compute_aoi(arrival_time, generation_time):
    return arrival_time - generation_time
