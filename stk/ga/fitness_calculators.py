"""
Module for defining fitness calculators.

Fitness calculators are classes which derive :class:`FitnessCalculator`
and define a :meth:`~FitnessCalculator.fitness` method. This method
is used to calculate the fitness of molecules. A
:class:`FitnessCalculator` will hold calculated fitness values in
:class:`FitnessCalculator.fitness_values`. The calculator can be
pickled if the calculated values are to be saved.

.. _`adding fitness functions`:

Extending stk: Adding fitness calculators.
------------------------------------------

A new class inheriting :class:`FitnessCalculator` must be added.
The class must define a :meth:`~FitnessCalculator.fitness` method,
which takes two arguments. The first is `mol` which takes a
:class:`.Molecule` object and is the molecule whose fitness is to be
calculated. The second is `conformer` and it is an :class:`int` holding
the conformer id of the conformer used for calculating the fitness.
`conformer` is should be an optional argument, defaulting to ``-1``.


"""

from functools import wraps
import logging

logger = logging.getLogger(__name__)


def _add_fitness_update(fitness):
    """
    Makes fitness functions add a :attr:`fitness` attribute.

    The attribute is added to the :class:`.Molecule` objects evaluated
    by the :meth:`~FitnessCalculator.fitness` method.

    Parameters
    ----------
    fitness : :class:`function`
        A fitness function, which is a
        :meth:`~FitnessCalculator.fitness` method of a
        :class:`FitnessCalculator`.

    Returns
    -------
    :class:`function`
        The decorated fitness function.

    """

    @wraps(fitness)
    def inner(self, mol, conformer=-1):
        r = fitness(self, mol, conformer)
        mol.fitness = r
        return r

    return inner


def _add_fitness_caching(fitness):
    """
    Gives fitness functions the option skip re-calculatations.

    Parameters
    ----------
    fitness : :class:`function`
        A fitness function, which is a
        :meth:`~FitnessCalculator.fitness` method of a
        :class:`FitnessCalculator`.

    Returns
    -------
    :class:`function`
        The decorated fitness function.

    """

    @wraps(fitness)
    def inner(self, mol, conformer=-1):
        key = (mol, conformer)
        if self.use_cache and key in self.fitness_values:
            return self.fitness_values[(mol, conformer)]

        r = fitness(self, mol, conformer)
        self.fitness_values[key] = r
        return r

    return inner


class FitnessCalculator:
    """
    Calculates and stores fitness values of molecules.

    A :class:`FitnessCalculator` will automatically add a
    :attr:`fitness` attribute to any :class:`.Molecule` objects
    it calculates a fitness value for. The attribute will hold the
    calculated fitness value

    Attributes
    ----------
    use_cache : :class:`bool`
        If ``True`` then fitness values for molecules and conformers
        already held in :attr:`fitness_values` are not re-calculated
        and the value already stored is used.

    fitness_values : :class:`dict`
        Stores fitness values of molecules in the form:

        .. code-block:: python

            fitness_values = {
                (mol1, conf1): 12.2,
                (mol1, conf3): 124.31,
                (mol2, conf1): 0.2
            }

        where ``mol1`` and ``mol2`` are :class:`.Molecule` objects
        and ``conf1`` and ``conf3`` are :class:`int` which are the
        conformers used to calculate the fitness values.

    """

    def __init__(self, use_cache):
        """
        Initializes a :class:`FitnessCalculator` instance.

        Parameters
        ----------
        use_cache : :class:`bool`
            If ``True`` then fitness values for molecules and
            conformers already held in :attr:`fitness_values` are not
            re-calculated and the value already stored is used.

        """

        self.use_cache = use_cache
        self.fitness_values = {}

    def __init_subclass__(cls, **kwargs):
        cls.fitness = _add_fitness_update(cls.fitness)
        cls.fitness = _add_fitness_caching(cls.fitness)

    def fitness(self, mol, conformer=-1):
        """
        Calculates the fitness value of a molecule.

        Parameters
        ----------
        mol : :class:`.Molecule`
            The molecule whose fitness should be calculated.

        conformer : :class:`int`, optional
            The conformer of `mol` to use.

        Returns
        -------
        :class:`float`
            The fitness value of a `conformer` of `mol`.

        """

        raise NotImplementedError()


# Provides labels for the progress plotter.
# @_param_labels('Cavity Difference',
#                'Window Difference',
#                'Asymmetry',
#                'Energy per Bond',
#                'Precursors Strain',
#                'Dihedral Strain')
class PropertyVector(FitnessCalculator):
    """
    Calculates the a set of properties of a molecule.

    This :class:`FitnessCalculator` applies a series of
    :class:`function`s to a :class:`.Molecule` and appends each result
    to a :class:`list`. The :class:`list` forms the property vector of
    the molecule and it is returned as the fitness value of the
    molecule.

    Attributes
    ----------
    property_fns : :class:`tuple` of :class:`function`
        A group of :class:`function`s, each of which is used to
        calculate a single property of the molecule. Each function must
        take 2 arguments, `mol` and `conformer`. `mol` accepts a
        :class:`.Molecule` object and `conformer` accepts an
        :class:`int`. These are the molecule and the conformer id used
        to calculate the property.


    Examples
    --------
    Use on :class:`.StructUnit` objects.

    .. code-block:: python

        # Create the molecules which are to have fitness values
        # evaluated.
        mol1 = StructUnit.smiles_init('NCCN', ['amine'])
        mol2 = StructUnit2.smiles_init('NC[Si]CCCN', ['amine'])
        mol3 = StructUnit3.smiles_init('O=CCC(C=O)CCC=O', ['aldehyde'])

        # Create the functions which calculate the molecule properties.
        def atom_number(mol, conformer):
            return mol.mol.GetNumAtoms()

        def diameter(mol, conformer):
            return mol.max_diamater(conformer)

        def energy(mol, conformer):
            energy_calculator = MMFFEnergy()
            return energy_calculator.energy(mol, conformer)

        # Create the fitness calculator.
        fitness_calculator = PropertyVector(atom_number,
                                            diameter,
                                            energy)

        # Calculate the fitness vector of mol1. It will be a list
        # holding the number of atoms, diameter and energy of mol1,
        # respectively.
        mol1_fitness = fitness_calculator.fitness(mol1)
        # The molecule will also have a fitness attribute holding the
        # result.
        if mol1.fitness == mol1_fitness:
            print('Fitness attribute added.')

        # Calculate the fitness vector of mol2. It will be a list
        # holding the number of atoms, diameter and energy of mol2,
        # respectively.
        mol2_fitness = fitness_calculator.fitness(mol2)
        # The molecule will also have a fitness attribute holding the
        # result.
        if mol2.fitness == mol2_fitness:
            print('Fitness attribute added.')

        # Calculate the fitness vector of mol3. It will be a list
        # holding the number of atoms, diameter and energy of mol3,
        # respectively.
        mol3_fitness = fitness_calculator.fitness(mol3)
        # The molecule will also have a fitness attribute holding the
        # result.
        if mol3.fitness == mol3_fitness:
            print('Fitness attribute added.')

        # The fitness calculate will have all the results saved in
        # its fitness_values attribute.
        print(fitness_calculator.fitness_values)


    Use on :class:`.MacroMolecule` objects, :class:`.Polymer`

    .. code-block:: python

        # First create molecules whose fitness value we wish to
        # caclculate.
        bb1 = StructUnit2.smiles_init('[Br]CC[Br]', ['bromine'])
        polymer1 = Polymer([bb1], Linear('A', [0], n=5))

        bb2 = StructUnit2.smiles_init('[Br]CCNNCC[Br]', ['bromine'])
        polymer2 = Polymer([bb1, bb2], Linear('AB', [0, 0], n=2))

        # Create the functions which calculate the molecule properties.
        def atom_number(mol, conformer):
            return mol.mol.GetNumAtoms()

        def diameter(mol, conformer):
            return mol.max_diamater(conformer)

        def monomer_number(mol, conformer):
            return mol.topology.n * len(mol.topology.repeating_unit)

        # Create the fitness calculator.
        fitness_calculator = PropertyVector(atom_number,
                                            diameter,
                                            monomer_number)

        # Calculate the fitness vector of polymer1. It will be a list
        # holding the number of atoms, diameter and the number of
        # monomers in polymer1, espectively.
        polymer1_fitness = fitness_calculator.fitness(polymer1)
        # The molecule will also have a fitness attribute holding the
        # result.
        if polymer1.fitness == polymer1_fitness:
            print('Fitness attribute added.')

        # Calculate the fitness vector of polymer2. It will be a list
        # holding the number of atoms, diameter and the number of
        # monomers in polymer2, espectively.
        polymer2_fitness = fitness_calculator.fitness(polymer2)
        # The molecule will also have a fitness attribute holding the
        # result.
        if polymer2.fitness == polymer2_fitness:
            print('Fitness attribute added.')

        # The fitness calculate will have all the results saved in
        # its fitness_values attribute.
        print(fitness_calculator.fitness_values)

    Use on :class:`.MacroMolecule` objects, :class:`.Cage`

    .. code-block:: python

        # First create molecules whose fitness value we wish to
        # caclculate.
        bb1 = StructUnit2.smiles_init('NCCN', ['amine'])
        bb2 = StructUnit3.smiles_init('O=CCCC(C=O)CC=O', ['aldehyde'])

        cage1 = Cage([bb1, bb2], FourPlusSix())
        cage2 = Cage([bb1, bb2], EightPlusTwelve())

        # Create the functions which calculate the molecule properties.
        def cavity_size(mol, conformer):
            return mol.cavity_size(conformer)

        def window_variance(mol, conformer):
            return mol.window_variance(conformer)

        # Create the fitness calculator.
        fitness_calculator = PropertyVector(cavity_size,
                                            window_variance)

        # Calculate the fitness vector of cage1. It will be a list
        # holding the cavity size and window variance, respectively.
        cage1_fitness = fitness_calculator.fitness(cage1)
        # The molecule will also have a fitness attribute holding the
        # result.
        if cage1.fitness == cage1_fitness:
            print('Fitness attribute added.')

        # Calculate the fitness vector of cage2. It will be a list
        # holding the cavity size and window variance, respectively.
        cage2_fitness = fitness_calculator.fitness(cage2)
        # The molecule will also have a fitness attribute holding the
        # result.
        if cage2.fitness == cage2_fitness:
            print('Fitness attribute added.')

        # The fitness calculate will have all the results saved in
        # its fitness_values attribute.
        print(fitness_calculator.fitness_values)


    """

    def __init__(self, *property_fns, use_cache=True):
        """
        Initializes a :class:`CageFitness` instance.

        Parameters
        ----------
        *property_fns : :class:`tuple` of :class:`function`
            A group of :class:`function`s, each of which is used to
            calculate a single property of the molecule. Each function
            must take 2 arguments, `mol` and `conformer`. `mol` accepts
            a :class:`.Molecule` object and `conformer` accepts an
            :class:`int`. These are the molecule and the conformer id
            used to calculate the property.

        use_cache : :class:`bool`
            If ``True`` then fitness values for molecules and
            conformers already held in :attr:`fitness_values` are not
            re-calculated and the value stored is used.

        """

        self.property_fns = property_fns
        super.__init__(use_cache=use_cache)

    def fitness(self, mol, conformer=-1):
        """
        Returns the property vector of a molecule.

        Parameters
        ----------
        mol : :class:`.Molecule`
            The molecule whose property vector should be calculated.

        conformer : :class:`int`, optional
            The conformer of `mol` to use.

        Returns
        -------
        :class:`list`
            A :class:`list` of properties of the `mol`.

        """

        property_vector = []
        for property_fn in self.property_fns:
            logger.info(
                f'Using {property_fn.__name__} on "{mol.name}".'
            )
            property_vector.append(property_fn(mol, conformer))
        return property_vector
