import os

from autofit import conf
from autofit.mapper import model_mapper as mm
from autofit.mapper import prior
from autofit.optimize import non_linear as nl
from autolens.data import ccd
from autolens.model.galaxy import galaxy, galaxy_model as gm
from autolens.model.profiles import light_profiles as lp
from autolens.pipeline import phase as ph
from test.integration import tools

dirpath = os.path.dirname(os.path.realpath(__file__))
conf.instance = conf.Config("{}/config".format(dirpath),
                            "{}/output/".format(dirpath))

dirpath = os.path.dirname(dirpath)
output_path = '{}/output'.format(dirpath)

test_name = "test"


class TestPhaseModelMapper(object):

    def test_pairing_works(self):
        test_name = 'pair_floats'

        tools.reset_paths(test_name, output_path)

        sersic = lp.EllipticalSersic(centre=(0.0, 0.0), axis_ratio=0.8, phi=90.0, intensity=1.0, effective_radius=1.3,
                                     sersic_index=3.0)

        lens_galaxy = galaxy.Galaxy(light_profile=sersic)

        tools.simulate_integration_image(test_name=test_name, pixel_scale=0.5, lens_galaxies=[lens_galaxy],
                                         source_galaxies=[], target_signal_to_noise=10.0)

        path = "{}/".format(
            os.path.dirname(os.path.realpath(__file__)))  # Setup path so we can output the simulated image.

        ccd_data = ccd.load_ccd_data_from_fits(image_path=path + '/data/' + test_name + '/image.fits',
                                               psf_path=path + '/data/' + test_name + '/psf.fits',
                                               noise_map_path=path + '/data/' + test_name + '/noise_map.fits',
                                               pixel_scale=0.1)

        class MMPhase(ph.LensPlanePhase):

            def pass_priors(self, previous_results):
                self.lens_galaxies.lens.sersic.intensity = self.lens_galaxies.lens.sersic.axis_ratio

        phase = MMPhase(lens_galaxies=dict(lens=gm.GalaxyModel(sersic=lp.EllipticalSersic)),
                        optimizer_class=nl.MultiNest, phase_name="{}/phase1".format(test_name))

        initial_total_priors = phase.variable.prior_count
        phase.make_analysis(data=ccd_data)

        assert phase.lens_galaxies[0].sersic.intensity == phase.lens_galaxies[0].sersic.axis_ratio
        assert initial_total_priors - 1 == phase.variable.prior_count
        assert len(phase.variable.flat_prior_model_tuples) == 1

        lines = list(
            filter(lambda line: "axis_ratio" in line or "intensity" in line, phase.variable.info.split("\n")))

        assert len(lines) == 2
        assert "lens_axis_ratio                                             UniformPrior, lower_limit = 0.2, " \
               "upper_limit = 1.0" in lines
        assert "lens_intensity                                              UniformPrior, lower_limit = 0.2, " \
               "upper_limit = 1.0" in lines

    def test_constants_work(self):
        name = "const_float"
        test_name = '/const_float'

        tools.reset_paths(test_name, output_path)

        sersic = lp.EllipticalSersic(centre=(0.0, 0.0), axis_ratio=0.8, phi=90.0, intensity=1.0, effective_radius=1.3,
                                     sersic_index=3.0)

        lens_galaxy = galaxy.Galaxy(light_profile=sersic)

        tools.simulate_integration_image(test_name=test_name, pixel_scale=0.5, lens_galaxies=[lens_galaxy],
                                         source_galaxies=[], target_signal_to_noise=10.0)
        path = "{}/".format(
            os.path.dirname(os.path.realpath(__file__)))  # Setup path so we can output the simulated image.

        ccd_data = ccd.load_ccd_data_from_fits(image_path=path + '/data/' + test_name + '/image.fits',
                                               psf_path=path + '/data/' + test_name + '/psf.fits',
                                               noise_map_path=path + '/data/' + test_name + '/noise_map.fits',
                                               pixel_scale=0.1)

        class MMPhase(ph.LensPlanePhase):

            def pass_priors(self, previous_results):
                self.lens_galaxies.lens.sersic.axis_ratio = 0.2
                self.lens_galaxies.lens.sersic.phi = 90.0
                self.lens_galaxies.lens.sersic.intensity = 1.0
                self.lens_galaxies.lens.sersic.effective_radius = 1.3
                self.lens_galaxies.lens.sersic.sersic_index = 3.0

        phase = MMPhase(lens_galaxies=dict(lens=gm.GalaxyModel(sersic=lp.EllipticalSersic)),
                        optimizer_class=nl.MultiNest, phase_name="{}/phase1".format(name))

        phase.optimizer.n_live_points = 20
        phase.optimizer.sampling_efficiency = 0.8

        phase.make_analysis(data=ccd_data)

        sersic = phase.variable.lens_galaxies[0].sersic

        assert isinstance(sersic, mm.PriorModel)

        assert isinstance(sersic.axis_ratio, prior.Constant)
        assert isinstance(sersic.phi, prior.Constant)
        assert isinstance(sersic.intensity, prior.Constant)
        assert isinstance(sersic.effective_radius, prior.Constant)
        assert isinstance(sersic.sersic_index, prior.Constant)
