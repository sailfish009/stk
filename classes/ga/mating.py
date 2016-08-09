import os

class Mating:
    """
    Carries out mating operations on the population.
    
    Instances of the ``Population`` class delegate mating operations to
    instances of this class. They do this by calling:
        
        >>> offspring_pop = pop.gen_offspring()
        
    which returns a new population consisting of molecules generated by
    performing mating operations on members of ``pop``. This class
    invokes an instance of the ``Selection`` class to select the
    parent pool. Both an instance of this class and the ``Selection``
    class are held in the `ga_tools` attribute of a ``Population`` 
    instance.
    
    This class is initialized with a ``FunctionData`` instance. The 
    object holds the name of the mating function to be used by the
    population as well as any additional parameters the function may 
    require. Mating functions should be defined as methods within this
    class.
    
    Members of this class are also initialized with an integer which
    holds the number of mating operations to be performed each
    generation.
    
    Attributes
    ----------
    func_data : FunctionData
        The ``FunctionData`` object holding the name of the function
        chosen for mating and any additional paramters and corresponding
        values the function may require.
    
    num_matings : int
        The number of matings thats need to be performed each
        generation.
    
    n_calls : int
        The total number of times an instance of ``Mating`` has been
        called during its lifetime.
    
    name : str
        A template string for naming ``MacroMolecule`` instances 
        produced during mating.
        
    """
    
    
    def __init__(self, func_data, num_matings):
        self.func_data = func_data
        self.num_matings = num_matings
        self.n_calls = 0
        self.name = "mating_{0}_topology_{1}_offspring_{2}.mol"
    
    def __call__(self, population):
        """
        Carries out mating operations on the supplied population.
        
        This function initially selects members of the population to
        be mated. The parents are then mated. This goes on until
        either all possible parents have been mated or the required
        number of successful mating operations have been performed.
        
        The offspring generated are returned together in a 
        ``Population`` instance. Any molecules that are created as a 
        result of mating that match a molecule present in the original 
        population are removed.
        
        Parameters
        ----------
        population : Population
            The population instance who's members are to mate.  
            
        Returns
        -------
        Population
            A population with all the offspring generated held in the
            `members` attribute. This does not include offspring which
            correspond to molecules already present in `population`.
        
        """
                
        # Create the parent pool by using `select('mating')`.
        parent_pool = population.select('mating')
        offspring_pop = Population(population.ga_tools)
        
        # Get the mating function object using the name of the mating
        # function supplied during initialization of the ``Mating`` 
        # instance.        
        func = getattr(self, self.func_data.name)
        
        # Keep a count of the number of successful matings.
        num_matings = 0
        for parents in parent_pool:         
            try:
                self.n_calls += 1
                # Apply the mating function and supply any additional
                # arguments to it.
                offspring = func(*parents, **self.func_data.params)
                # Add the new offspring to the offspring population.                
                offspring_pop.add_members(offspring)
                num_matings += 1
                print('Mating number {0}. Finish when {1}.'.format(
                                num_matings, self.num_matings))
                if num_matings == self.num_matings:
                    break
            except:
                continue

        # Make sure that only original molecules are left in the 
        # offspring population.
        offspring_pop -= population
        return offspring_pop

    """
    The following mating operations apply to ``Cage`` instances    
    
    """

    def bb_lk_exchange(self, cage1, cage2):
        """
        Exchanges the building-blocks* and linkers of cages.
        
        This operation is basically:
        
            > bb1-lk1 + bb2-lk2 --> bb1-lk2 + bb2-lk1,
            
        where bb-lk represents a building-block* - linker combination
        of a cage.
        
        If the parent cages do not have the same topology the pair of 
        offspring are created for each topology. This means that there
        may be up to 4 offspring. 
        
        Parameters
        ----------
        cage1 : Cage
            The first parent cage. Its building-block* and linker are
            combined with those of `cage2` to form new cages.
        
        cage2 : Cage
            The second parent cage. Its building-block* and linker are
            combined with those of `cage1` to form new cages.
        
        Returns
        -------
        Population
            A population of all the offspring generated by mating
            `cage1` with `cage2`.
        
        """
        
        # Make a variable for each building-block* and linker of each
        # each cage. Make set consisting of topologies of the cages
        # provided as arguments - this automatically removes copies.
        # For each topology create two offspring cages by combining the
        # building-block* of one cage with the linker of the other.
        # Place each new cage into a ``Population`` instance and return
        # that.
        
        # The build_block here refers to any building block, be it a
        # building-block* or linker. The first building block of the 
        # first cage is taken initially. This may be a linker or 
        # building-block*.
        build_block1 = cage1.building_blocks[0]
        # The counterpart to this ``build_block1`` is the 
        # ``BuildingBlock`` or ``Linker`` of the other cage which can be 
        # used together with build_block1 to make a new cage. For 
        # example if build_block1 is a ``BuildingBlock`` instance then
        # its counter part is the ``Linker`` instance in `cage2`. The
        # generator below returns the building block instance from cage2
        # which is not the same type as ``build_block1``. This means
        # that a ``BuildingBlock`` is paired up with a ``Linker`` and
        # vice versa.
        counterpart1 = next(x for x in cage2.building_blocks if 
                            type(build_block1) != type(x))
        # Same as above but for the other building block.
        build_block2 = cage1.building_blocks[1]
        counterpart2 = next(x for x in cage2.building_blocks if 
                            type(build_block2) != type(x))
        # Get all the topologies. A set automatically removes 
        # duplicates.
        topologies = {type(x.topology) for x in (cage1, cage2)}

        offspring_pop = Population()
        # For each topology create a new pair of offspring using the
        # building block pairings determined earlier.
        for index, topology in enumerate(topologies):
                        
            offspring1 = Cage((build_block1, counterpart1), topology, 
                              os.path.join(os.getcwd(),
                              self.name.format(self.n_calls, index, 1)))
                              
            offspring2 = Cage((build_block2, counterpart2), topology,
                              os.path.join(os.getcwd(),
                              self.name.format(self.n_calls, index, 2)))
            offspring_pop.add_members((offspring1, offspring2))
            
        return offspring_pop
        
        
from ..population import Population
from ..molecular import BuildingBlock, Linker, Cage, Polymer