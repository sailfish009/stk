"""
Defines :class:`Selector` classes.

:class:`Selector`s are classes which define the :meth:`Selector.select`
method, which is used to select molecules from a :class:`.Population`.
Examples of how :class:`Selector` classes can be used is given their
documentation, for example :class:`Fittest`, :class:`Roulette` or
:class:`AboveAverage`.

:class:`Selector`s can be combined to generate more complex selection
processes, such as stochastic sampling, using :class:`.Pipeline` or
:class:`SelectorFunnel`. Examples of how this can happen are given in
the documentation of these two classes.

.. _`adding selectors`:

Extending stk: Adding selectors.
--------------------------------

When a new :class:`Selector` is to be added it must inherit
:class:`Selector` and define a :meth:`~Selection.select` method.
:meth:`~Selection.select` must take a single argument, which is the
:class:`Population` from which molecules are selected.

"""

import itertools as it
import numpy as np
import logging


logger = logging.getLogger(__name__)


class Selector:
    """
    Selects batches of molecules from a population.

    Molecules are selected in batches, and each batch is selected
    based on its fitness. The fitness of a batch is the sum of all
    fitness values of the molecules in the batch. Batches may be of
    size 1, if single molecules are to be yielded.

    Attributes
    ----------
    num : :class:`int`
        The number of batches to yield. If ``None`` then yielding
        will continue forever or until the generator is exhausted,
        whichever comes first.

    duplicates : :class:`bool`
        If ``True`` the same member can be yielded in more than one
        batch.

    use_rank : :class:`bool`
        When ``True`` the fitness value of a molecule is calculated as
        ``f = 1/rank``.

    batch_size : :class:`int`
        The number of molecules yielded at once.

    """

    def __init__(self, num, duplicates, use_rank, batch_size):
        """
        Initializes a :class:`Selector` instance.

        Parameters
        ----------
        num : :class:`int`
            The number of batches to yield. If ``None`` then yielding
            will continue forever or until the generator is exhausted,
            whichever comes first.

        duplicates : :class:`bool`
            If ``True`` the same member can be yielded in more than one
            batch.

        use_rank : :class:`bool`
            When ``True`` the fitness value of a moleucle is calculated
            as ``f = 1/rank``.

        batch_size : :class:`int`
            The number of molecules yielded at once.

        """

        self.num = num
        self.duplicates = duplicates
        self.use_rank = use_rank
        self.batch_size = batch_size

    def _batch(self, population):
        """
        Batch molecules of `population` together.

        Parameters
        ----------
        population : :class:`.Population`
            A :class:`.Population` from which batches of molecules are
            selected.

        Yields
        ------
        :class:`tuple`
            A :class:`tuple` of form ``(batch, fitness)`` where
            ``batch`` is a :class:`tuple` of :class:`.Molecule` and
            ``fitness`` is a :class:`float` which is the sum of all
            fitness values of the molecules in the batch.

        """

        for batch in it.combinations(population, self.batch_size):
            yield batch, sum(m.fitness for m in batch)

    @staticmethod
    def _no_duplicates(batches):
        """
        Makes sure that no molecule is yielded in more than one batch.

        Parameters
        ----------
        batches : :class:`iterable`
            An :class:`iterable` yielding :class:`tuple` of form
            ``(batch, fitness)`` where ``batch`` is a :class:`tuple`
            of :class:`.Molecule`.

        Yields
        ------
        :class:`tuple`
            A :class:`tuple` of form ``(batch, fitness)`` where
            ``batch`` is a :class:`tuple` of :class:`.Molecule` and
            ``fitness`` is a :class:`float`.

        """

        seen = set()
        for batch, fitness in batches:
            if all(mol not in seen for mol in batch):
                seen.update(batch)
                yield batch, fitness

    def select(self, population):
        """
        Selects batches of molecules from `population`.

        Parameters
        ----------
        population : :class:`.Population`
            A :class:`.Population` from which batches of molecules are
            selected.

        Yields
        ------
        :class:`tuple` of :class:`.Molecule`
            A batch of selected molecules.

        """

        return NotImplementedError()


class SelectorFunnel(Selector):
    """
    Applies :class:`Selector`s in order.

    Each :class:`Selector` in :attr:`selectors` is used until
    exhaustion. The molecules selected by each :class:`Selector`
    are passed to the next one for selection. As a result, only the
    final :class:`Selector` can yield batches of size greater than 1.

    Attributes
    ----------
    selectors : :class:`tuple` of :class:`Selector`
        The :class:`Selector`s used to select molecules. For all
        except the last :attr:`num` must be ``1``.

    Examples
    --------
    Use :class:`Roulette` on only the 10 molecules with the highest
    fitness.

    .. code-block:: python

        # Make a population with 20 molecules.
        pop = Population(...)

        # Create a Selector which yields the top 10 molecules according
        # to roulette selection.
        fittest = Fittest(num=10)
        roulette = Roulette()
        elitist_roulette = SelectorFunnel(fittest, roulette)

        # Use the selector to yield molecules.
        for selected_mol in elitist_roulette.select(pop):
            # Do something with the selected molecules.
            ...

    """

    def __init__(self, *selectors):
        """
        Initializes a :class:`SelectorFunnel` instance.

        Parameters
        ----------
        *selectors : :class:`Selector`
            The :class:`Selector`s used to select molecules. For all
            except the last :attr:`num` must be ``1``.

        """

        self.selectors = selectors

    def select(self, population):
        """
        Yields batches of molecules.

        Parameters
        ----------
        population : :class:`.Population`
            A :class:`.Population` from which batches of molecules are
            selected.

        Yields
        ------
        :class:`tuple` of :class:`.Molecule`
            A batch of selected molecules.

        """

        for selector in self.selectors:
            population = [mol for mol, in selector.select(population)]


class Fittest(Selector):
    """
    Selects batches of molcules, fittest first.

    The fitness of a batch is the sum of the fitness values of the
    molecules in the batch.

    Examples
    --------
    Yielding molecules one at a time. For example, if molecules need
    to be selected for mutation or the next generation.

    .. code-block:: python

        # Make a population holding some molecules.
        pop = Population(...)

        # Make the selector.
        fittest = Fittest()

        # Select the molecules.
        for selected, in fittest.select(pop):
            # Do stuff with each selected molecule, like apply a
            # mutation to it to generate a mutant.
            mutant = mutator.mutate(selected)

    Yielding multiple molecules at once. For example, if molecules need
    to be selected for crossover.

    .. code-block:: python

        # Make a population holding some molecules.
        pop = Population(...)

        # Make the selector.
        fittest = Fittest(batch_size=2)

        # Select the molecules.
        for selected in fittest.select(pop):
            # selected is a tuple of length 2, holding the selected
            # molecules. You can do stuff with the selected molecules
            # Like apply crossover operations on them.
            offspring = list(crosser.crossover(*selectd))

    """

    def __init__(self, num=None, duplicates=True, batch_size=1):
        """
        Initializes a :class:`Fittest` instance.

        Parameters
        ----------
        num : :class:`int`, optional
            The number of batches to yield. If ``None`` then yielding
            will continue until the generator is exhausted.

        duplicates : :class:`bool`, optional
            If ``True``, the same molecule can be yielded in more than
            one batch.

        batch_size : :class:`int`, optional
            The number of molecules yielded at once.

        """

        super(num=num,
              duplicates=duplicates,
              use_rank=False,
              batch_size=batch_size)

    def select(self, population):
        """
        Yields batches of molecules, fittest first.

        Parameters
        ----------
        population : :class:`.Population`
            A :class:`.Population` from which batches of molecules are
            selected.

        Yields
        ------
        :class:`tuple` of :class:`.Molecule`
            A batch of selected molecules.

        """

        batches = self._batch(population)

        # Sort by total fitness value of each batch.
        batches = sorted(batches, reverse=True, key=lambda x: x[1])

        if not self.duplicates:
            batches = self._no_duplicates(batches)

        for i, (batch, fitness) in enumerate(batches):
            if i >= self.num:
                break
            yield batch


class Roulette(Selector):
    """
    Uses roulette selection to select batches of molecules.

    In roulette selection the probability a batch is selected
    is given by its fitness. If the total fitness is the sum of all
    fitness values, the chance a batch is selected is given
    by::

        p = batch fitness / total fitness,

    where ``p`` is the probability of selection and the batch
    fitness is the sum of all fitness values of molecules in the
    batch [#]_.

    References
    ----------
    .. [#] http://tinyurl.com/csc3djm

    Examples
    --------
    Yielding molecules one at a time. For example, if molecules need
    to be selected for mutation or the next generation.

    .. code-block:: python

        # Make a population holding some molecules.
        pop = Population(...)

        # Make the selector.
        roulette = Roulette()

        # Select the molecules.
        for selected, in roulette.select(pop):
            # Do stuff with each selected molecule, like apply a
            # mutation to it to generate a mutant.
            mutant = mutator.mutate(selected)

    Yielding multiple molecules at once. For example, if molecules need
    to be selected for crossover.

    .. code-block:: python

        # Make a population holding some molecules.
        pop = Population(...)

        # Make the selector.
        roulette = Roulette(batch_size=2)

        # Select the molecules.
        for selected in roulette.select(pop):
            # selected is a tuple of length 2, holding the selected
            # molecules. You can do stuff with the selected molecules
            # Like apply crossover operations on them.
            offspring = list(crosser.crossover(*selectd))

    """

    def __init__(self,
                 num=None,
                 duplicates=True,
                 use_rank=False,
                 batch_size=1):
        """
        Initializes a :class:`Roulette` instance.

        Parameters
        ----------
        num : :class:`int`, optional
            The number of batches to yield. If ``None`` then yielding
            will continue forever or until the generator is exhausted,
            whichever comes first.

        duplicates : :class:`bool`, optional
            If ``True`` the same member can be yielded in more than
            one batch.

        use_rank : :class:`bool`, optional
            When ``True`` the fitness value of an individual is
            calculated as ``f = 1/rank``.

        batch_size : :class:`int`, optional
            The number of molecules yielded at once.

        """

        super(num=num,
              duplicates=duplicates,
              use_rank=use_rank,
              batch_size=batch_size)

    def select(self, population):
        """
        Yields batches of molecules using roulette selection.

        Parameters
        ----------
        population : :class:`.Populaion`
            A :class:`.Population` from which batches of molecules are
            selected.

        Yields
        ------
        :class:`tuple` of :class:`.Molecule`
            A batch of selected molecules.

        """

        yielded = set()

        valid_pop = list(population)
        yields = 0
        while len(valid_pop) >= self.batch_size and yields < self.num:

            if self.use_rank:
                ranks = range(1, len(valid_pop)+1)
                total = sum(1/rank for rank in ranks)

                ranks = range(1, len(valid_pop)+1)
                weights = [1/(rank*total) for rank in ranks]

                valid_pop = sorted(valid_pop, reverse=True)

            else:
                total = sum(mol.fitness for mol in valid_pop)
                weights = [mol.fitness / total for mol in valid_pop]

            selected = tuple(np.random.choice(a=valid_pop,
                                              size=self.batch_size,
                                              replace=False,
                                              p=weights))
            yield selected
            yields += 1
            if not self.duplicates:
                yielded.update(selected)
                valid_pop = [
                    ind for ind in population if ind not in yielded
                ]


class AboveAverage(Selector):
    """
    Yields above average batches of molecules.

    The fitness of a batch is the sum of all fitness values of the
    molecules in the batch. Contrary to the name, this selector will
    also yield a batch which has exactly average fitness.

    Attributes
    ----------
    duplicate_batches : :class:`bool`
        If ``True``, the same batch may be yielded more than once. For
        example, if the batch has a fitness twice above average it will
        be yielded twice, if it has a fitness three times above
        average, it will be yielded three times and so on.

    Examples
    --------
    Yielding molecules one at a time. For example, if molecules need
    to be selected for mutation or the next generation.

    .. code-block:: python

        # Make a population holding some molecules.
        pop = Population(...)

        # Make the selector.
        above_avg = AboveAverage()

        # Select the molecules.
        for selected, in above_avg.select(pop):
            # Do stuff with each selected molecule, like apply a
            # mutation to it to generate a mutant.
            mutant = mutator.mutate(selected)

    Yielding multiple molecules at once. For example, if molecules need
    to be selected for crossover.

    .. code-block:: python

        # Make a population holding some molecules.
        pop = Population(...)

        # Make the selector.
        above_avg = AboveAverage(batch_size=2)

        # Select the molecules.
        for selected in above_avg.select(pop):
            # selected is a tuple of length 2, holding the selected
            # molecules. You can do stuff with the selected molecules
            # Like apply crossover operations on them.
            offspring = list(crosser.crossover(*selectd))

    """

    def __init__(self,
                 duplicate_batches=False,
                 num=None,
                 duplicates=True,
                 use_rank=False,
                 batch_size=1):
        """
        Initializes a :class:`AboveAverage` instance.

        Parameters
        ----------
        duplicate_batches : :class:`bool`, optional
            If ``True``, the same batch may be yielded more than
            once. For example, if the batch has a fitness twice above
            average it will be yielded twice, if it has a fitness
            three times above average, it will be yielded three times
            and so on.

        num : :class:`int`, optional
            The number of batches to yield. If ``None`` then yielding
            will continue forever or until the generator is exhausted,
            whichever comes first.

        duplicates : :class:`bool`, optional
            If ``True``, the same molecule can be yielded in more than
            one batch.

        use_rank : :class:`bool`, optional
            When ``True`` the fitness value of an individual is
            calculated as ``f = 1/rank``.

        batch_size : :class:`int`, optional
            The number of molecules yielded at once.

        """

        self.duplicate_batches = duplicate_batches
        super(num=num,
              duplicates=duplicates,
              use_rank=use_rank,
              batch_size=batch_size)

    def select(self, population):
        """
        Yields above average fitness batches of molecules.

        Parameters
        ----------
        population : :class:`.Populaion`
            The population from which individuals are to be selected.

        Yields
        ------
        :class:`tuple` of :class:`.Molecule`
            The next selected batch of molecules.

        """

        mean = np.mean([
            fitness for batch, fitness in self._batch(population)
        ])

        # Sort the batches so that highest fitness batches are
        # yielded first. This is neccessary because if not all batches
        # will be yielded, we want the molecules to appear in the
        # batches of the highest fitness. The same is true for when
        # self.duplicates is False. If duplicates is False then we want
        # molecules to appear in their optimal batch only.
        batches = sorted(self._batch(population),
                         reverse=True,
                         key=lambda x: x[-1])

        if self.duplicates:
            batches = self._no_duplicates(batches)

        for i, (batch, fitness) in enumerate(batches):
            if i >= self.num:
                break

            if fitness >= mean:
                n = fitness // mean if self.duplicate_batches else 1
                for i in range(int(n)):
                    yield batch
