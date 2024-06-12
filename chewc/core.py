# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/01_core.ipynb.

# %% auto 0
__all__ = ['Genome', 'Individual', 'Population', 'PopulationDataset', 'create_population_dataloader']

# %% ../nbs/01_core.ipynb 4
import torch
from typing import List, Tuple, Union, Callable, Optional
import torch
import matplotlib.pyplot as plt

# %% ../nbs/01_core.ipynb 6
class Genome:
    """
    Represents the genomic architecture for the simulation.

    Args:
        ploidy (int): Ploidy level. Defaults to 2.
        n_chromosomes (int): Number of chromosomes. Defaults to 10.
        n_loci_per_chromosome (int): Number of loci per chromosome. Defaults to 5.
        map_type (str, optional): Type of genetic map ('uniform' or 'random'). Defaults to 'random'.
        chromosome_length (float): Genetic length of each chromosome in cM. Defaults to 100.0.
    """

    def __init__(self, ploidy: int = 2, n_chromosomes: int = 10, n_loci_per_chromosome: int = 5, 
                 map_type: Optional[str] = 'random', chromosome_length: float = 100.0):

        assert n_chromosomes > 0, "Number of chromosomes must be greater than 0"
        assert n_loci_per_chromosome > 0, "Loci per chromosome must be greater than 0"

        self.ploidy = ploidy
        self.n_chromosomes = n_chromosomes
        self.n_loci_per_chromosome = n_loci_per_chromosome
        self.map_type = map_type
        self.chromosome_length = chromosome_length

        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.create_genetic_map() 
        
        
    def shape(self) -> Tuple[int, int, int]:
        """Returns the shape of the genome (ploidy, chromosomes, loci)."""
        return self.ploidy, self.n_chromosomes, self.n_loci_per_chromosome

    def create_genetic_map(self):
        """Creates the genetic map based on the specified `map_type`."""
        if self.map_type == 'uniform':
            self.genetic_map = torch.arange(0, self.chromosome_length, self.chromosome_length / self.n_loci_per_chromosome, 
                                            device=self.device).repeat(self.n_chromosomes, 1)
        elif self.map_type == 'random':
            self.genetic_map = torch.zeros((self.n_chromosomes, self.n_loci_per_chromosome), device=self.device)
            for chr_idx in range(self.n_chromosomes):
                random_positions = torch.sort(torch.rand(self.n_loci_per_chromosome - 1, device=self.device) * self.chromosome_length).values
                self.genetic_map[chr_idx, 1:] = random_positions
        else:
            self.genetic_map = None
        
        if self.genetic_map is not None:
            print('Created genetic map')

    def to(self, device: torch.device):
        """Moves the genetic map to the specified device."""
        if self.genetic_map is not None:
            self.genetic_map = self.genetic_map.to(device)
            self.device = device
        return self

class Individual:
    """
    Represents an individual in the breeding simulation.

    Args:
        genome (Genome): Reference to the shared Genome object.
        haplotypes (torch.Tensor): Tensor representing the individual's haplotypes.
                                    Shape: (ploidy, n_chromosomes, n_loci_per_chromosome).
        id (Optional[str]): Unique identifier. Defaults to None.
        mother_id (Optional[str]): Mother's identifier. Defaults to None.
        father_id (Optional[str]): Father's identifier. Defaults to None.
        breeding_values (Optional[torch.Tensor]): Breeding values for traits. 
                                                   Shape: (n_traits,). Defaults to None.
        phenotypes (Optional[torch.Tensor]): Phenotype for traits. Shape: (n_traits,). Defaults to None.
    """

    def __init__(self, 
                 genome: 'Genome', 
                 haplotypes: torch.Tensor, 
                 id: Optional[str] = None, 
                 mother_id: Optional[str] = None, 
                 father_id: Optional[str] = None, 
                 breeding_values: Optional[torch.Tensor] = None, 
                 phenotypes: Optional[torch.Tensor] = None):

        self.genome = genome
        self.haplotypes = haplotypes.to(self.genome.device)
        self.id = id
        self.mother_id = mother_id
        self.father_id = father_id
        self.breeding_values = breeding_values
        self.phenotypes = phenotypes

    @classmethod
    def create_random_individual(cls, genome: 'Genome', id: Optional[str] = None) -> 'Individual':
        """
        Creates a random individual with the specified genome.

        Args:
            genome (Genome): The genome object.
            id (Optional[str]): Unique identifier for the individual.

        Returns:
            Individual: A new Individual object with random haplotypes.
        """
        haplotypes = torch.randint(0, 2, genome.shape(), device=genome.device)
        return cls(genome=genome, haplotypes=haplotypes, id=id)


class Population:
    """
    Represents a population of individuals.

    Args:
        individuals (List[Individual], optional): List of Individual objects in the population. Defaults to None.
        id (Optional[str]): Unique identifier for the population. Defaults to None.
    """

    def __init__(self, individuals: Optional[List[Individual]] = None, id: Optional[str] = None):
        self.individuals = individuals if individuals is not None else []
        self.id = id

    def create_random_founder_population(self, genome: 'Genome', n_founders: int):
        """
        Creates a founder population with random haplotypes.

        Args:
            genome (Genome): The genome object.
            n_founders (int): The number of founder individuals to create.
        """
        self.individuals = [Individual.create_random_individual(genome, id=str(i)) 
                            for i in range(n_founders)]

    def size(self) -> int:
        """Returns the number of individuals in the population."""
        return len(self.individuals)

    def get_genotypes(self) -> torch.Tensor:
        """
        Returns a tensor of all genotypes in the population.

        Returns:
            torch.Tensor: Genotype tensor with shape 
                          (population_size, ploidy, n_chromosomes, n_loci_per_chromosome).
        """
        return torch.stack([individual.haplotypes for individual in self.individuals])

    def get_dosages(self) -> torch.Tensor:
        """
        Calculates the allele dosage for each locus in the population by summing over the ploidy.

        Returns:
            torch.Tensor: Allele dosage tensor with shape 
                          (population_size, n_chromosomes, n_loci_per_chromosome).
        """
        return self.get_genotypes().sum(dim=1)  # Sum over the ploidy dimension

    def add_individual(self, individual: Individual):
        """Adds an individual to the population."""
        self.individuals.append(individual)

    def calculate_allele_frequencies(self) -> torch.Tensor:
        """
        Calculates allele frequencies for each locus in the population.

        Returns:
            torch.Tensor: Allele frequencies (n_chromosomes, n_loci_per_chromosome).
        """
        return self.get_genotypes().float().mean(dim=(0, 1)) # Average over ploidy and individuals

    def calculate_genetic_diversity(self) -> torch.Tensor:
        """
        Calculates a measure of genetic diversity (e.g., heterozygosity).

        Returns:
            torch.Tensor: Genetic diversity (n_chromosomes, n_loci_per_chromosome).
        """
        allele_frequencies = self.calculate_allele_frequencies()
        return 1.0 - (allele_frequencies**2 + (1 - allele_frequencies)**2)

# %% ../nbs/01_core.ipynb 8
from torch.utils.data import Dataset, DataLoader

class PopulationDataset(Dataset):
    """PyTorch Dataset for loading genotypes from a Population."""
    def __init__(self, population: Population, transform=None):
        self.population = population
        self.transform = transform

    def __len__(self):
        return self.population.size()

    def __getitem__(self, idx):
        genotype = self.population.individuals[idx].haplotypes
        if self.transform:
            genotype = self.transform(genotype)
        return genotype

def create_population_dataloader(population: Population, batch_size: int, shuffle=True, num_workers=0, pin_memory=True):
    """Creates a DataLoader for the given Population."""
    dataset = PopulationDataset(population)
    dataloader = DataLoader(
        dataset, 
        batch_size=batch_size, 
        shuffle=shuffle, 
        num_workers=num_workers,
        pin_memory=pin_memory  # Pin memory for faster transfer to GPU
    )
    return dataloader
