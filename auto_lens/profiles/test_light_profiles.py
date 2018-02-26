from __future__ import division, print_function

import pytest
from profiles import light_profiles
from profiles import geometry_profiles
import math
import numpy as np

# TODO : Combined light profile for intensity integral

@pytest.fixture(name='circular')
def circular_sersic():
    return light_profiles.SersicLightProfile(axis_ratio=1.0, phi=0.0, intensity=1.0, effective_radius=0.6,
                                             sersic_index=4.0)


@pytest.fixture(name='elliptical')
def elliptical_sersic():
    return light_profiles.SersicLightProfile(axis_ratio=0.5, phi=0.0, intensity=1.0, effective_radius=0.6,
                                             sersic_index=4.0)


@pytest.fixture(name='vertical')
def vertical_sersic():
    return light_profiles.SersicLightProfile(axis_ratio=0.5, phi=90.0, intensity=1.0, effective_radius=0.6,
                                             sersic_index=4.0)


@pytest.fixture(name='dev_vaucouleurs')
def dev_vaucouleurs_profile():
    return light_profiles.DevVaucouleursLightProfile(axis_ratio=0.6, phi=10.0, intensity=2.0, effective_radius=0.9,
                                                     centre=(0.0, 0.1))


@pytest.fixture(name="exponential")
def exponential_profile():
    return light_profiles.ExponentialLightProfile(axis_ratio=0.5, phi=45.0, intensity=3.0, effective_radius=0.2,
                                                  centre=(1, -1))


@pytest.fixture(name="core")
def core_profile():
    return light_profiles.CoreSersicLightProfile(axis_ratio=0.5, phi=0.0, intensity=1.0,
                                                 effective_radius=5.0, sersic_index=4.0, radius_break=0.01,
                                                 intensity_break=0.1, gamma=1.0, alpha=1.0)


class TestSetupProfiles(object):
    def test__setup_sersic(self, circular):
        assert circular.x_cen == 0.0
        assert circular.y_cen == 0.0
        assert circular.axis_ratio == 1.0
        assert circular.phi == 0.0
        assert circular.intensity == 1.0
        assert circular.effective_radius == 0.6
        assert circular.sersic_index == 4.0
        assert circular.sersic_constant == pytest.approx(7.66925, 1e-3)
        assert circular.elliptical_effective_radius == 0.6

    def test__setup_exponential(self, exponential):
        assert exponential.x_cen == 1.0
        assert exponential.y_cen == -1.0
        assert exponential.axis_ratio == 0.5
        assert exponential.phi == 45.0
        assert exponential.intensity == 3.0
        assert exponential.effective_radius == 0.2
        assert exponential.sersic_index == 1.0
        assert exponential.sersic_constant == pytest.approx(1.678378, 1e-3)
        assert exponential.elliptical_effective_radius == 0.2 / math.sqrt(0.5)

    def test__setup_dev_vaucouleurs(self, dev_vaucouleurs):
        assert dev_vaucouleurs.x_cen == 0.0
        assert dev_vaucouleurs.y_cen == 0.1
        assert dev_vaucouleurs.axis_ratio == 0.6
        assert dev_vaucouleurs.phi == 10.0
        assert dev_vaucouleurs.intensity == 2.0
        assert dev_vaucouleurs.effective_radius == 0.9
        assert dev_vaucouleurs.sersic_index == 4.0
        assert dev_vaucouleurs.sersic_constant == pytest.approx(7.66925, 1e-3)
        assert dev_vaucouleurs.elliptical_effective_radius == 0.9 / math.sqrt(0.6)

    def test__setup_core_sersic(self, core):
        assert core.x_cen == 0.0
        assert core.y_cen == 0.0
        assert core.axis_ratio == 0.5
        assert core.phi == 0.0
        assert core.intensity == 1.0
        assert core.effective_radius == 5.0
        assert core.sersic_index == 4.0
        assert core.sersic_constant == pytest.approx(7.66925, 1e-3)
        assert core.radius_break == 0.01
        assert core.intensity_break == 0.1
        assert core.gamma == 1.0
        assert core.alpha == 1.0
        assert core.elliptical_effective_radius == 5.0 / math.sqrt(0.5)


class TestLuminosityIntegral(object):

    class TestWithinCircle(object):

        def test__spherical_exponential__compare_to_analytic(self):

            import math
            import scipy.special

            sersic = light_profiles.SersicLightProfile(axis_ratio=1.0, phi=0.0, intensity=3.0, effective_radius=2.0,
                                                       sersic_index=1.0)

            integral_radius = 5.5

            # Use gamma functioon for analytic computation of the intensity within a radius=0.5

            x = sersic.sersic_constant * (integral_radius / sersic.effective_radius) ** (1.0 / sersic.sersic_index)

            intensity_analytic = sersic.intensity * sersic.effective_radius ** 2 * 2 * math.pi * sersic.sersic_index * \
                                 (math.e ** sersic.sersic_constant / (
                                 sersic.sersic_constant ** (2 * sersic.sersic_index))) * \
                                 scipy.special.gamma(2 * sersic.sersic_index) * scipy.special.gammainc(
                2 * sersic.sersic_index, x)

            intensity_integral = sersic.luminosity_within_circle(radius=integral_radius)

            assert intensity_analytic == pytest.approx(intensity_integral, 1e-3)

        def test__spherical_sersic_index_2__compare_to_analytic(self):

            import math
            import scipy.special

            sersic = light_profiles.SersicLightProfile(axis_ratio=1.0, phi=0.0, intensity=3.0, effective_radius=2.0,
                                                       sersic_index=2.0)

            integral_radius = 0.5

            # Use gamma functioon for analytic computation of the intensity within a radius=0.5

            x = sersic.sersic_constant * ((integral_radius / sersic.effective_radius) ** (1.0 / sersic.sersic_index))

            intensity_analytic = sersic.intensity * sersic.effective_radius ** 2 * 2 * math.pi * sersic.sersic_index * \
                                 ((math.e ** sersic.sersic_constant) / (
                                 sersic.sersic_constant ** (2 * sersic.sersic_index))) * \
                                 scipy.special.gamma(2 * sersic.sersic_index) * scipy.special.gammainc(
                2 * sersic.sersic_index, x)

            intensity_integral = sersic.luminosity_within_circle(radius=0.5)

            assert intensity_analytic == pytest.approx(intensity_integral, 1e-3)

        def test__spherical_dev_vaucouleurs__compare_to_analytic(self):

            import math
            import scipy.special

            sersic = light_profiles.SersicLightProfile(axis_ratio=1.0, phi=0.0, intensity=3.0, effective_radius=2.0,
                                                       sersic_index=4.0)

            integral_radius = 0.5

            # Use gamma functioon for analytic computation of the intensity within a radius=0.5

            x = sersic.sersic_constant * ((integral_radius / sersic.effective_radius) ** (1.0 / sersic.sersic_index))

            intensity_analytic = sersic.intensity * sersic.effective_radius ** 2 * 2 * math.pi * sersic.sersic_index * \
                                 ((math.e ** sersic.sersic_constant) / (
                                 sersic.sersic_constant ** (2 * sersic.sersic_index))) * \
                                 scipy.special.gamma(2 * sersic.sersic_index) * scipy.special.gammainc(
                2 * sersic.sersic_index, x)

            intensity_integral = sersic.luminosity_within_circle(radius=0.5)

            assert intensity_analytic == pytest.approx(intensity_integral, 1e-3)

        def test__spherical_exponential__compare_to_grid(self):

            sersic = light_profiles.SersicLightProfile(axis_ratio=1.0, phi=0.0, intensity=3.0, effective_radius=2.0,
                                                       sersic_index=1.0)

            import numpy as np

            integral_radius = 1.0
            luminosity_tot = 0.0

            xs = np.linspace(-1.5, 1.5, 40)
            ys = np.linspace(-1.5, 1.5, 40)

            edge = xs[1] - xs[0]
            area = edge ** 2

            for x in xs:
                for y in ys:

                    eta = math.sqrt(x ** 2 + y ** 2)

                    if eta < integral_radius:
                        luminosity_tot += sersic.intensity_at_radius(eta) * area

            intensity_integral = sersic.luminosity_within_circle(radius=integral_radius)

            assert luminosity_tot == pytest.approx(intensity_integral, 0.02)

        def test__spherical_sersic_2__compare_to_grid(self):

            sersic = light_profiles.SersicLightProfile(axis_ratio=1.0, phi=0.0, intensity=3.0, effective_radius=2.0,
                                                       sersic_index=2.0)

            import numpy as np

            integral_radius = 1.0
            luminosity_tot = 0.0

            xs = np.linspace(-1.5, 1.5, 40)
            ys = np.linspace(-1.5, 1.5, 40)

            edge = xs[1] - xs[0]
            area = edge ** 2

            for x in xs:
                for y in ys:

                    eta = math.sqrt(x ** 2 + y ** 2)
                    if eta < integral_radius:
                        luminosity_tot += sersic.intensity_at_radius(eta) * area

            intensity_integral = sersic.luminosity_within_circle(radius=integral_radius)

            assert luminosity_tot == pytest.approx(intensity_integral, 0.02)

        def test__spherical_dev_vaucauleurs__compare_to_grid(self):

            sersic = light_profiles.SersicLightProfile(axis_ratio=1.0, phi=0.0, intensity=3.0, effective_radius=2.0,
                                                       sersic_index=4.0)

            import numpy as np

            integral_radius = 1.0
            luminosity_tot = 0.0

            xs = np.linspace(-1.5, 1.5, 40)
            ys = np.linspace(-1.5, 1.5, 40)

            edge = xs[1] - xs[0]
            area = edge ** 2

            for x in xs:
                for y in ys:

                    eta = math.sqrt(x ** 2 + y ** 2)
                    if eta < integral_radius:
                        luminosity_tot += sersic.intensity_at_radius(eta) * area

            intensity_integral = sersic.luminosity_within_circle(radius=integral_radius)

            assert luminosity_tot == pytest.approx(intensity_integral, 0.02)

        def test__elliptical_exponential__compare_to_grid(self):

            sersic = light_profiles.SersicLightProfile(axis_ratio=0.5, phi=0.0, intensity=3.0, effective_radius=2.0,
                                                       sersic_index=1.0)

            integral_radius = 0.5
            luminosity_tot = 0.0

            xs = np.linspace(-1.0, 1.0, 40)
            ys = np.linspace(-1.0, 1.0, 40)

            edge = xs[1] - xs[0]
            area = edge ** 2

            for x in xs:
                for y in ys:

                    eta = math.sqrt(x ** 2 + y ** 2)
                    if eta < integral_radius:
                        luminosity_tot += sersic.intensity_at_radius(eta) * area

            intensity_integral = sersic.luminosity_within_circle(radius=integral_radius)

            assert luminosity_tot == pytest.approx(intensity_integral, 0.02)

        def test__elliptical_sersic_2__compare_to_grid(self):

            sersic = light_profiles.SersicLightProfile(axis_ratio=0.3, phi=0.0, intensity=3.0, effective_radius=2.0,
                                                       sersic_index=2.0)

            integral_radius = 0.5
            luminosity_tot = 0.0

            xs = np.linspace(-1.8, 1.8, 50)
            ys = np.linspace(-1.8, 1.8, 50)

            edge = xs[1] - xs[0]
            area = edge ** 2

            for x in xs:
                for y in ys:

                    eta = math.sqrt(x ** 2 + y ** 2)
                    if eta < integral_radius:
                        luminosity_tot += sersic.intensity_at_radius(eta) * area

            intensity_integral = sersic.luminosity_within_circle(radius=integral_radius)

            assert luminosity_tot == pytest.approx(intensity_integral, 0.02)

    class TestWithinEllipse(object):

        def test__elliptical_exponential__compare_to_grid(self):

            sersic = light_profiles.SersicLightProfile(axis_ratio=0.5, phi=0.0, intensity=3.0, effective_radius=2.0,
                                                       sersic_index=1.0)

            integral_radius = 0.5
            luminosity_tot = 0.0

            xs = np.linspace(-1.0, 1.0, 40)
            ys = np.linspace(-1.0, 1.0, 40)

            edge = xs[1] - xs[0]
            area = edge ** 2

            for x in xs:
                for y in ys:

                    eta = sersic.coordinates_to_elliptical_radius((x, y))

                    if eta < integral_radius:
                        luminosity_tot += sersic.intensity_at_radius(eta) * area

            intensity_integral = sersic.luminosity_within_ellipse(major_axis=integral_radius)

            assert luminosity_tot == pytest.approx(intensity_integral, 0.02)

        def test__elliptical_sersic_2__compare_to_grid(self):

            sersic = light_profiles.SersicLightProfile(axis_ratio=0.5, phi=90.0, intensity=3.0, effective_radius=2.0,
                                                       sersic_index=2.0)

            integral_radius = 0.5
            luminosity_tot = 0.0

            xs = np.linspace(-1.8, 1.8, 80)
            ys = np.linspace(-1.8, 1.8, 80)

            edge = xs[1] - xs[0]
            area = edge ** 2

            for x in xs:
                for y in ys:

                    eta = sersic.coordinates_to_elliptical_radius((x, y))

                    if eta < integral_radius:
                        luminosity_tot += sersic.intensity_at_radius(eta) * area

            intensity_integral = sersic.luminosity_within_ellipse(major_axis=integral_radius)

            assert luminosity_tot == pytest.approx(intensity_integral, 0.02)

        def test__elliptical_dev_vaucauleurs__compare_to_grid(self):

            sersic = light_profiles.SersicLightProfile(axis_ratio=0.7, phi=30.0, intensity=3.0, effective_radius=2.0,
                                                       sersic_index=4.0)

            integral_radius = 0.5
            luminosity_tot = 0.0

            xs = np.linspace(-1.5, 1.5, 50)
            ys = np.linspace(-1.5, 1.5, 50)

            edge = xs[1] - xs[0]
            area = edge ** 2

            for x in xs:
                for y in ys:

                    eta = sersic.coordinates_to_elliptical_radius((x, y))

                    if eta < integral_radius:
                        luminosity_tot += sersic.intensity_at_radius(eta) * area

            intensity_integral = sersic.luminosity_within_ellipse(major_axis=integral_radius)

            assert luminosity_tot == pytest.approx(intensity_integral, 0.01)

    class TestComblinedLightProfile(object):

        def test__one_integral_same_as_individual_integral_circle(self):

            sersic = light_profiles.SersicLightProfile(axis_ratio=1.0, phi=0.0, intensity=3.0, effective_radius=2.0,
                                                       sersic_index=1.0)

            integral_radius = 5.5

            intensity_integral = sersic.luminosity_within_circle(radius=integral_radius)

            sersic_combined = light_profiles.CombinedLightProfile(light_profiles.SersicLightProfile(axis_ratio=1.0,
                                                                   phi=0.0, intensity=3.0, effective_radius=2.0,
                                                                   sersic_index=1.0))

            combined_intensity_integral = sersic_combined.luminosity_within_circle(radius=integral_radius)

            assert intensity_integral == combined_intensity_integral

        def test__two_integrals_sum_to_combined_profile_circle(self):

            sersic_1 = light_profiles.SersicLightProfile(axis_ratio=1.0, phi=0.0, intensity=3.0, effective_radius=2.0,
                                                       sersic_index=1.0)

            sersic_2 = light_profiles.SersicLightProfile(axis_ratio=0.5, phi=0.0, intensity=7.0, effective_radius=3.0,
                                                       sersic_index=2.0)

            integral_radius = 5.5

            intensity_integral = sersic_1.luminosity_within_circle(radius=integral_radius)
            intensity_integral += sersic_2.luminosity_within_circle(radius=integral_radius)

            sersic_combined = light_profiles.CombinedLightProfile(
                              light_profiles.SersicLightProfile(axis_ratio=1.0, phi=0.0, intensity=3.0,
                                                                effective_radius=2.0, sersic_index=1.0),
                              light_profiles.SersicLightProfile(axis_ratio=0.5, phi=0.0, intensity=7.0,
                                                                effective_radius=3.0, sersic_index=2.0))

            combined_intensity_integral = sersic_combined.luminosity_within_circle(radius=integral_radius)

            assert intensity_integral == combined_intensity_integral

        def test__three_integrals_sum_to_combined_profile_circle(self):

            sersic_1 = light_profiles.SersicLightProfile(axis_ratio=1.0, phi=0.0, intensity=3.0, effective_radius=2.0,
                                                       sersic_index=1.0)

            sersic_2 = light_profiles.SersicLightProfile(axis_ratio=0.5, phi=0.0, intensity=7.0, effective_radius=3.0,
                                                       sersic_index=2.0)

            sersic_3 = light_profiles.SersicLightProfile(axis_ratio=0.8, phi=50.0, intensity=2.0, effective_radius=3.0,
                                                       sersic_index=2.0)

            integral_radius = 5.5

            intensity_integral = sersic_1.luminosity_within_circle(radius=integral_radius)
            intensity_integral += sersic_2.luminosity_within_circle(radius=integral_radius)
            intensity_integral += sersic_3.luminosity_within_circle(radius=integral_radius)

            sersic_combined = light_profiles.CombinedLightProfile(
                              light_profiles.SersicLightProfile(axis_ratio=1.0, phi=0.0, intensity=3.0,
                                                                effective_radius=2.0, sersic_index=1.0),
                              light_profiles.SersicLightProfile(axis_ratio=0.5, phi=0.0, intensity=7.0,
                                                                effective_radius=3.0, sersic_index=2.0),
                              light_profiles.SersicLightProfile(axis_ratio=0.8, phi=50.0, intensity=2.0,
                                                                effective_radius=3.0, sersic_index=2.0))

            combined_intensity_integral = sersic_combined.luminosity_within_circle(radius=integral_radius)

            assert intensity_integral == combined_intensity_integral

        def test__three_integrals_individual_profiles_identical_circle(self):

            sersic_1 = light_profiles.SersicLightProfile(axis_ratio=1.0, phi=0.0, intensity=3.0, effective_radius=2.0,
                                                       sersic_index=1.0)

            sersic_2 = light_profiles.SersicLightProfile(axis_ratio=0.5, phi=0.0, intensity=7.0, effective_radius=3.0,
                                                       sersic_index=2.0)

            sersic_3 = light_profiles.SersicLightProfile(axis_ratio=0.8, phi=50.0, intensity=2.0, effective_radius=3.0,
                                                       sersic_index=2.0)

            integral_radius = 5.5

            intensity_integral_1 = sersic_1.luminosity_within_circle(radius=integral_radius)
            intensity_integral_2 = sersic_2.luminosity_within_circle(radius=integral_radius)
            intensity_integral_3 = sersic_3.luminosity_within_circle(radius=integral_radius)

            sersic_combined = light_profiles.CombinedLightProfile(
                              light_profiles.SersicLightProfile(axis_ratio=1.0, phi=0.0, intensity=3.0,
                                                                effective_radius=2.0, sersic_index=1.0),
                              light_profiles.SersicLightProfile(axis_ratio=0.5, phi=0.0, intensity=7.0,
                                                                effective_radius=3.0, sersic_index=2.0),
                              light_profiles.SersicLightProfile(axis_ratio=0.8, phi=50.0, intensity=2.0,
                                                                effective_radius=3.0, sersic_index=2.0))

            combined_intensity_integral = sersic_combined.luminosity_within_circle_individual(radius=integral_radius)

            assert intensity_integral_1 == combined_intensity_integral[0]
            assert intensity_integral_2 == combined_intensity_integral[1]
            assert intensity_integral_3 == combined_intensity_integral[2]

        def test__one_integral_same_as_individual_integral_ellipse(self):

            sersic = light_profiles.SersicLightProfile(axis_ratio=0.5, phi=0.0, intensity=3.0, effective_radius=2.0,
                                                       sersic_index=1.0)

            integral_radius = 0.5

            intensity_integral = sersic.luminosity_within_ellipse(major_axis=integral_radius)

            sersic_combined = light_profiles.CombinedLightProfile(light_profiles.SersicLightProfile(axis_ratio=0.5,
                                                                   phi=0.0, intensity=3.0, effective_radius=2.0,
                                                                   sersic_index=1.0))

            combined_intensity_integral = sersic_combined.luminosity_within_ellipse(major_axis=integral_radius)

            assert intensity_integral == combined_intensity_integral

        def test__two_integrals_sum_to_combined_profile_ellipse(self):
            sersic_1 = light_profiles.SersicLightProfile(axis_ratio=1.0, phi=0.0, intensity=3.0, effective_radius=2.0,
                                                         sersic_index=1.0)

            sersic_2 = light_profiles.SersicLightProfile(axis_ratio=0.5, phi=0.0, intensity=7.0, effective_radius=3.0,
                                                         sersic_index=2.0)

            integral_radius = 5.5

            intensity_integral = sersic_1.luminosity_within_ellipse(major_axis=integral_radius)
            intensity_integral += sersic_2.luminosity_within_ellipse(major_axis=integral_radius)

            sersic_combined = light_profiles.CombinedLightProfile(
                light_profiles.SersicLightProfile(axis_ratio=1.0, phi=0.0, intensity=3.0,
                                                  effective_radius=2.0, sersic_index=1.0),
                light_profiles.SersicLightProfile(axis_ratio=0.5, phi=0.0, intensity=7.0,
                                                  effective_radius=3.0, sersic_index=2.0))

            combined_intensity_integral = sersic_combined.luminosity_within_ellipse(major_axis=integral_radius)

            assert intensity_integral == combined_intensity_integral

        def test__three_integrals_sum_to_combined_profile_ellipse(self):

            sersic_1 = light_profiles.SersicLightProfile(axis_ratio=1.0, phi=0.0, intensity=3.0, effective_radius=2.0,
                                                       sersic_index=1.0)

            sersic_2 = light_profiles.SersicLightProfile(axis_ratio=0.5, phi=0.0, intensity=7.0, effective_radius=3.0,
                                                       sersic_index=2.0)

            sersic_3 = light_profiles.SersicLightProfile(axis_ratio=0.8, phi=50.0, intensity=2.0, effective_radius=3.0,
                                                       sersic_index=2.0)

            integral_radius = 5.5

            intensity_integral = sersic_1.luminosity_within_ellipse(major_axis=integral_radius)
            intensity_integral += sersic_2.luminosity_within_ellipse(major_axis=integral_radius)
            intensity_integral += sersic_3.luminosity_within_ellipse(major_axis=integral_radius)

            sersic_combined = light_profiles.CombinedLightProfile(
                              light_profiles.SersicLightProfile(axis_ratio=1.0, phi=0.0, intensity=3.0,
                                                                effective_radius=2.0, sersic_index=1.0),
                              light_profiles.SersicLightProfile(axis_ratio=0.5, phi=0.0, intensity=7.0,
                                                                effective_radius=3.0, sersic_index=2.0),
                              light_profiles.SersicLightProfile(axis_ratio=0.8, phi=50.0, intensity=2.0,
                                                                effective_radius=3.0, sersic_index=2.0))

            combined_intensity_integral = sersic_combined.luminosity_within_ellipse(major_axis=integral_radius)

            assert intensity_integral == combined_intensity_integral

        def test__three_integrals_individual_profiles_identical_ellipsse(self):

            sersic_1 = light_profiles.SersicLightProfile(axis_ratio=1.0, phi=0.0, intensity=3.0, effective_radius=2.0,
                                                       sersic_index=1.0)

            sersic_2 = light_profiles.SersicLightProfile(axis_ratio=0.5, phi=0.0, intensity=7.0, effective_radius=3.0,
                                                       sersic_index=2.0)

            sersic_3 = light_profiles.SersicLightProfile(axis_ratio=0.8, phi=50.0, intensity=2.0, effective_radius=3.0,
                                                       sersic_index=2.0)

            integral_radius = 5.5

            intensity_integral_1 = sersic_1.luminosity_within_ellipse(major_axis=integral_radius)
            intensity_integral_2 = sersic_2.luminosity_within_ellipse(major_axis=integral_radius)
            intensity_integral_3 = sersic_3.luminosity_within_ellipse(major_axis=integral_radius)

            sersic_combined = light_profiles.CombinedLightProfile(
                              light_profiles.SersicLightProfile(axis_ratio=1.0, phi=0.0, intensity=3.0,
                                                                effective_radius=2.0, sersic_index=1.0),
                              light_profiles.SersicLightProfile(axis_ratio=0.5, phi=0.0, intensity=7.0,
                                                                effective_radius=3.0, sersic_index=2.0),
                              light_profiles.SersicLightProfile(axis_ratio=0.8, phi=50.0, intensity=2.0,
                                                                effective_radius=3.0, sersic_index=2.0))

            combined_intensity_integral = sersic_combined.luminosity_within_ellipse_individual(major_axis=integral_radius)

            assert intensity_integral_1 == combined_intensity_integral[0]
            assert intensity_integral_2 == combined_intensity_integral[1]
            assert intensity_integral_3 == combined_intensity_integral[2]


class TestIntensityValues(object):
    def test__intensity_at_radius__correct_value(self, circular):
        intensity = circular.intensity_at_radius(radius=1.0)
        assert intensity == pytest.approx(0.351797, 1e-3)

    def test__intensity_at_radius_2__correct_value(self):
        sersic = light_profiles.SersicLightProfile(axis_ratio=1.0, phi=0.0, intensity=3.0, effective_radius=2.0,
                                                   sersic_index=2.0)
        intensity = sersic.intensity_at_radius(
            radius=1.5)  # 3.0 * exp(-3.67206544592 * (1,5/2.0) ** (1.0 / 2.0)) - 1) = 0.351797
        assert intensity == pytest.approx(4.90657319276, 1e-3)

    def test__intensity_at_coordinates__different_axis_ratio(self):
        sersic = light_profiles.SersicLightProfile(axis_ratio=0.5, phi=0.0, intensity=3.0, effective_radius=2.0,
                                                   sersic_index=2.0)

        intensity = sersic.intensity_at_coordinates(coordinates=(0, 1))

        assert intensity == pytest.approx(5.38066670129, 1e-3)

    def test__intensity_at_coordinates__different_rotate_phi_90_same_result(self):
        sersic = light_profiles.SersicLightProfile(axis_ratio=0.5, phi=0.0, intensity=3.0, effective_radius=2.0,
                                                   sersic_index=2.0)

        intensity_1 = sersic.intensity_at_coordinates(coordinates=(0, 1))

        sersic = light_profiles.SersicLightProfile(axis_ratio=0.5, phi=90.0, intensity=3.0, effective_radius=2.0,
                                                   sersic_index=2.0)

        intensity_2 = sersic.intensity_at_coordinates(coordinates=(1, 0))

        assert intensity_1 == intensity_2

    def test__core_sersic_light_profile(self, core):
        assert core.intensity_at_radius(0.01) == 0.1


class TestCoordinates(object):
    def test__coordinates_to_eccentric_radius(self, elliptical):
        assert elliptical.coordinates_to_eccentric_radius((1, 1)) == pytest.approx(
            elliptical.coordinates_to_eccentric_radius(
                (-1, -1)), 1e-10)

    def test__intensity_at_coordinates(self, elliptical):
        assert elliptical.intensity_at_coordinates((1, 1)) == pytest.approx(
            elliptical.intensity_at_coordinates((-1, -1)), 1e-10)


class TestCombinedProfiles(object):
    def test__summation(self, circular):
        combined = light_profiles.CombinedLightProfile(circular, circular)
        assert combined.intensity_at_coordinates((0, 0)) == 2 * circular.intensity_at_coordinates((0, 0))

    def test_1d_symmetry(self):
        sersic1 = light_profiles.SersicLightProfile(axis_ratio=1.0, phi=0.0, intensity=1.0, effective_radius=0.6,
                                                    sersic_index=4.0)

        sersic2 = light_profiles.SersicLightProfile(axis_ratio=1.0, phi=0.0, intensity=1.0, effective_radius=0.6,
                                                    sersic_index=4.0, centre=(100, 0))

        combined = light_profiles.CombinedLightProfile(sersic1, sersic2)
        assert combined.intensity_at_coordinates((0, 0)) == combined.intensity_at_coordinates((100, 0))
        assert combined.intensity_at_coordinates((49, 0)) == combined.intensity_at_coordinates((51, 0))

    def test_2d_symmetry(self):
        sersic1 = light_profiles.SersicLightProfile(axis_ratio=1.0, phi=0.0, intensity=1.0, effective_radius=0.6,
                                                    sersic_index=4.0)

        sersic2 = light_profiles.SersicLightProfile(axis_ratio=1.0, phi=0.0, intensity=1.0, effective_radius=0.6,
                                                    sersic_index=4.0, centre=(100, 0))
        sersic3 = light_profiles.SersicLightProfile(axis_ratio=1.0, phi=0.0, intensity=1.0, effective_radius=0.6,
                                                    sersic_index=4.0, centre=(0, 100))

        sersic4 = light_profiles.SersicLightProfile(axis_ratio=1.0, phi=0.0, intensity=1.0, effective_radius=0.6,
                                                    sersic_index=4.0, centre=(100, 100))

        combined = light_profiles.CombinedLightProfile(sersic1, sersic2, sersic3, sersic4)

        assert combined.intensity_at_coordinates((49, 0)) == pytest.approx(combined.intensity_at_coordinates((51, 0)),
                                                                           1e-5)
        assert combined.intensity_at_coordinates((0, 49)) == pytest.approx(combined.intensity_at_coordinates((0, 51)),
                                                                           1e-5)
        assert combined.intensity_at_coordinates((100, 49)) == pytest.approx(
            combined.intensity_at_coordinates((100, 51)), 1e-5)
        assert combined.intensity_at_coordinates((49, 49)) == pytest.approx(combined.intensity_at_coordinates((51, 51)),
                                                                            1e-5)


class TestArray(object):
    def test__simple_assumptions(self, circular):
        array = geometry_profiles.array_function(circular.intensity_at_coordinates)(x_min=0, x_max=101, y_min=0, y_max=101,
                                                                                    pixel_scale=1)
        assert array.shape == (101, 101)
        assert array[51][51] > array[51][52]
        assert array[51][51] > array[52][51]
        assert all(map(lambda i: i > 0, array[0]))

        array = geometry_profiles.array_function(circular.intensity_at_coordinates)(x_min=0, x_max=100, y_min=0, y_max=100,
                                                                                    pixel_scale=0.5)
        assert array.shape == (200, 200)

    def test__ellipticity(self, circular, elliptical, vertical):
        array = geometry_profiles.array_function(circular.intensity_at_coordinates)(x_min=0, x_max=101, y_min=0, y_max=101,
                                                                                    pixel_scale=1)
        assert array[60][0] == array[0][60]

        array = geometry_profiles.array_function(elliptical.intensity_at_coordinates)(x_min=0, x_max=100, y_min=0, y_max=100,
                                                                                      pixel_scale=1)

        assert array[60][51] > array[51][60]

        array = geometry_profiles.array_function(vertical.intensity_at_coordinates)(x_min=0, x_max=100, y_min=0, y_max=100,
                                                                                    pixel_scale=1)
        assert array[60][51] < array[51][60]

    # noinspection PyTypeChecker
    def test__flat_array(self, circular):
        array = geometry_profiles.array_function(circular.intensity_at_coordinates)(x_min=0, x_max=100, y_min=0, y_max=100,
                                                                                    pixel_scale=1)
        flat_array = geometry_profiles.array_function(circular.intensity_at_coordinates)(x_min=0, x_max=100, y_min=0, y_max=100,
                                                                                         pixel_scale=1).flatten()

        assert all(array[0] == flat_array[:100])
        assert all(array[1] == flat_array[100:200])

    def test_combined_array(self, circular):
        combined = light_profiles.CombinedLightProfile(circular, circular)

        assert all(map(lambda i: i == 2,
                       geometry_profiles.array_function(combined.intensity_at_coordinates)().flatten() / geometry_profiles.array_function(
                           circular.intensity_at_coordinates)().flatten()))

    def test_symmetric_profile(self, circular):
        circular.centre = (50, 50)
        array = geometry_profiles.array_function(circular.intensity_at_coordinates)(x_min=0, x_max=100, y_min=0, y_max=100,
                                                                                    pixel_scale=1.0)

        assert array[50][50] > array[50][51]
        assert array[50][50] > array[49][50]
        assert array[49][50] == array[50][51]
        assert array[50][51] == array[50][49]
        assert array[50][49] == array[51][50]

        array = geometry_profiles.array_function(circular.intensity_at_coordinates)(x_min=0, x_max=100, y_min=0, y_max=100,
                                                                                    pixel_scale=0.5)

        assert array[100][100] > array[100][101]
        assert array[100][100] > array[99][100]
        assert array[99][100] == array[100][101]
        assert array[100][101] == array[100][99]
        assert array[100][99] == array[101][100]

    def test_origin_symmetric_profile(self, circular):
        array = geometry_profiles.array_function(circular.intensity_at_coordinates)()

        assert circular.intensity_at_coordinates((-5, 0)) < circular.intensity_at_coordinates((0, 0))
        assert circular.intensity_at_coordinates((5, 0)) < circular.intensity_at_coordinates((0, 0))
        assert circular.intensity_at_coordinates((0, -5)) < circular.intensity_at_coordinates((0, 0))
        assert circular.intensity_at_coordinates((0, 5)) < circular.intensity_at_coordinates((0, 0))
        assert circular.intensity_at_coordinates((5, 5)) < circular.intensity_at_coordinates((0, 0))
        assert circular.intensity_at_coordinates((-5, -5)) < circular.intensity_at_coordinates((0, 0))

        assert array.shape == (100, 100)

        assert array[50][50] > array[50][51]
        assert array[50][50] > array[49][50]
        assert array[49][50] == pytest.approx(array[50][51], 1e-10)
        assert array[50][51] == pytest.approx(array[50][49], 1e-10)
        assert array[50][49] == pytest.approx(array[51][50], 1e-10)


class TestTransform(object):
    def test_exceptions(self, elliptical):
        with pytest.raises(geometry_profiles.CoordinatesException):
            elliptical.transform_to_reference_frame(geometry_profiles.TransformedCoordinates((0, 0)))

        with pytest.raises(geometry_profiles.CoordinatesException):
            elliptical.transform_from_reference_frame((0, 0))
