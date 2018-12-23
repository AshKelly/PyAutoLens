from autolens.lensing import lensing_fitters
from autolens.lensing import ray_tracing

class AbstractSensitivityFit(object):

    def __init__(self, tracer_normal, tracer_sensitive):

        self.tracer_normal = tracer_normal
        self.tracer_sensitive = tracer_sensitive

class SensitivityProfileFitter(AbstractSensitivityFit):

    def __init__(self, lensing_image, tracer_normal, tracer_sensitive):
        """Evaluate the sensitivity of a profile fit to a specific component of a lens model and tracer. This is \
        performed by evaluating the likelihood of a fit to an image using two tracers:

        1) A 'normal tracer', which uses the same lens model as a the simulated lensing image. This gives a baseline \
           value of the likelihood we can expect when we fit the model to itself.,
        2) A 'sensitive tracer', which uses the same lens model as the simulated lensing image, but also includes the \
           additional model components (e.g. a mass clump 'subhalo') which we are testing our sensitivity to.

        The difference in likelihood of these two fits informs us of how sensitive we are to the component in the \
        second tracer. For example, if the difference in likelihood is neglible, it means the model component had no \
        impact on our fit, meaning we are not sensitive to its properties.

        Parameters
        ----------
        lensing_image: li.LensingImage
            A simulated lensing image which is used to determine our sensitiivity to specific model components.
        tracer_normal : ray_tracing.Tracer
            A tracer whose galaxies have the same model components (e.g. light profiles, mass profiles) as the \
            lensing image that we are fitting.
       tracer_sensitive : ray_tracing.AbstractTracerNonStack
            A tracer whose galaxies have the same model components (e.g. light profiles, mass profiles) as the \
            lensing image that we are fitting, but also addition components (e.g. mass clumps) which we measure \
            how sensitive we are too.
        """
        AbstractSensitivityFit.__init__(self=self, tracer_normal=tracer_normal, tracer_sensitive=tracer_sensitive)
        self.fit_normal = lensing_fitters.LensingProfileFitter(lensing_image=lensing_image, tracer=tracer_normal)
        self.fit_sensitive = lensing_fitters.LensingProfileFitter(lensing_image=lensing_image, tracer=tracer_sensitive)

    @property
    def figure_of_merit(self):
        return self.fit_sensitive.likelihood - self.fit_normal.likelihood