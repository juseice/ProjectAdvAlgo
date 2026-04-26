import math
import os

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import seaborn as sns
from pathlib import Path

from core import EdgeNode, Sensor, UserNode

plt.rcParams['axes.unicode_minus'] = False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_geo_dict_from_csv(csv_path):
    geo_dict = {}
    if csv_path and os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            for _, row in df.iterrows():
                geo_dict[str(row['Node_ID'])] = (row['Longitude'], row['Latitude'])
            print(f"Loaded {len(geo_dict)} node geo-coordinates from CSV.")
        except Exception as e:
            print(f"Failed to read CSV coordinates: {e}")
    return geo_dict


# ---------------------------------------------------------------------------
# Network topology plots
# ---------------------------------------------------------------------------

def plot_network_topology(network):
    """
    Three-layer layout: Sensor → Edge Node → User.
    """
    G = network.graph

    sensors, edge_nodes, users = [], [], []
    for node_id, data in G.nodes(data=True):
        node = data.get('node')
        if isinstance(node, Sensor):
            sensors.append(node_id)
        elif isinstance(node, UserNode):
            users.append(node_id)
        else:
            edge_nodes.append(node_id)

    sensors.sort()
    edge_nodes.sort()
    users.sort()

    X_SPACE = 10.0
    pos = {}

    for i, nid in enumerate(sensors):
        total = (len(sensors) - 1) * 4.0
        pos[nid] = (0, total / 2 - i * 4.0)

    for i, nid in enumerate(edge_nodes):
        total = (len(edge_nodes) - 1) * 3.0
        pos[nid] = (X_SPACE, total / 2 - i * 3.0)

    for i, nid in enumerate(users):
        total = (len(users) - 1) * 5.0
        pos[nid] = (X_SPACE * 2, total / 2 - i * 5.0)

    plt.figure(figsize=(16, 10), dpi=100)
    BASE = 1600

    nx.draw_networkx_nodes(G, pos, nodelist=sensors,    node_color='#4caf50', node_shape='^',
                           node_size=BASE * 0.8, label='Sensor',    edgecolors='black', linewidths=1.5)
    nx.draw_networkx_nodes(G, pos, nodelist=edge_nodes, node_color='#2196f3', node_shape='o',
                           node_size=BASE,        label='Edge Node', edgecolors='black', linewidths=1.5)
    nx.draw_networkx_nodes(G, pos, nodelist=users,      node_color='#f44336', node_shape='s',
                           node_size=BASE * 0.8, label='User',       edgecolors='black', linewidths=1.5)

    nx.draw_networkx_edges(G, pos, arrowstyle='-|>', arrowsize=25,
                           edge_color='#757575', width=1.5, alpha=0.6)

    label_pos = {k: (v[0], v[1] - 0.7) for k, v in pos.items()}
    nx.draw_networkx_labels(G, label_pos, font_size=12, font_weight='bold', font_color='#212121')

    edge_labels = {(u, v): f"{d['edge'].bandwidth:.0f}M" for u, v, d in G.edges(data=True)}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=9, font_color='#424242',
                                 bbox=dict(facecolor='white', edgecolor='none', alpha=0.7,
                                           boxstyle='round,pad=0.2'),
                                 label_pos=0.3)

    plt.title("Heterogeneous Edge Network Topology (Layered View)", fontsize=20, fontweight='bold', pad=20)
    plt.gca().margins(0.1)
    plt.legend(scatterpoints=1, loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=3, fontsize=12, frameon=False)
    plt.axis('off')
    plt.tight_layout()
    plt.show()


def plot_macro_topology(network, geo_csv_path=None):
    """
    Lightweight overview for large networks (50+ nodes). No text labels, tiny nodes.
    """
    G = network.graph
    sensors, edge_nodes, users = [], [], []
    pos = {}

    external_geo = _load_geo_dict_from_csv(geo_csv_path)

    for node_id, data in G.nodes(data=True):
        node = data.get('node')
        t = type(node).__name__
        if t == 'Sensor':
            sensors.append(node_id)
        elif t == 'UserNode':
            users.append(node_id)
        else:
            edge_nodes.append(node_id)

        nstr = str(node.id)
        if nstr in external_geo:
            pos[node_id] = external_geo[nstr]
        elif hasattr(node, 'lon') and hasattr(node, 'lat'):
            pos[node_id] = (node.lon, node.lat)

    if not pos:
        pos = nx.spring_layout(G, k=0.8, iterations=150, seed=42)

    plt.figure(figsize=(12, 12), dpi=150)
    nx.draw_networkx_nodes(G, pos, nodelist=edge_nodes, node_color='#2196f3',
                           node_shape='o', node_size=80,  label='Edge Node', alpha=0.9,
                           edgecolors='white', linewidths=0.5)
    nx.draw_networkx_nodes(G, pos, nodelist=sensors,    node_color='#4caf50',
                           node_shape='^', node_size=40,  label='Sensor',    alpha=0.9,
                           edgecolors='white', linewidths=0.5)
    nx.draw_networkx_nodes(G, pos, nodelist=users,      node_color='#f44336',
                           node_shape='s', node_size=6,   label='User',      alpha=0.9,
                           edgecolors='white', linewidths=0.5)
    nx.draw_networkx_edges(G, pos, edge_color='#BDBDBD', width=0.6, alpha=0.3, arrows=False)

    plt.legend(scatterpoints=1, loc='upper right', fontsize=12, framealpha=0.9, edgecolor='#E0E0E0')
    plt.axis('off')
    plt.tight_layout()
    plt.show()

    return pos


def plot_infrastructure_topology(network, geo_csv_path=None, fixed_pos=None):
    """
    Infrastructure view: Edge Nodes + Sensors only (no users).
    """
    G = network.graph
    infra_nodes = [nid for nid, d in G.nodes(data=True)
                   if type(d.get('node')).__name__ in ('EdgeNode', 'Sensor')]
    G_infra = G.subgraph(infra_nodes)

    sensors, edge_nodes = [], []
    pos = {}

    for node_id, data in G_infra.nodes(data=True):
        node = data.get('node')
        if type(node).__name__ == 'Sensor':
            sensors.append(node_id)
        else:
            edge_nodes.append(node_id)

    if fixed_pos is not None:
        pos = {n: fixed_pos[n] for n in infra_nodes if n in fixed_pos}
    else:
        ext = _load_geo_dict_from_csv(geo_csv_path)
        for node_id, data in G_infra.nodes(data=True):
            nstr = str(data['node'].id)
            if nstr in ext:
                pos[node_id] = ext[nstr]
        if not pos:
            pos = nx.spring_layout(G_infra, k=0.4, iterations=150, seed=42)

    plt.figure(figsize=(10, 10), dpi=150)
    nx.draw_networkx_nodes(G_infra, pos, nodelist=edge_nodes, node_color='#2196f3',
                           node_shape='o', node_size=80, label='Edge Node', edgecolors='white', linewidths=1)
    nx.draw_networkx_nodes(G_infra, pos, nodelist=sensors,    node_color='#4caf50',
                           node_shape='^', node_size=40, label='Sensor',    edgecolors='white', linewidths=1)
    nx.draw_networkx_edges(G_infra, pos, edge_color='#9E9E9E', width=1.0, alpha=0.5, arrows=False)

    plt.legend(scatterpoints=1, loc='upper right', fontsize=12, framealpha=0.9)
    plt.axis('off')
    plt.tight_layout()
    plt.show()


# ---------------------------------------------------------------------------
# Simulation result plots
# ---------------------------------------------------------------------------

def plot_simulation_results(metrics_history):
    """
    AoI and Cost trend for a single algorithm run.
    """
    if not metrics_history:
        print("No data to plot.")
        return

    reqs = [d['req'] for d in metrics_history]
    aois = [d['aoi'] for d in metrics_history]
    costs = [d['cost'] for d in metrics_history]
    mig_reqs = [d['req'] for d in metrics_history if d['migrated']]
    mig_aois = [d['aoi'] for d in metrics_history if d['migrated']]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

    ax1.plot(reqs, aois, marker='o', linestyle='-', color='#1f77b4', label='Age of Information')
    if mig_reqs:
        ax1.scatter(mig_reqs, mig_aois, color='red', s=100, marker='*', zorder=5, label='Migration')
    ax1.set_xlabel('Request Index')
    ax1.set_ylabel('Age of Information (s)')
    ax1.set_title('Age of Information Trend')
    ax1.grid(True, linestyle='--', alpha=0.7)
    ax1.legend()

    ax2.plot(reqs, costs, marker='s', linestyle='-', color='#ff7f0e', label='Cost')
    ax2.set_xlabel('Request Index')
    ax2.set_ylabel('Cost')
    ax2.set_title('Cost Trend')
    ax2.grid(True, linestyle='--', alpha=0.7)
    ax2.legend()

    plt.tight_layout()
    plt.show()


# Label constants — single source of truth
# Keys used in main.py when building the histories dict
_STYLE_MAP = {
    'Random Baseline': {'color': '#f44336', 'marker': 'x', 'linestyle': '--'},
    'Greedy Best':     {'color': '#2196f3', 'marker': 'o', 'linestyle': '-'},
    'DP Ideal':        {'color': '#4caf50', 'marker': '^', 'linestyle': '--'},
    'DP Real':         {'color': '#4caf50', 'marker': 's', 'linestyle': '-'},
    'PPO (DRL)':       {'color': '#FF9800', 'marker': 'd', 'linestyle': '-'},
}

_DESIRED_ORDER = ['DP Ideal', 'Random Baseline', 'Greedy Best', 'DP Real', 'PPO (DRL)']

_LOCALIZE = {
    'Random Baseline': 'Random Baseline',
    'Greedy Best':     'Greedy Best',
    'DP Ideal':        'DP Oracle (Ideal)',
    'DP Real':         'DP Real (Simulated)',
    'PPO (DRL)':       'PPO (Deep RL)',
}


def plot_comparative_results(histories, num=-1):
    """
    Side-by-side AoI and Cost comparison for multiple algorithms.

    :param histories: dict  e.g. {'Random Baseline': [...], 'DP Ideal': [...], ...}
    :param num: only plot the first `num` requests (-1 = all)
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), dpi=100)

    sorted_labels = sorted(
        histories.keys(),
        key=lambda l: _DESIRED_ORDER.index(l) if l in _DESIRED_ORDER else 999
    )

    for label in sorted_labels:
        history = histories.get(label)
        if not history:
            continue

        style = _STYLE_MAP.get(label, {'color': 'gray', 'marker': '.', 'linestyle': '-'})
        display = _LOCALIZE.get(label, label)

        slice_ = history if num == -1 else history[:num]
        reqs  = [h['req'] for h in slice_]
        aois  = [None if math.isinf(h['aoi'])  else h['aoi']  for h in slice_]
        costs = [None if math.isinf(h['cost']) else h['cost'] for h in slice_]

        ax1.plot(reqs, aois,  label=display, color=style['color'],
                 marker=style['marker'], linestyle=style['linestyle'], linewidth=2, markersize=6)
        ax2.plot(reqs, costs, label=display, color=style['color'],
                 marker=style['marker'], linestyle=style['linestyle'], linewidth=2, markersize=6)

    ax1.set_title('Age of Information Comparison', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Request Index', fontsize=12)
    ax1.set_ylabel('Age of Information (s)', fontsize=12)
    ax1.grid(True, linestyle=':', alpha=0.8)
    ax1.legend(fontsize=11, loc='best')

    ax2.set_title('Cost Comparison', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Request Index', fontsize=12)
    ax2.set_ylabel('Total Cost', fontsize=12)
    ax2.grid(True, linestyle=':', alpha=0.8)
    ax2.legend(fontsize=11, loc='best')

    plt.tight_layout()
    plt.show()
