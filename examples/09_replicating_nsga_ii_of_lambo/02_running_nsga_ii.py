from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from pymoo.optimize import minimize
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.mixed import (
    MixedVariableMating,
    MixedVariableSampling,
    MixedVariableDuplicateElimination,
)
from pymoo.core.variable import Choice
from pymoo.core.crossover import Crossover

from poli import objective_factory

from poli_baselines.core.utils.pymoo.interface import DiscretePymooProblem
from poli_baselines.core.utils.pymoo.wildtype_sampling import WildtypeMutationSampling
from poli_baselines.core.utils.pymoo.wildtype_mutation import (
    NoMutation,
    WildtypeMutation,
)
from poli_baselines.core.utils.pymoo.wildtype_mating import WildtypeMating
from poli_baselines.core.utils.pymoo.save_history import save_all_populations


class NoCrossover(Crossover):
    def __init__(self, n_parents=2, n_offsprings=2, prob=0.9, **kwargs):
        super().__init__(n_parents, n_offsprings, prob, **kwargs)

    def _do(self, problem, X, **kwargs):
        return X


if __name__ == "__main__":
    # Loading up the initial Pareto front
    # to get the initial wildtypes
    THIS_DIR = Path(__file__).parent.resolve()
    original_pareto_front = pd.read_csv(
        THIS_DIR / "initial_pareto_front.csv",
        index_col=False,
    )

    wildtype_pdb_paths = []
    for pdb_id in original_pareto_front["pdb_id"]:
        folder_to_pdb = list((THIS_DIR / "repaired_pdbs").glob(f"{pdb_id}_*"))
        if len(list(folder_to_pdb)) == 0:
            print(f"Could not find PDB for {pdb_id}")
            continue

        folder_to_pdb = list(folder_to_pdb)[0]
        pdb_id_and_chain = folder_to_pdb.name
        pdb_path = folder_to_pdb / f"{pdb_id_and_chain}_Repair.pdb"
        wildtype_pdb_paths.append(pdb_path)

    # Creating the objective function
    problem_info, f, x0, y0, _ = objective_factory.create(
        name="foldx_stability_and_sasa",
        wildtype_pdb_path=wildtype_pdb_paths,
    )

    pymoo_problem = DiscretePymooProblem(
        black_box=-f,
        x0=x0,
        y0=y0,
    )

    # Now we can use PyMoo's NSGA-II to solve the problem.
    population_size = 10
    method = NSGA2(
        pop_size=population_size,
        sampling=WildtypeMutationSampling(
            x_0=x0, alphabet=problem_info.alphabet, num_mutations=1
        ),
        mating=WildtypeMating(),
        eliminate_duplicates=MixedVariableDuplicateElimination(),
    )

    # Now we can minimize the problem
    res = minimize(
        pymoo_problem,
        method,
        termination=("n_gen", 2),
        seed=1,
        save_history=True,
        verbose=True,
    )

    save_all_populations(
        result=res,
        alphabet=problem_info.alphabet,
        path=THIS_DIR / "history.json",
    )

    # Let's plot all the different populations:
    all_F = -np.concatenate(
        [history_i.pop.get("F") for history_i in res.history], axis=0
    )
    fig, ax = plt.subplots(1, 1)
    sns.scatterplot(
        x=all_F[:, 1],
        y=all_F[:, 0],
        ax=ax,
        label="All populations",
    )
    sns.scatterplot(
        x=y0[:, 1], y=y0[:, 0], ax=ax, label="Wildtype", c="red", marker="x"
    )
    ax.set_xlabel("SASA")
    ax.set_ylabel("Stability")

    plt.show()
