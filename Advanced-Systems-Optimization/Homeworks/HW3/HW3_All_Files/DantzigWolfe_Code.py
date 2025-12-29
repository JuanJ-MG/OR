# -*- coding: utf-8 -*-
"""
Dantzig-Wolfe Reformulation for Production Planning with Big M Initialization
Author: Jeorge Atherton
Coding Assistance given from Google Gemini
"""

import gurobipy as gp
from gurobipy import GRB
import numpy as np

class ProductionProblem:
    """
    Represents the production planning problem and implements the
    Dantzig-Wolfe reformulation with column generation and Big M initialization.
    """
    def __init__(self):
        self.ingredients = ['Formula', 'Water', 'Fruit Juice', 'Brown Sugar']
        self.countries = [1, 2, 3]
        self.cost = {
            ('Fruit Juice', 1): 3, ('Fruit Juice', 2): 3.6, ('Fruit Juice', 3): 3.1,
            ('Brown Sugar', 1): 3.2, ('Brown Sugar', 2): 4, ('Brown Sugar', 3): 4.1,
            ('Formula', 1): 8, ('Formula', 2): 8, ('Formula', 3): 8,
            ('Water', 1): 2.7, ('Water', 2): 2.5, ('Water', 3): 3.10
        }
        self.lower_bounds = {'Fruit Juice': 0.25, 'Brown Sugar': 0.10, 'Formula': 0.02, 'Water': 0}
        self.upper_bounds = {'Fruit Juice': 0.35, 'Brown Sugar': 0.30, 'Formula': 0.04, 'Water': 1}
        self.h = {'Fruit Juice': 0.08, 'Brown Sugar': 0.09, 'Formula': 0.10, 'Water': 0.07}
        self.v = {'Fruit Juice': 0.07, 'Brown Sugar': 0.08, 'Formula': 0.10, 'Water': 0.05}
        self.max_capacity_h = {1: 24, 2: 27.5, 3: 30}
        self.min_capacity_v = {1: 19.5, 2: 22, 3: 22}
        self.demand = 1000
        self.fixed_cost = 25
        self.unit_costs = np.array([8, 8, 8, 2.7, 2.5, 3.10, 3, 3.6, 3.1, 3.2, 4, 4.1])
        self.fixed_cost_indicator = np.array([1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0])

    def generate_patterns(self):
        """
        Provides a list of initial production patterns (as numpy arrays).
        """
        patterns = []

        return patterns

    def master_problem(self, patterns):
        """
        Defines and solves the reduced master problem with Big M initialization.

        Args:
            patterns (list of numpy.ndarray): A list of production patterns.

        Returns:
            gurobipy.Model: The solved master problem model.
        """
        num_patterns = len(patterns)
        pattern_indices = range(num_patterns)

        master_model = gp.Model("master_problem")

        # Big M value (should be significantly larger than any reasonable cost)
        M = 1e4  # Adjust this value as needed

        # Define lambda variables for the generated patterns
        lambda_vars = master_model.addVars(pattern_indices,
                                           vtype=gp.GRB.CONTINUOUS,
                                           lb=0,
                                           ub=1,
                                           name="lambda")

        # Define artificial variables for the demand and fixed cost constraints
        a_1 = master_model.addVar(vtype=gp.GRB.CONTINUOUS, lb=0, name="artifical_1")
        a_2 = master_model.addVar(vtype=gp.GRB.CONTINUOUS, lb=0, name="artifical_2")
        s_1 = master_model.addVar(vtype=gp.GRB.CONTINUOUS, lb=0, name="slack_1")
        s_2 = master_model.addVar(vtype=gp.GRB.CONTINUOUS, lb=0, name="slack_2")

        # Objective function: Minimize the total cost (including Big M for artificials)
        objective_expression = gp.quicksum(
            np.dot(self.unit_costs, patterns[q]) * lambda_vars[q]
            for q in pattern_indices
        ) + M * (a_1 + a_2) + 0 * (s_1 + s_2)

        master_model.setObjective(objective_expression, sense=gp.GRB.MINIMIZE)

        # Constraint 1: Meet the total demand (using artificial variables)
        master_model.addConstr(
            gp.quicksum(np.sum(patterns[q]) * lambda_vars[q] for q in pattern_indices) +
            a_1 - s_1 == self.demand,
            name="demand_constraint"
        )

        # Constraint 2: Fixed cost/formula constraint (using artificial variable)
        master_model.addConstr(
            gp.quicksum(np.dot(self.fixed_cost_indicator, patterns[q]) * lambda_vars[q]
                        for q in pattern_indices) + s_2 == self.fixed_cost,
            name="formula_constraint"
        )
        
        # Constraint 3: lambdas must be equal to 1
        master_model.addConstr( 
            gp.quicksum(lambda_vars[q] for q in pattern_indices) + a_2 == 1 )

        return master_model

    def auxiliary_problem(self, dual_variables):
        """
        Defines and solves the auxiliary problem to generate new production patterns.
    
        Args:
            dual_variables (numpy.ndarray): The dual variables from the master problem
                                             (pi for demand, pi for formula, pi for convexity).
    
        Returns:
            gurobipy.Model: The solved auxiliary problem model.
        """
        auxiliary_model = gp.Model("auxiliary_problem")
    
        pi_demand = dual_variables[0]
        pi_formula = dual_variables[1]
        pi_convexity = dual_variables[2]
    
        # Define auxiliary decision variables: production quantity of each ingredient in each country
        x = auxiliary_model.addVars(self.ingredients, self.countries,
                                     vtype=gp.GRB.CONTINUOUS, lb=0, name="x")
    
        # Cost of a potential new pattern
        pattern_cost = gp.quicksum(self.cost[i, j] * x[i, j]
                                   for i in self.ingredients for j in self.countries)
    
        # Total production in the pattern
        total_production = gp.quicksum(x[i, j] for i in self.ingredients for j in self.countries)
    
        # Total 'Formula' in the pattern
        total_formula = gp.quicksum(x['Formula', j] for j in self.countries)
    
        # Objective function: Minimize the reduced cost
        reduced_cost = pattern_cost - pi_demand * total_production - pi_formula * total_formula - pi_convexity
        auxiliary_model.setObjective(reduced_cost, sense=gp.GRB.MINIMIZE)
    
        # Constraints for each country (same as before)
        for j in self.countries:
            total_production_j = gp.quicksum(x[i, j] for i in self.ingredients)
            for i in self.ingredients:
                auxiliary_model.addConstr(x[i, j] <= self.upper_bounds[i] * total_production_j,
                                            name=f"upper_bound_{i}_{j}")
                auxiliary_model.addConstr(x[i, j] >= self.lower_bounds[i] * total_production_j,
                                            name=f"lower_bound_{i}_{j}")
            auxiliary_model.addConstr(
                gp.quicksum(self.h[i] * x[i, j] for i in self.ingredients) <= self.max_capacity_h[j],
                name=f"capacity_h_{j}"
            )
            auxiliary_model.addConstr(
                gp.quicksum(self.v[i] * x[i, j] for i in self.ingredients) >= self.min_capacity_v[j],
                name=f"capacity_v_{j}"
            )
    
        return auxiliary_model

    def column_generation(self):
        """
        Implements the column generation algorithm with Big M initialization.

        Returns:
            list: A history of the objective values of the master problem.
        """
        production_patterns = self.generate_patterns()  # Start with an empty list
        objective_value_history = []
        iteration = 0
        while True:
            iteration += 1
            print(f"\n--- Iteration {iteration} ---")

            master = self.master_problem(production_patterns)
            master.Params.OutputFlag = 0 # Set to 1 for more detailed Gurobi output
            master.optimize()
            objective_value_history.append(master.objVal)
            print(f"Master Problem Objective Value: {master.objVal}")
            
            #mp_vars = np.array([var for var in master.getVars()])
            #print(f"Master Problem Vars:\n {mp_vars}")

            dual_vars = np.array([constraint.pi for constraint in master.getConstrs()])
            print(f"Dual Variables (Demand, Fixed Cost, Convexity): {dual_vars}")

            aux = self.auxiliary_problem(dual_vars)
            aux.Params.OutputFlag = 0 # Set to 1 for more detailed Gurobi output
            aux.optimize()
            print(f"Auxiliary Problem Objective Value (Max Reduced Cost): {aux.objVal}")

            # For a minimization master problem, a positive aux.objVal indicates a
            # column with a positive reduced cost that can improve the solution.
            if aux.objVal < -1e-6:
                new_pattern = [var.x for var in aux.getVars()]
                production_patterns.append(np.array(new_pattern))
                print(f"New Pattern Added: {new_pattern}")
            elif not production_patterns:
                print("No improving column found and no initial patterns. Big M solution might be active.")
                break
            else:
                print("No improving column found.")
                break

        print("\n--- Column Generation Finished ---")
        return objective_value_history, master, production_patterns
    
    
    def full_lp(self):
        """
        Creates the soda production problem in one go for validation

        Returns:
            gurobi model
        """
        
        full_model = gp.Model("Soda_Production")
        
        ## add variables
        x = full_model.addVars(self.ingredients, self.countries,
                                     vtype=gp.GRB.CONTINUOUS,
                                     lb=0,
                                     obj=self.cost,
                                     name="x")
        
        full_model.ModelSense = GRB.MINIMIZE
        
        ## meet demand
        full_model.addConstr( gp.quicksum(x[i,j] for i in self.ingredients
                                          for j in self.countries) >= self.demand )
        
        ## formula scarcity
        full_model.addConstr( gp.quicksum( x['Formula',j] for j in self.countries)
                             <= self.fixed_cost )
        
        # Constraints for each country
        for j in self.countries:
            total_production_j = gp.quicksum(x[i, j] for i in self.ingredients)
            for i in self.ingredients:
                full_model.addConstr(x[i, j] <= self.upper_bounds[i] * total_production_j)
                full_model.addConstr(x[i, j] >= self.lower_bounds[i] * total_production_j)
                full_model.addConstr( gp.quicksum(self.h[i] * x[i, j] for i in self.ingredients) <= self.max_capacity_h[j])
                full_model.addConstr( gp.quicksum(self.v[i] * x[i, j] for i in self.ingredients) >= self.min_capacity_v[j])
        
    
        return full_model
    
    
    def print_lambda_weighted_patterns(self, final_master_model, final_patterns):
        """
        Prints the lambda-weighted production patterns of the final master problem solution.

        Args:
            final_master_model (gurobipy.Model): The solved final master problem model.
            final_patterns (list of numpy.ndarray): The list of production patterns used in the final master problem.
        """
        if final_master_model.status == GRB.OPTIMAL:
            lambda_vars = final_master_model.getVars()[:len(final_patterns)]  # Lambda variables are the first ones added

            print("\n--- Lambda Weighted Production Patterns ---")
            for i, lambda_var in enumerate(lambda_vars):
                if lambda_var.x > 1e-6:  # Only print patterns with a significant weight
                    weight = lambda_var.x
                    pattern = final_patterns[i]
                    weighted_pattern = weight * pattern
                    print(f"Pattern {i} (lambda = {weight:.4f}):")
                    for k in range(len(self.ingredients)):
                        for c_idx, country in enumerate(self.countries):
                            index = k * len(self.countries) + c_idx
                            print(f"  {self.ingredients[k]} in Country {country}: {weighted_pattern[index]:.4f}")
        else:
            print("Master problem did not reach an optimal solution.")
        
    
    
if __name__ == '__main__':

    ## initialize class instance
    problem = ProductionProblem()

    ## solve column generation problem
    history, final_master, prod_patterns = problem.column_generation()
    print("\nObjective Value History:", history)

    ## print lambda weighted patterns
    problem.print_lambda_weighted_patterns(final_master, prod_patterns)

    ## solve full LP
    print("\nNow solve full model for comparison")
    full_model = problem.full_lp()
    full_model.Params.OutputFlag = 0
    full_model.optimize()
    print(f"Full LP Objective Value: {full_model.objVal}")

  