# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/04_cross.ipynb.

# %% auto 0
__all__ = ['x_random', 'x_DH']

# %% ../nbs/04_cross.ipynb 3
from .core import *
from .trait import *
from .meiosis import *

import torch

# %% ../nbs/04_cross.ipynb 4
def x_random( genome: Genome, parent_haplotypes: torch.Tensor, n_crosses: int) -> torch.Tensor:
    """
    Generate random crosses from a set of parent haplotypes.

    Args:
    ----
        parent_haplotypes (torch.Tensor): Haplotypes of the parents. 
                                           Shape: (n_parents, ploidy, chr, loci)
        n_crosses (int): Number of crosses to generate.
        genome (Genome): Genome object.

    Returns:
    -------
        torch.Tensor: Haplotypes of the progeny. 
                      Shape: (n_crosses, ploidy, chr, loci)
    """
    
    assert len(parent_haplotypes.shape) == 4, f"Your input was {parent_haplotypes.shape} when it should be (#parents,ploidy,#chr,#loci)"
    device = genome.device
    n_parents = parent_haplotypes.shape[0]

    # Randomly select parents for each cross
    female_indices = torch.randint(0, n_parents, (n_crosses,), device=device)
    male_indices = torch.randint(0, n_parents, (n_crosses,), device=device)

    # Extract haplotypes of the selected parents
    female_haplotypes = parent_haplotypes[female_indices]
    male_haplotypes = parent_haplotypes[male_indices]

    # Simulate gametes
    female_gametes = simulate_gametes(genome, female_haplotypes)
    male_gametes = simulate_gametes(genome, male_haplotypes)

    # Combine gametes to form progeny haplotypes
    progeny_haplotypes = torch.cat([female_gametes, male_gametes], dim=1)

    return progeny_haplotypes

# %% ../nbs/04_cross.ipynb 7
def x_DH(genome: Genome, parent_haplotypes: torch.Tensor) -> torch.Tensor:
    """
    Generate doubled haploid individuals from a set of parent haplotypes.

    Args:
    ----
        parent_haplotypes (torch.Tensor): Haplotypes of the parents. 
                                           Shape: (n_parents, ploidy, chr, loci)
        genome (Genome): Genome object.

    Returns:
    -------
        torch.Tensor: Haplotypes of the doubled haploid progeny. 
                      Shape: (n_parents, ploidy, chr, loci)
    """
    gametes = simulate_gametes(genome, parent_haplotypes)
    dh_haplotypes = gametes.repeat(1, 2, 1, 1)  # Duplicate the gametes along ploidy dimension

    return dh_haplotypes
