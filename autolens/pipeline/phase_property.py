import inspect

from autolens.analysis import galaxy_prior as gp
from autolens.autopipe import model_mapper as mm


def phase_property(name):
    """
    Create a property that is tied to the non_linear instance determines whether to set itself as a constant or
    variable.

    Parameters
    ----------
    name: str
        The phase_name of this variable

    Returns
    -------
    property: property
        A property that appears to be an attribute of the phase but is really an attribute of constant or variable.
    """

    def fget(self):
        if hasattr(self.optimizer.constant, name):
            return getattr(self.optimizer.constant, name)
        elif hasattr(self.optimizer.variable, name):
            return getattr(self.optimizer.variable, name)

    def fset(self, value):
        if inspect.isclass(value) or isinstance(value, mm.PriorModel) or isinstance(value, gp.GalaxyPrior) or \
                isinstance(value, list):
            setattr(self.optimizer.variable, name, value)
            try:
                delattr(self.optimizer.constant, name)
            except AttributeError:
                pass
        else:
            setattr(self.optimizer.constant, name, value)
            try:
                delattr(self.optimizer.variable, name)
            except AttributeError:
                pass

    return property(fget=fget, fset=fset, doc=name)