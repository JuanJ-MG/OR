import gurobipy as gp
from gurobipy import GRB

# --------------------------
# 1. INPUT DATA
# --------------------------
stations = [1, 2, 3, 4, 5, 6, 7, 8]

# OD Demand Matrix (8x8): demand_data[i-1][j-1] = # of passengers i->j
demand_data = [
    [0,   150, 300, 200, 100, 250, 180, 220],  # from station 1
    [160, 0,   210, 270, 130, 190, 240, 150],  # from station 2
    [240, 180, 0,   310, 140, 260, 170, 200],  # from station 3
    [200, 220, 190, 0,   280, 210, 320, 160],  # from station 4
    [130, 140, 150, 160, 0,   230, 250, 290],  # from station 5
    [210, 170, 260, 230, 310, 0,   180, 150],  # from station 6
    [190, 240, 200, 270, 220, 160, 0,   210],  # from station 7
    [250, 200, 150, 180, 210, 230, 190, 0  ]   # from station 8
]

# Travel-time matrix (minutes): time_data[i-1][j-1] = travel time i->j
time_data = [
    [0,  10, 15, 20, 25, 30, 35, 40],  # from station 1
    [12, 0,  18, 24, 16, 20, 28, 32],  # from station 2
    [14, 16, 0,  22, 26, 30, 18, 24],  # from station 3
    [20, 24, 26, 0,  12, 18, 22, 28],  # from station 4
    [18, 14, 20, 16, 0,  15, 25, 30],  # from station 5
    [25, 20, 22, 28, 30, 0,  14, 19],  # from station 6
    [30, 28, 24, 20, 18, 15, 0,  17],  # from station 7
    [35, 32, 28, 24, 20, 18, 16, 0 ]   # from station 8
]

# Convert Time Travel and OD matrices into dictionaries for easy lookup.
ArcDemand = {}       #OD Arcs and passenger demand 
ArcTime = {}      #Time between Arcs

# Loop through the 8x8 staion matrix and create arc time and demand
for i in stations:      
    for j in stations:
        ArcDemand[(i, j)] = demand_data[i-1][j-1]  #Arc demand
        ArcTime[(i, j)] = time_data[i-1][j-1]   #Arc time

# Problem parameters
bus_capacity   = 150
max_buses      = 5
total_time_cap = 391890
fixed_cost     = 1000
station_cost   = 100

# --------------------------
# 2. ENUMERATE ROUTES (ASCENDING AND DESCENDING)
# --------------------------

# Generate all no backtracking routes from i to j store in "all_routes"
all_routes = []
for i in stations:  #loop through all Stations
    for j in stations:
        if i != j:  #Ignore when stations are the same
            # Determine direction by finding out lower and higher station values.
            EarlierStation = min(i, j)
            LasterStation = max(i, j)
            intermediate = []
            #sort through lowest number to highest number station within this route
            for m in stations:
                if m > EarlierStation and m < LasterStation:       #if station is within this route
                    intermediate.append(m)  #add station to the route

            # In order to loop through all possible station combinations within this route
            # There are 2^(number of intermediates) subsets of intermediate stations
            n_mid = len(intermediate)       # Identify total stations within the route
            num_subsets = 1 << n_mid        # bit shift to the left, this is the same as taking 2^n_mid
            
            subset_mask = 0
            
            # Loop through all possible intermediate stations within the low and high range
            while subset_mask < num_subsets:
                chosen = []
                
                # Add starting station
                chosen.append(i)
                
                # Add mid section intermediate stations.
                for idx in range(n_mid):
                    bit = 1 << idx
                    if (subset_mask & bit) != 0:
                        chosen.append(intermediate[idx])
                
                # Add last ending station
                chosen.append(j)  
                
                # Sort chosen stations direction
                if i < j:
                    #if going forward
                    chosen.sort()            # ascending order
                else:
                    #else sort it by reverse direction
                    chosen.sort(reverse=True)  # descending order
                
                # Save the route as a tuple.
                all_routes.append(tuple(chosen))
                subset_mask += 1

# Since list can contain duplicates Remove duplicates by forcing as set
all_routes = list(set(all_routes))
all_routes.sort()           # Sort the list 
R = range(len(all_routes))  # Total Routes

# --------------------------
# 3. PRECOMPUTE ROUTE COST, ROUTE LENGTH & ROUTE TRAVEL TIMES
# --------------------------
route_cost = {}     #Route Cost
route_length = {}   #Route Length
route_time = {}     #Route Travel Time in minutes for OD pair (i, j) on route r
                    #route_time[((i, j), r)] 

# R has total routes, and we will go through each route r_ind
for r_idx in R:
    # Update Route Cost
    route_stations = all_routes[r_idx]      # Identify all stations in this route
    length_r = len(route_stations)          # Count total stations in this route
    route_cost[r_idx] = fixed_cost + station_cost * length_r# Calculate cost for this route
    
    # Update Route Length
    route_length[r_idx] = length_r
    
    # Update Route Travel Time
    cumulative_station_time = {}
    first_station = route_stations[0]             # First station
    cumulative_station_time[first_station] = 0            # First station as start time
    total_time = 0
    
    # Loop through each arc and create an initial cumulative time for each station
    for idx in range(len(route_stations) - 1):
        s1 = route_stations[idx]                # Current station
        s2 = route_stations[idx + 1]            # Next station
        # Look up ArcTime dictionary of time between current station and next station
        total_time += ArcTime[(s1, s2)]         # Add up time between two stations
        cumulative_station_time[s2] = total_time

    # Loop through each arc and update route travel time
    for (i_val, j_val) in ArcDemand.keys():
        # Continue if arc isn't looping to itself (e.g. 1,1)
        if i_val != j_val:
            if i_val in route_stations and j_val in route_stations: #If this arc is within this route
                idx_i = route_stations.index(i_val)
                idx_j = route_stations.index(j_val)
                if idx_i < idx_j:                                   #Figure out direction
                    # If station direction is ascending then update route time
                    route_time[((i_val, j_val), r_idx)] = cumulative_station_time[j_val] - cumulative_station_time[i_val]
                else:
                    # Else in reverse and set to zero
                    route_time[((i_val, j_val), r_idx)] = 0
            else:
                # If this arc isn't within this route then set to zero time
                route_time[((i_val, j_val), r_idx)] = 0
        else:
            # If this arc is self looping then set to zero time
            route_time[((i_val, j_val), r_idx)] = 0

# --------------------------
# 4. BUILD THE MODEL
# --------------------------
model = gp.Model("BiDirectional_Route_Model")

# Decision variables:
y_vars = {} # y_vars[r]: binary variable indicating whether route r is used.
b_vars = {} # b_vars[r]: integer number of buses assigned to route r (0 to max_buses).
x_vars = {} # x_vars[(i,j), r]: continuous variable representing passenger flow for OD (i,j) on route r.

# R is total number of all routs. Value from all_routes variable length
for r_idx in R:
    #y tracks if each route are used or not
    y_vars[r_idx] = model.addVar(vtype=GRB.BINARY, name="y_r%d" % r_idx)
    #b sets Bus quantity with max bus as upper bound
    b_vars[r_idx] = model.addVar(vtype=GRB.INTEGER, lb=0, ub=max_buses, name="b_r%d" % r_idx)

# K is a list of OD arc pairs (i, j) for reference
K = []
for i in stations: # Start from station 1 to 8
    for j in stations:
        if i != j: # Make sure not self looping arc
            K.append((i, j)) # Add arc pairs to K

# Create arc demand x_var for each OD arc pairs            
for (i_val, j_val) in K:
    # Loop through all routs and add variables 
    for r_idx in R:
        # initialize x variable for all OD arc demand
        x_vars[((i_val, j_val), r_idx)] = model.addVar(vtype=GRB.CONTINUOUS, lb=0,
                                                        name="x_%d_%d_r%d" % (i_val, j_val, r_idx))

# --------------------------
# 5. SET THE OBJECTIVE
# --------------------------
# Minimize the total cost of used routes.
obj_expr = gp.LinExpr() # Create linear expression objective

# Loop through all routs and create an objective function with term of Route Cost * y variable (each route)
for r_idx in R:
    obj_expr.addTerms(route_cost[r_idx], y_vars[r_idx])

# Create objective function to minimization Route cost
model.setObjective(obj_expr, GRB.MINIMIZE)

# --------------------------
# 6. ADD CONSTRAINTS
# --------------------------
# (a) Demand satisfaction: For every OD pair, the sum over routes must equal the demand.
for (i_val, j_val) in K:    # Loop through each OD arc pairs K(i, j)
    lhs = gp.LinExpr()      # Create linear expression
    for r_idx in R:         # Loop through all routs and add constraints 
        lhs.addTerms(1.0, x_vars[((i_val, j_val), r_idx)])
    # Set x variable to all OD arc demand
    model.addConstr(lhs == ArcDemand[(i_val, j_val)], "demand_%d_%d" % (i_val, j_val))

# (b) Capacity constraint: Passenger flow on route r cannot exceed bus capacity times number of buses.
for r_idx in R:             # Loop through all routs and add constraints 
    lhs_cap = gp.LinExpr()  # Create linear expression objective
    for (i_val, j_val) in K:# Loop through each OD arc pairs K(i, j)
        lhs_cap.addTerms(1.0, x_vars[((i_val, j_val), r_idx)])
    # All x <= bus capacity * bus quantity
    model.addConstr(lhs_cap <= bus_capacity * b_vars[r_idx], "cap_r%d" % r_idx)

# (c) Bus-route activation: Number of buses is zero if route is not used.
for r_idx in R: # Loop through all routs and add constraints 
    model.addConstr(b_vars[r_idx] <= max_buses * y_vars[r_idx], "buslink_r%d" % r_idx)

# (d) Total travel time constraint.
lhs_time = gp.LinExpr()     # Create linear expression objective
for (i_val, j_val) in K:    # Loop through each OD arc pairs K(i, j)
    for r_idx in R:         # Loop through all routs and add constraints 
        val_time = route_time[((i_val, j_val), r_idx)]
        if val_time > 0:
            lhs_time.addTerms(val_time, x_vars[((i_val, j_val), r_idx)])
# all rout time <= total time cap of 391890
model.addConstr(lhs_time <= total_time_cap, "time_limit")

# (e) Force x_vars to zero if the route does not serve an OD pair.
for (i_val, j_val) in K:    # Loop through each OD arc pairs K(i, j)
    for r_idx in R:         # Loop through all routs and add constraints 
        if route_time[((i_val, j_val), r_idx)] == 0:    #If route time is zero then set to zero
            model.addConstr(x_vars[((i_val, j_val), r_idx)] == 0,
                            "no_service_%d_%d_r%d" % (i_val, j_val, r_idx))

# --------------------------
# 7. SOLVE THE MODEL
# --------------------------
modelTimeLimit = 0.2                            # Limit Gurobi optimization processing time e.g. 1 is 1min time limit
model.setParam('TimeLimit', modelTimeLimit*60)  # Set model time limit
model.optimize()

# --------------------------
# 8. DISPLAY RESULTS AND ROUTES
# --------------------------
# Print objective min cost
print("Objective (min cost) =", model.ObjVal)
used_routes = []
for r_idx in R:
    if y_vars[r_idx].X > 0.5:
        used_routes.append(r_idx)

 # Display route used.
print("Number of routes used =", len(used_routes))
for r_idx in used_routes:
    route_stations = all_routes[r_idx]
    print("  Route index =", r_idx, "stations =", route_stations)
    print("    y =", y_vars[r_idx].X)
    print("    buses =", b_vars[r_idx].X)
    print("    route cost =", route_cost[r_idx])

 # Calculate total passenger travel time used.
total_time_used = 0.0
for (i_val, j_val) in K:
    for r_idx in R:
        flow = x_vars[((i_val, j_val), r_idx)].X
        if flow > 1e-6:
             total_time_used += route_time[((i_val, j_val), r_idx)] * flow
print("Total passenger travel time =", total_time_used, "(limit =", total_time_cap, ")")
