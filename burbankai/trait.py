# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/02_trait.ipynb.

# %% auto 0
__all__ = ['select_qtl_loci', 'generate_marker_effects', 'calculate_genetic_variance', 'scale_marker_effects', 'TraitA']

# %% ../nbs/02_trait.ipynb 4
from .core import *

import torch
import attr

def select_qtl_loci(num_qtl_per_chromosome: int, genome:Genome) -> torch.Tensor:
    """
    Randomly selects loci to be QTLs on each chromosome.

    Args:
    ----
    num_qtl_per_chromosome (int): Number of QTLs to select per chromosome.
    genome (Genome): Genome object containing the chromosome structure.

    Returns:
    -------
    torch.Tensor: A boolean tensor indicating which loci are QTLs. 
                  Shape: (number_chromosomes, loci_per_chromosome)
    """
    qtl_indices = []
    for i in range(genome.number_chromosomes):
        # Randomly sample indices for QTLs on the current chromosome
        chromosome_indices = torch.randperm(genome.loci_per_chromosome)[:num_qtl_per_chromosome]
        
        # Create a boolean tensor for the current chromosome, marking QTL positions as True
        chromosome_qtl_flags = torch.zeros(genome.loci_per_chromosome, dtype=torch.bool)
        chromosome_qtl_flags[chromosome_indices] = True
        
        qtl_indices.append(chromosome_qtl_flags)
    
    return torch.stack(qtl_indices)

def generate_marker_effects(qtl_map: torch.Tensor, mean: float = 0.0, variance: float = 1.0) -> torch.Tensor:
    """
    Generates random marker effects for QTLs, drawn from a normal distribution.

    Args:
    ----
    qtl_map (torch.Tensor): A boolean tensor indicating which loci are QTLs. 
                            Shape: (number_chromosomes, loci_per_chromosome)
    mean (float): The mean of the normal distribution from which to draw effects. Defaults to 0.0.
    variance (float): The variance of the normal distribution from which to draw effects. Defaults to 1.0.

    Returns:
    -------
    torch.Tensor: A tensor of marker effects. Shape: (number_chromosomes, loci_per_chromosome).
                  Non-QTL loci will have an effect of 0.
    """
    # Create a tensor of zeros with the same shape as the qtl_map
    effects = torch.zeros_like(qtl_map, dtype=torch.float)
    
    # Determine the number of QTLs
    num_qtl = qtl_map.sum().item()

    # Sample random effects from a normal distribution
    qtl_effects = torch.randn(num_qtl) * (variance ** 0.5) + mean
    
    # Assign the sampled effects to the QTL positions in the effects tensor
    effects[qtl_map] = qtl_effects
    
    return effects
def calculate_genetic_variance(founder_pop: torch.Tensor, marker_effects: torch.Tensor, genome: Genome) -> float:
    """
    Calculates the additive genetic variance in the founder population.

    Args:
        founder_pop (torch.Tensor): Tensor of founder haplotypes. 
                                    Shape: (n_founders, ploidy, number_chromosomes, loci_per_chromosome)
        marker_effects (torch.Tensor): Tensor of marker effects. 
                                       Shape: (number_chromosomes, loci_per_chromosome)
        genome (Genome): The genome object.

    Returns:
        torch.Tensor: The additive genetic variance.
    """
    # Convert to float for mean operation to work
    founder_pop = founder_pop.float()
    # Calculate allele frequencies in the founder population
    allele_frequencies = founder_pop.mean(dim=(0, 1))  # Average across founders and ploidy

    # Calculate the genetic value contributions of each locus
    locus_contributions = 2 * allele_frequencies * (1 - allele_frequencies) * marker_effects**2

    # Sum the contributions across all loci to get the total genetic variance
    genetic_variance = locus_contributions.sum().item()

    return genetic_variance

def scale_marker_effects(marker_effects: torch.Tensor, 
                         initial_variance: float, 
                         desired_variance: float) -> torch.Tensor:
    """
    Scales marker effects to achieve a desired genetic variance.

    Args:
        marker_effects (torch.Tensor): The initial marker effects.
        initial_variance (float): The genetic variance with the initial effects.
        desired_variance (float): The desired genetic variance.

    Returns:
        torch.Tensor: The scaled marker effects.
    """
    scaling_factor = (desired_variance / initial_variance) ** 0.5
    return marker_effects * scaling_factor

#| hide



# %% ../nbs/02_trait.ipynb 5
import torch
import attr
from typing import Tuple, Optional, List

@attr.s(auto_attribs=True)
class TraitA:
    """
    Represents a trait with only additive genetic effects.

    Attributes:
    ----------
    qtl_map (torch.Tensor): A boolean tensor indicating which loci are QTLs. 
                           Shape: (number_chromosomes, loci_per_chromosome)
    additive_effects (torch.Tensor): A tensor of additive effects for each QTL. 
                                  Shape: (number_chromosomes, loci_per_chromosome)
    genome (Genome): The genome object.
    founder_pop (torch.Tensor): Tensor of founder haplotypes. 
                                Shape: (n_founders, ploidy, number_chromosomes, loci_per_chromosome)
    target_variance (float): The desired genetic variance for the trait.
    intercept (float): The intercept value, calculated during initialization.
    
    Methods:
    -------
    calculate_genetic_value(genotypes: torch.Tensor) -> torch.Tensor:
        Calculates the genetic value of individuals based on their genotypes.
    _calculate_intercept() -> float:
        Calculates the intercept based on the mean genetic value of the founder population.
    _calculate_scaled_additive_dosages(genotypes: torch.Tensor) -> torch.Tensor:
        Calculates the scaled additive genotype dosages.
    _scale_effects() -> None:
        Scales the additive effects to achieve the target genetic variance.
    """

    qtl_map: torch.Tensor 
    additive_effects: torch.Tensor 
    genome: Genome 
    founder_pop: torch.Tensor 
    target_variance: float
    target_mean: float
    intercept: float = attr.ib(init=False)

    def __attrs_post_init__(self):
        """
        Calculate the intercept and scale the effects after initialization.
        """
        self.intercept = self._calculate_intercept()
        self._scale_effects() 

    def _calculate_intercept(self) -> float:
        """
        Calculates the intercept based on the mean genetic value of the founder population.

        Returns:
            float: The intercept value.
        """
        # Calculate the mean genetic value of the founder population (without scaling)
        founder_genetic_values = (self.founder_pop.float() * self.additive_effects).sum(dim=(1, 2, 3))
        mean_founder_gv = founder_genetic_values.mean().item()
        return self.target_mean - mean_founder_gv 

    def _calculate_scaled_additive_dosages(self, genotypes: torch.Tensor) -> torch.Tensor:
        """
        Calculates the scaled additive genotype dosages.

        Args:
            genotypes (torch.Tensor): A tensor representing the genotypes of individuals.
                                     Shape: (n_individuals, ploidy, number_chromosomes, loci_per_chromosome).

        Returns:
            torch.Tensor: A tensor of scaled additive dosages. 
                         Shape: (n_individuals, ploidy, number_chromosomes, loci_per_chromosome).
        """
        return (genotypes - self.genome.ploidy / 2) * (2 / self.genome.ploidy)

    def _scale_effects(self) -> None:
        """
        Scales the additive effects to achieve the target genetic variance and 
        calculates the intercept to achieve the target mean.
        """
        # Calculate the initial genetic variance in the founder population
        founder_gvs = self.calculate_genetic_value(self.founder_pop)
        initial_variance = founder_gvs.var().item()

        # Calculate the scaling factor
        scaling_factor = (self.target_variance / initial_variance) ** 0.5

        # Scale the additive effects
        self.additive_effects = self.additive_effects * scaling_factor

        # Recalculate the intercept after scaling
        # self.intercept = self._calculate_intercept() 

    def calculate_genetic_value(self, genotypes: torch.Tensor) -> torch.Tensor:
        """
        Calculates the genetic value of individuals given their genotypes.

        Args:
        ----
        genotypes (torch.Tensor): A tensor representing the genotypes of individuals.
                                 Shape: (n_individuals, ploidy, number_chromosomes, loci_per_chromosome).

        Returns:
        -------
        torch.Tensor: A tensor of genetic values for each individual. Shape: (n_individuals,).
        """

        # Calculate the scaled additive genotype dosages
        scaled_dosages = self._calculate_scaled_additive_dosages(genotypes)

        # Apply the additive effects to the scaled dosages, only at QTL positions
        additive_genetic_values = (scaled_dosages * self.additive_effects).sum(dim=(1, 2, 3))

        # Add the intercept to adjust the mean genetic value
        return additive_genetic_values + self.intercept
