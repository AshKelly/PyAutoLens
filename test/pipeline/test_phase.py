import os
from os import path

import numpy as np
import pytest
from astropy import cosmology as cosmo
from autofit import conf
from autofit.mapper import model_mapper as mm
from autofit.mapper import prior
from autofit.optimize import non_linear

from autolens import exc
from autolens.data import ccd
from autolens.data.array import grids, mask as msk
from autolens.data.array import scaled_array
from autolens.lens import lens_data as li
from autolens.lens import lens_fit
from autolens.model.galaxy import galaxy as g, galaxy_model as gm
from autolens.model.inversion import pixelizations as pix
from autolens.model.inversion import regularization as reg
from autolens.model.profiles import light_profiles as lp, mass_profiles as mp
from autolens.pipeline import phase as ph

pytestmark = pytest.mark.filterwarnings(
    "ignore:Using a non-tuple sequence for multidimensional indexing is deprecated; use `arr[tuple(seq)]` instead of "
    "`arr[seq]`. In the future this will be interpreted as an array index, `arr[np.array(seq)]`, which will result "
    "either in an error or a different result.")

directory = path.dirname(path.realpath(__file__))


@pytest.fixture(scope="session", autouse=True)
def do_something():
    conf.instance = conf.Config(
        '{}/../test_files/configs/phase'.format(directory))


shape = (10, 10)


class MockAnalysis(object):

    def __init__(self, number_galaxies, value):
        self.number_galaxies = number_galaxies
        self.value = value

    # noinspection PyUnusedLocal
    def galaxy_images_for_model(self, model):
        return self.number_galaxies * [np.array([self.value])]


class MockResults(object):
    def __init__(self, model_image=None, galaxy_images=(), constant=None, analysis=None, optimizer=None):
        self.model_image = model_image
        self.galaxy_images = galaxy_images
        self.constant = constant or mm.ModelInstance()
        self.variable = mm.ModelMapper()
        self.analysis = analysis
        self.optimizer = optimizer


class NLO(non_linear.NonLinearOptimizer):
    def fit(self, analysis):
        class Fitness(object):
            def __init__(self, instance_from_physical_vector, constant):
                self.result = None
                self.instance_from_physical_vector = instance_from_physical_vector
                self.constant = constant

            def __call__(self, vector):
                instance = self.instance_from_physical_vector(vector)
                instance += self.constant

                likelihood = analysis.fit(instance)
                self.result = non_linear.Result(instance, likelihood)

                # Return Chi squared
                return -2 * likelihood

        fitness_function = Fitness(self.variable.instance_from_physical_vector, self.constant)
        fitness_function(self.variable.prior_count * [0.8])

        return fitness_function.result


@pytest.fixture(name="grid_stack")
def make_grids(lens_data):
    return grids.GridStack.grid_stack_from_mask_sub_grid_size_and_psf_shape(
        lens_data.mask, 1, lens_data.psf.shape)


@pytest.fixture(name="phase")
def make_phase():
    return ph.LensSourcePlanePhase(optimizer_class=NLO, mask_function=ph.default_mask_function, phase_name='test_phase')


@pytest.fixture(name="galaxy")
def make_galaxy():
    return g.Galaxy()


@pytest.fixture(name="galaxy_model")
def make_galaxy_model():
    return gm.GalaxyModel()


@pytest.fixture(name="ccd_data")
def make_ccd_data():
    pixel_scale = 1.0

    image = scaled_array.ScaledSquarePixelArray(array=np.array(np.zeros(shape)), pixel_scale=pixel_scale)
    psf = ccd.PSF(array=np.ones((3, 3)), pixel_scale=pixel_scale)
    noise_map = ccd.NoiseMap(np.ones(shape), pixel_scale=1.0)

    return ccd.CCDData(image=image, pixel_scale=pixel_scale, psf=psf, noise_map=noise_map)


@pytest.fixture(name="lens_data")
def make_lens_image():
    ccd_data = ccd.CCDData(np.array(np.zeros(shape)), pixel_scale=1.0, psf=ccd.PSF(np.ones((3, 3)), pixel_scale=1.0),
                           noise_map=ccd.NoiseMap(np.ones(shape), pixel_scale=1.0))
    mask = msk.Mask.circular(shape=shape, pixel_scale=1, radius_arcsec=3.0)
    return li.LensData(ccd_data=ccd_data, mask=mask)


@pytest.fixture(name="results")
def make_results():
    return MockResults(np.ones(shape),
                       galaxy_images=[np.ones(shape), np.ones(shape)])


@pytest.fixture(name="results_collection")
def make_results_collection(results):
    return ph.ResultsCollection([results])


class TestAutomaticPriorPassing(object):

    def test_galaxy_model_dict(self, phase, galaxy_model):
        phase.lens_galaxies = dict(galaxy_one=galaxy_model)
        assert phase.galaxy_model_tuples == [("galaxy_one", galaxy_model)]

    def test_match_galaxy_models_by_name(self, phase, galaxy_model, galaxy):
        phase.lens_galaxies = dict(galaxy_one=galaxy_model)
        instance = mm.ModelInstance()
        instance.galaxy_one = galaxy

        assert phase.match_instance_to_models(instance) == [("galaxy_one", galaxy, galaxy_model)]

    def test_phase_property_collections(self, phase):
        assert phase.phase_property_collections == [phase.lens_galaxies, phase.source_galaxies]

    # noinspection PyUnresolvedReferences
    def test_fit_priors(self, phase, galaxy_model, galaxy):
        argument_tuples = []

        new_galaxy_model = gm.GalaxyModel()

        def fitting_function(best_fit_galaxy, initial_galaxy_model):
            argument_tuples.append((best_fit_galaxy, initial_galaxy_model))
            return new_galaxy_model

        phase.lens_galaxies = dict(galaxy_one=galaxy_model)
        assert phase.lens_galaxies.galaxy_one is not None

        instance = mm.ModelInstance()
        instance.galaxy_one = galaxy

        phase.fit_priors(instance, fitting_function)

        assert phase.lens_galaxies.galaxy_one == new_galaxy_model
        assert argument_tuples == [(galaxy, galaxy_model)]

    def test_model_instance_sum_priority(self):
        instance_1 = mm.ModelInstance()
        galaxy_1 = g.Galaxy()
        instance_1.galaxy = galaxy_1

        instance_2 = mm.ModelInstance()
        galaxy_2 = g.Galaxy()
        instance_2.galaxy = galaxy_2

        assert (instance_1 + instance_2).galaxy == galaxy_2

    # noinspection PyUnresolvedReferences
    def test_fit_priors_with_results(self, phase):
        argument_tuples = []

        galaxy_model_one = gm.GalaxyModel()
        galaxy_model_two = gm.GalaxyModel()

        new_galaxy_model_one = gm.GalaxyModel()
        new_galaxy_model_two = gm.GalaxyModel()

        new_galaxy_models = {galaxy_model_one: new_galaxy_model_one, galaxy_model_two: new_galaxy_model_two}

        def fitting_function(best_fit_galaxy, initial_galaxy_model):
            argument_tuples.append((best_fit_galaxy, initial_galaxy_model))
            return new_galaxy_models[initial_galaxy_model]

        phase.lens_galaxies = dict(galaxy_one=galaxy_model_one, galaxy_two=galaxy_model_two)

        instance_one = mm.ModelInstance()
        galaxy_one = g.Galaxy()
        instance_one.galaxy_one = galaxy_one
        instance_one.galaxy_two = g.Galaxy()
        results_one = MockResults(constant=instance_one)

        instance_two = mm.ModelInstance()
        galaxy_two = g.Galaxy()
        instance_two.galaxy_two = galaxy_two
        results_two = MockResults(constant=instance_two)

        assert phase.lens_galaxies.galaxy_one == galaxy_model_one
        assert phase.lens_galaxies.galaxy_two == galaxy_model_two

        phase.fit_priors_with_results([results_one, results_two], fitting_function)

        assert phase.lens_galaxies.galaxy_one == new_galaxy_model_one
        assert phase.lens_galaxies.galaxy_two == new_galaxy_model_two
        assert argument_tuples == [(galaxy_one, galaxy_model_one),
                                   (galaxy_two, galaxy_model_two)]


def clean_images():
    try:
        os.remove('{}/source_lens_phase/source_image_0.fits'.format(directory))
        os.remove('{}/source_lens_phase/lens_image_0.fits'.format(directory))
        os.remove('{}/source_lens_phase/model_image_0.fits'.format(directory))
    except FileNotFoundError:
        pass
    conf.instance.data_path = directory


class TestPhase(object):

    def test_set_constants(self, phase, galaxy):
        phase.lens_galaxies = [galaxy]
        assert phase.optimizer.constant.lens_galaxies == [galaxy]
        assert phase.optimizer.variable.lens_galaxies == []

    def test_set_variables(self, phase, galaxy_model):
        phase.lens_galaxies = [galaxy_model]
        assert phase.optimizer.variable.lens_galaxies == [galaxy_model]
        assert phase.optimizer.constant.lens_galaxies == []

    def test_make_analysis(self, phase, ccd_data, lens_data):
        analysis = phase.make_analysis(data=ccd_data)
        assert analysis.last_results is None
        assert analysis.lens_data.image == ccd_data.image
        assert analysis.lens_data.noise_map == ccd_data.noise_map
        assert analysis.lens_data.image == lens_data.image
        assert analysis.lens_data.noise_map == lens_data.noise_map

    def test_make_analysis__mask_input_uses_mask__no_mask_uses_mask_function(self, phase, ccd_data):

        # If an input mask is supplied and there is no mask function, we use mask input.

        phase.mask_function = None

        mask_input = msk.Mask.circular(shape=shape, pixel_scale=1, radius_arcsec=2.0)

        analysis = phase.make_analysis(data=ccd_data, mask=mask_input)
        assert (analysis.lens_data.mask == mask_input).all()

        # If a mask function is suppled, we should use this mask, regardless of whether an input mask is supplied.

        def mask_function(image):
            return msk.Mask.circular(shape=image.shape, pixel_scale=1, radius_arcsec=1.4)

        mask_from_function = mask_function(image=ccd_data.image)
        phase.mask_function = mask_function

        analysis = phase.make_analysis(data=ccd_data, mask=None)
        assert (analysis.lens_data.mask == mask_from_function).all()
        analysis = phase.make_analysis(data=ccd_data, mask=mask_input)
        assert (analysis.lens_data.mask == mask_from_function).all()

        # If no mask is suppled, nor a mask function, we should use the default mask.

        mask_default = ph.default_mask_function(image=ccd_data.image)
        phase.mask_function = None
        analysis = phase.make_analysis(data=ccd_data, mask=None)
        assert (analysis.lens_data.mask == mask_default).all()

    def test_make_analysis__mask_input_uses_mask__inner_mask_radius_included_which_masks_centre(self, phase, ccd_data):

        # If an input mask is supplied and there is no mask function, we use mask input.

        phase.mask_function = None
        phase.inner_circular_mask_radii = 1.0

        mask_input = msk.Mask.circular(shape=shape, pixel_scale=1, radius_arcsec=2.0)

        analysis = phase.make_analysis(data=ccd_data, mask=mask_input)

        # The inner circulaar mask radii of 1.0" masks the centra pixels of the mask
        mask_input[4:6, 4:6] = True

        assert (analysis.lens_data.mask == mask_input).all()

        # If a mask function is suppled, we should use this mask, regardless of whether an input mask is supplied.

        def mask_function(image):
            return msk.Mask.circular(shape=image.shape, pixel_scale=1, radius_arcsec=1.4)

        mask_from_function = mask_function(image=ccd_data.image)
        # The inner circulaar mask radii of 1.0" masks the centra pixels of the mask
        mask_from_function[4:6, 4:6] = True

        phase.mask_function = mask_function

        analysis = phase.make_analysis(data=ccd_data, mask=None)
        assert (analysis.lens_data.mask == mask_from_function).all()
        analysis = phase.make_analysis(data=ccd_data, mask=mask_input)
        assert (analysis.lens_data.mask == mask_from_function).all()

        # If no mask is suppled, nor a mask function, we should use the default mask.

        mask_default = ph.default_mask_function(image=ccd_data.image)
        # The inner circulaar mask radii of 1.0" masks the centra pixels of the mask
        mask_default[4:6, 4:6] = True

        phase.mask_function = None
        analysis = phase.make_analysis(data=ccd_data, mask=None)
        assert (analysis.lens_data.mask == mask_default).all()

    def test_make_analysis__positions_are_input__are_used_in_analysis(self, phase, ccd_data):

        # If use positions is true and positions are input, make the positions part of the lens data.

        phase.use_positions = True

        analysis = phase.make_analysis(data=ccd_data, positions=[[[1.0, 1.0], [2.0, 2.0]]])
        assert (analysis.lens_data.positions[0][0] == np.array([1.0, 1.0])).all()
        assert (analysis.lens_data.positions[0][1] == np.array([2.0, 2.0])).all()

        # If use positions is true but no positions are supplied, raise an error

        with pytest.raises(exc.PhaseException):
           phase.make_analysis(data=ccd_data, positions=None)
           phase.make_analysis(data=ccd_data)

        # If use positions is False, positions should always be None.

        phase.use_positions = False
        analysis = phase.make_analysis(data=ccd_data, positions=[[[1.0, 1.0], [2.0, 2.0]]])
        assert analysis.lens_data.positions == None

    def test__make_analysis__phase_info_is_made(self, phase, ccd_data):

        analysis = phase.make_analysis(data=ccd_data)

        file_phase_info = "{}/{}/{}".format(conf.instance.output_path, phase.phase_name, 'phase.info')

        phase_info = open(file_phase_info, 'r')

        optimizer = phase_info.readline()
        sub_grid_size = phase_info.readline()
        image_psf_shape = phase_info.readline()
        pixelization_psf_shape = phase_info.readline()
        use_positions = phase_info.readline()
        positions_threshold = phase_info.readline()
        cosmology = phase_info.readline()
        auto_link_priors = phase_info.readline()

        phase_info.close()

        assert optimizer == 'Optimizer = NLO \n'
        assert sub_grid_size == 'Sub-grid size = 2 \n'
        assert image_psf_shape == 'Image PSF shape = None \n'
        assert pixelization_psf_shape == 'Pixelization PSF shape = None \n'
        assert use_positions == 'Use positions = False \n'
        assert positions_threshold == 'Positions Threshold = 0.5 \n'
        assert cosmology == 'Cosmology = FlatLambdaCDM(name="Planck15", H0=67.7 km / (Mpc s), Om0=0.307, Tcmb0=2.725 K, ' \
                            'Neff=3.05, m_nu=[0.   0.   0.06] eV, Ob0=0.0486) \n'
        assert auto_link_priors == 'Auto Link Priors = False \n'

    def test_fit(self, ccd_data):
        clean_images()

        phase = ph.LensSourcePlanePhase(optimizer_class=NLO,
                                        lens_galaxies=[gm.GalaxyModel(light=lp.EllipticalSersic)],
                                        source_galaxies=[gm.GalaxyModel(light=lp.EllipticalSersic)],
                                        phase_name='test_phase')
        result = phase.run(data=ccd_data)
        assert isinstance(result.constant.lens_galaxies[0], g.Galaxy)
        assert isinstance(result.constant.source_galaxies[0], g.Galaxy)

    def test_customize(self, results, ccd_data):
        class MyPlanePhaseAnd(ph.LensSourcePlanePhase):
            def pass_priors(self, previous_results):
                self.lens_galaxies = previous_results.last.constant.lens_galaxies
                self.source_galaxies = previous_results.last.variable.source_galaxies

        galaxy = g.Galaxy()
        galaxy_model = gm.GalaxyModel()

        setattr(results.constant, "lens_galaxies", [galaxy])
        setattr(results.variable, "source_galaxies", [galaxy_model])

        phase = MyPlanePhaseAnd(optimizer_class=NLO, phase_name='test_phase')
        phase.make_analysis(data=ccd_data, previous_results=ph.ResultsCollection([results]))

        assert phase.lens_galaxies == [galaxy]
        assert phase.source_galaxies == [galaxy_model]

    def test_default_mask_function(self, phase, ccd_data):
        lens_data = li.LensData(ccd_data=ccd_data, mask=phase.mask_function(ccd_data.image))
        assert len(lens_data.image_1d) == 32

    def test_duplication(self):
        phase = ph.LensSourcePlanePhase(lens_galaxies=[gm.GalaxyModel()], source_galaxies=[gm.GalaxyModel()],
                                        phase_name='test_phase')

        ph.LensSourcePlanePhase(phase_name='test_phase')

        assert phase.lens_galaxies is not None
        assert phase.source_galaxies is not None

    def test_modify_image(self, ccd_data):
        class MyPhase(ph.PhaseImaging):
            def modify_image(self, image, previous_results):
                assert ccd_data.image.shape == image.shape
                image = 20.0*np.ones(shape=shape)
                return image

        phase = MyPhase(phase_name='phase')
        analysis = phase.make_analysis(data=ccd_data)
        assert (analysis.lens_data.image == 20.0*np.ones(shape=shape)).all()
        assert (analysis.lens_data.image_1d == 20.0*np.ones(shape=32)).all()

    def test__tracer_for_instance__includes_cosmology(self, ccd_data):
        lens_galaxy = g.Galaxy()
        source_galaxy = g.Galaxy()

        phase = ph.LensPlanePhase(lens_galaxies=[lens_galaxy], cosmology=cosmo.FLRW, phase_name='test_phase')
        analysis = phase.make_analysis(ccd_data)
        instance = phase.constant
        tracer = analysis.tracer_for_instance(instance)
        padded_tracer = analysis.padded_tracer_for_instance(instance)

        assert tracer.image_plane.galaxies[0] == lens_galaxy
        assert tracer.cosmology == cosmo.FLRW
        assert padded_tracer.image_plane.galaxies[0] == lens_galaxy
        assert padded_tracer.cosmology == cosmo.FLRW

        phase = ph.LensSourcePlanePhase(lens_galaxies=[lens_galaxy], source_galaxies=[source_galaxy],
                                        cosmology=cosmo.FLRW, phase_name='test_phase')
        analysis = phase.make_analysis(ccd_data)
        instance = phase.constant
        tracer = analysis.tracer_for_instance(instance)
        padded_tracer = analysis.padded_tracer_for_instance(instance)

        assert tracer.image_plane.galaxies[0] == lens_galaxy
        assert tracer.source_plane.galaxies[0] == source_galaxy
        assert tracer.cosmology == cosmo.FLRW
        assert padded_tracer.image_plane.galaxies[0] == lens_galaxy
        assert padded_tracer.source_plane.galaxies[0] == source_galaxy
        assert padded_tracer.cosmology == cosmo.FLRW

        galaxy_0 = g.Galaxy(redshift=0.1)
        galaxy_1 = g.Galaxy(redshift=0.2)
        galaxy_2 = g.Galaxy(redshift=0.3)

        phase = ph.MultiPlanePhase(galaxies=[galaxy_0, galaxy_1, galaxy_2], cosmology=cosmo.WMAP7,
                                   phase_name='test_phase')
        analysis = phase.make_analysis(ccd_data)
        instance = phase.constant
        tracer = analysis.tracer_for_instance(instance)
        padded_tracer = analysis.padded_tracer_for_instance(instance)

        assert tracer.planes[0].galaxies[0] == galaxy_0
        assert tracer.planes[1].galaxies[0] == galaxy_1
        assert tracer.planes[2].galaxies[0] == galaxy_2
        assert tracer.cosmology == cosmo.WMAP7
        assert padded_tracer.planes[0].galaxies[0] == galaxy_0
        assert padded_tracer.planes[1].galaxies[0] == galaxy_1
        assert padded_tracer.planes[2].galaxies[0] == galaxy_2
        assert padded_tracer.cosmology == cosmo.WMAP7

    def test__fit_figure_of_merit__matches_correct_fit_given_galaxy_profiles(self, ccd_data):

        lens_galaxy = g.Galaxy(light=lp.EllipticalSersic(intensity=0.1))
        source_galaxy = g.Galaxy(pixelization=pix.Rectangular(shape=(4, 4)),
                                 regularization=reg.Constant(coefficients=(1.0,)))

        phase = ph.LensPlanePhase(lens_galaxies=[lens_galaxy], mask_function=ph.default_mask_function,
                                  cosmology=cosmo.FLRW, phase_name='test_phase')
        analysis = phase.make_analysis(data=ccd_data)
        instance = phase.constant
        fit_figure_of_merit = analysis.fit(instance=instance)

        mask = phase.mask_function(image=ccd_data.image)
        lens_data = li.LensData(ccd_data=ccd_data, mask=mask)
        tracer = analysis.tracer_for_instance(instance=instance)
        fit = lens_fit.LensProfileFit(lens_data=lens_data, tracer=tracer)

        assert fit.likelihood == fit_figure_of_merit

        phase = ph.LensSourcePlanePhase(lens_galaxies=[lens_galaxy], source_galaxies=[source_galaxy],
                                        mask_function=ph.default_mask_function, cosmology=cosmo.FLRW,
                                        phase_name='test_phase')
        analysis = phase.make_analysis(data=ccd_data)
        instance = phase.constant
        fit_figure_of_merit = analysis.fit(instance=instance)

        mask = phase.mask_function(image=ccd_data.image)
        lens_data = li.LensData(ccd_data=ccd_data, mask=mask)
        tracer = analysis.tracer_for_instance(instance=instance)
        fit = lens_fit.LensProfileInversionFit(lens_data=lens_data, tracer=tracer)

        assert fit.evidence == fit_figure_of_merit

    # TODO : Need to test using results

    # def test_unmasked_model_image_for_instance(self, image_):
    #
    #     lens_galaxy = g.Galaxy(light_profile=lp.SphericalSersic(intensity=1.0))
    #     image_padded_grid = msk.PaddedRegularGrid.unmasked_grid_from_shapes_and_pixel_scale(shape=image_.shape,
    #                                                                                         psf_shape=image_.psf.shape,
    #                                                                                         pixel_scale=image_.pixel_scale)
    #     image_1d = lens_galaxy.intensities_from_grid(image_padded_grid)
    #     blurred_image_1d = image_padded_grid.convolve_array_1d_with_psf(image_1d, image_.psf)
    #     blurred_image = image_padded_grid.scaled_array_from_array_1d(blurred_image_1d)
    #
    #     phase = ph.LensPlanePhase(lens_galaxies=[lens_galaxy])
    #     analysis = phase.make_analysis(image_)
    #     instance = phase.constant
    #     unmasked_tracer = analysis.unmasked_tracer_for_instance(instance)
    #     unmasked_model_image = analysis.unmasked_model_image_for_tracer(unmasked_tracer)
    #
    #     assert blurred_image == pytest.approx(unmasked_model_image, 1e-4)
    #
    # def test_unmasked_model_images_of_galaxies_for_instance(self, image_):
    #
    #     g0= g.Galaxy(light_profile=lp.SphericalSersic(intensity=1.0))
    #     g1 = g.Galaxy(light_profile=lp.SphericalSersic(intensity=2.0))
    #
    #     image_padded_grid = msk.PaddedRegularGrid.unmasked_grid_from_shapes_and_pixel_scale(shape=image_.shape,
    #                                                                                         psf_shape=image_.psf.shape,
    #                                                                                         pixel_scale=image_.pixel_scale)
    #
    #     g0_image_1d = g0.intensities_from_grid(image_padded_grid)
    #     g0_blurred_image_1d = image_padded_grid.convolve_array_1d_with_psf(g0_image_1d, image_.psf)
    #     g0_blurred_image = image_padded_grid.scaled_array_from_array_1d(g0_blurred_image_1d)
    #
    #     g1_image_1d = g1.intensities_from_grid(image_padded_grid)
    #     g1_blurred_image_1d = image_padded_grid.convolve_array_1d_with_psf(g1_image_1d, image_.psf)
    #     g1_blurred_image = image_padded_grid.scaled_array_from_array_1d(g1_blurred_image_1d)
    #
    #     phase = ph.LensPlanePhase(lens_galaxies=[g0, g1])
    #     analysis = phase.make_analysis(image_)
    #     instance = phase.constant
    #     unmasked_tracer = analysis.unmasked_tracer_for_instance(instance)
    #     unmasked_model_images = analysis.unmasked_model_images_of_galaxies_for_tracer(unmasked_tracer)
    #
    #     assert g0_blurred_image == pytest.approx(unmasked_model_images[0], 1e-4)
    #     assert g1_blurred_image == pytest.approx(unmasked_model_images[1], 1e-4)

    def test__phase_can_receive_list_of_galaxy_models(self):
        phase = ph.LensPlanePhase(lens_galaxies=[gm.GalaxyModel(sersic=lp.EllipticalSersic,
                                                                sis=mp.SphericalIsothermal,
                                                                variable_redshift=True),
                                                 gm.GalaxyModel(sis=mp.SphericalIsothermal,
                                                                variable_redshift=True)],
                                  optimizer_class=non_linear.MultiNest, phase_name='test_phase')

        instance = phase.optimizer.variable.instance_from_physical_vector(
            [0.2, 0.21, 0.22, 0.23, 0.24, 0.25, 0.8, 0.1, 0.2, 0.3,
             0.4, 0.9, 0.5, 0.7, 0.8])

        assert instance.lens_galaxies[0].sersic.centre[0] == 0.2
        assert instance.lens_galaxies[0].sis.centre[0] == 0.1
        assert instance.lens_galaxies[0].sis.centre[1] == 0.2
        assert instance.lens_galaxies[0].sis.einstein_radius == 0.3
        assert instance.lens_galaxies[0].redshift == 0.4
        assert instance.lens_galaxies[1].sis.centre[0] == 0.9
        assert instance.lens_galaxies[1].sis.centre[1] == 0.5
        assert instance.lens_galaxies[1].sis.einstein_radius == 0.7
        assert instance.lens_galaxies[1].redshift == 0.8

        class LensPlanePhase2(ph.LensPlanePhase):
            # noinspection PyUnusedLocal
            def pass_models(self, previous_results):
                self.lens_galaxies[0].sis.einstein_radius = prior.Constant(10.0)

        phase = LensPlanePhase2(lens_galaxies=[gm.GalaxyModel(sersic=lp.EllipticalSersic,
                                                              sis=mp.SphericalIsothermal,
                                                              variable_redshift=True),
                                               gm.GalaxyModel(sis=mp.SphericalIsothermal,
                                                              variable_redshift=True)],
                                optimizer_class=non_linear.MultiNest, phase_name='test_phase')

        # noinspection PyTypeChecker
        phase.pass_models(None)

        instance = phase.optimizer.variable.instance_from_physical_vector(
            [0.01, 0.02, 0.23, 0.04, 0.05, 0.06, 0.87, 0.1, 0.2,
             0.4, 0.5, 0.5, 0.7, 0.8])
        instance += phase.optimizer.constant

        assert instance.lens_galaxies[0].sersic.centre[0] == 0.01
        assert instance.lens_galaxies[0].sis.centre[0] == 0.1
        assert instance.lens_galaxies[0].sis.centre[1] == 0.2
        assert instance.lens_galaxies[0].sis.einstein_radius == 10.0
        assert instance.lens_galaxies[0].redshift == 0.4
        assert instance.lens_galaxies[1].sis.centre[0] == 0.5
        assert instance.lens_galaxies[1].sis.centre[1] == 0.5
        assert instance.lens_galaxies[1].sis.einstein_radius == 0.7
        assert instance.lens_galaxies[1].redshift == 0.8


# class TestPixelizedPhase(object):
#     def test_constructor(self):
#         phase = ph.PixelizedSourceLensAndPhase()
#         assert isinstance(phase.source_galaxies, gm.GalaxyModel)
#         assert phase.lens_galaxies is None


# class TestAnalysis(object):
#     def test_model_image(self, results_collection, lens_data):
#         lens = ph.LensPlanePhase.Analysis(results_collection, lens_data, "analysis_path")
#         assert (results_collection[0].model_image == lens.last_results.model_image).all()


class TestResult(object):

    # def test_hyper_galaxy_and_model_images(self):
    #
    #     lens = MockAnalysis(number_galaxies=2, value=1.0)
    #
    # result = ph.LensSourcePlanePhase.Result(constant=mm.ModelInstance(), likelihood=1,
    # variable=mm.ModelMapper(), lens=lens) assert (result.image_plane_source_images[0] == np.array([
    # 1.0])).all() assert (result.image_plane_source_images[1] == np.array([1.0])).all() assert (
    # result.image_ == np.array([2.0])).all()

    def test_results(self):
        results = ph.ResultsCollection([1, 2, 3])
        assert results == [1, 2, 3]
        assert results.last == 3
        assert results.first == 1

    def test__results_of_phase_are_available_as_properties(self, ccd_data):
        clean_images()

        phase = ph.LensPlanePhase(optimizer_class=NLO,
                                  lens_galaxies=[g.Galaxy(light=lp.EllipticalSersic(intensity=1.0))],
                                  phase_name='test_phase')

        result = phase.run(data=ccd_data)

        assert hasattr(result, "most_likely_tracer")
        assert hasattr(result, "most_likely_padded_tracer")
        assert hasattr(result, "most_likely_fit")
        assert hasattr(result, "unmasked_model_image")
        assert hasattr(result, "unmasked_model_image_of_planes")
        assert hasattr(result, "unmasked_model_image_of_planes_and_galaxies")

    def test__fit_figure_of_merit__matches_correct_fit_given_galaxy_profiles(self, ccd_data):

        lens_galaxy = g.Galaxy(light=lp.EllipticalSersic(intensity=0.1))
        source_galaxy = g.Galaxy(pixelization=pix.Rectangular(shape=(4, 4)),
                                 regularization=reg.Constant(coefficients=(1.0,)))

        phase = ph.LensPlanePhase(lens_galaxies=[lens_galaxy], mask_function=ph.default_mask_function,
                                  cosmology=cosmo.FLRW, phase_name='test_phase')
        analysis = phase.make_analysis(data=ccd_data)
        instance = phase.constant
        fit_figure_of_merit = analysis.fit(instance=instance)

        mask = phase.mask_function(image=ccd_data.image)
        lens_data = li.LensData(ccd_data=ccd_data, mask=mask)
        tracer = analysis.tracer_for_instance(instance=instance)
        fit = lens_fit.LensProfileFit(lens_data=lens_data, tracer=tracer)

        assert fit.likelihood == fit_figure_of_merit

        phase = ph.LensSourcePlanePhase(lens_galaxies=[lens_galaxy], source_galaxies=[source_galaxy],
                                        mask_function=ph.default_mask_function, cosmology=cosmo.FLRW,
                                        phase_name='test_phase')
        analysis = phase.make_analysis(data=ccd_data)
        instance = phase.constant
        fit_figure_of_merit = analysis.fit(instance=instance)

        mask = phase.mask_function(image=ccd_data.image)
        lens_data = li.LensData(ccd_data=ccd_data, mask=mask)
        tracer = analysis.tracer_for_instance(instance=instance)
        fit = lens_fit.LensProfileInversionFit(lens_data=lens_data, tracer=tracer)

        assert fit.evidence == fit_figure_of_merit
