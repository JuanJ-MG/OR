from gurobipy import *
import gurobipy as gp
import pandas as pd
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt


#define stations
stations = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]

#define travel time matrix
travel_data = [
    [ np.inf, 10, 15, 20, 25, 30, 35, 40],
    [ 12, np.inf, 18, 24, 16, 20, 28, 32],
    [ 14, 16, np.inf, 22, 26, 30, 18, 24],
    [ 20, 24, 26, np.inf, 12, 18, 22, 28],
    [ 18, 14, 20, 16, np.inf, 15, 25, 30],
    [ 25, 20, 22, 28, 30, np.inf, 14, 19],
    [ 30, 28, 24, 20, 18, 15, np.inf, 17],
    [ 35, 32, 28, 24, 20, 18, 16, np.inf]
]

travel_time = pd.DataFrame(travel_data, index=stations, columns=stations)


#define passenger demand OD matrix
demand_data = [
    [0, 150, 300, 200, 100, 250, 180, 220],
    [160, 0, 210, 270, 130, 190, 240, 150],
    [240, 180, 0, 310, 140, 260, 170, 200],
    [200, 220, 190, 0, 280, 210, 320, 160],
    [130, 140, 150, 160, 0, 230, 250, 290],
    [210, 170, 260, 230, 310, 0, 180, 150],
    [190, 240, 200, 270, 220, 160, 0, 210],
    [250, 200, 150, 180, 210, 230, 190, 0]
]

passenger_demand = pd.DataFrame(demand_data, index=stations, columns=stations)


#define data set
Arcs = [(i, j) for i in stations for j in stations if travel_time.loc[i, j] != np.inf]
OD_pairs = [(o, d) for o in stations for d in stations if passenger_demand.loc[o, d] > 0]

#Assign name to model
model = gp.Model(name="HW2-P2a")

# Decision variables x_ij^od
x = model.addVars(Arcs, OD_pairs, lb=0, vtype=GRB.CONTINUOUS, name="x")

# Objective function: minimize total travel time
objFun = quicksum(travel_time.loc[i, j] * x[i, j, o, d] for (i, j) in Arcs for (o, d) in OD_pairs)
model.setObjective(objFun, GRB.MINIMIZE)

for i in stations:
    for (o, d) in OD_pairs:
        model.addConstr(
            quicksum(x[i, j, o, d] for j in stations if (j, i) in Arcs) -
            quicksum(x[j, i, o, d] for j in stations if (i, j) in Arcs) ==
            (passenger_demand.loc[o, d] if i == o else -passenger_demand.loc[o, d] if i == d else 0),
            name="Constrain_%s_%s_%s" %(i,o,d)
        )
#name=f"flow_{i}_{o}_{d}"

model.update()
model.write("HW2P2.lp")

# Optimize model
model.optimize()

# Display optimal travel time
if model.status == GRB.OPTIMAL:
    print(f" Optimal Time: {model.objVal}")
    for (i, j, o, d) in x:
        if x[i, j, o, d].x > 0:
            print(f"Passengers from {o} to {d} traveled via {i} to {j}: {x[i, j, o, d].x}")


