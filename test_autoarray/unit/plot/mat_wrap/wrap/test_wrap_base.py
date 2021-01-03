import autoarray as aa
import autoarray.plot as aplt

from os import path

import matplotlib.pyplot as plt
import matplotlib.colors as colors
import shutil
import numpy as np

directory = path.dirname(path.realpath(__file__))


class TestUnits:
    def test__loads_values_from_config_if_not_manually_input(self):

        units = aplt.Units()

        assert units.use_scaled == True
        assert units.in_kpc == False
        assert units.conversion_factor == None

        units = aplt.Units(in_kpc=True, conversion_factor=2.0)

        assert units.use_scaled == True
        assert units.in_kpc == True
        assert units.conversion_factor == 2.0


class TestFigure:
    def test__loads_values_from_config_if_not_manually_input(self):

        figure = aplt.Figure()

        assert figure.config_dict_figure["figsize"] == (7, 7)
        assert figure.config_dict_imshow["aspect"] == "square"

        figure = aplt.Figure(aspect="auto")

        assert figure.config_dict_figure["figsize"] == (7, 7)
        assert figure.config_dict_imshow["aspect"] == "auto"

        figure = aplt.Figure()
        figure.for_subplot = True

        assert figure.config_dict_figure["figsize"] == None
        assert figure.config_dict_imshow["aspect"] == "square"

        figure = aplt.Figure(figsize=(6, 6))
        figure.for_subplot = True

        assert figure.config_dict_figure["figsize"] == (6, 6)
        assert figure.config_dict_imshow["aspect"] == "square"

    def test__aspect_from_shape_2d(self):

        figure = aplt.Figure(aspect="auto")

        aspect = figure.aspect_from_shape_2d(shape_2d=(2, 2))

        assert aspect == "auto"

        figure = aplt.Figure(aspect="square")

        aspect = figure.aspect_from_shape_2d(shape_2d=(2, 2))

        assert aspect == 1.0

        aspect = figure.aspect_from_shape_2d(shape_2d=(4, 2))

        assert aspect == 0.5

    def test__open_and_close__open_and_close_figures_correct(self):

        figure = aplt.Figure()

        figure.open()

        assert plt.fignum_exists(num=1) == True

        figure.close()

        assert plt.fignum_exists(num=1) == False


class TestCmap:
    def test__loads_values_from_config_if_not_manually_input(self):

        cmap = aplt.Cmap()

        assert cmap.config_dict["cmap"] == "jet"
        assert cmap.config_dict["norm"] == "linear"

        cmap = aplt.Cmap(cmap="cold")

        assert cmap.config_dict["cmap"] == "cold"
        assert cmap.config_dict["norm"] == "linear"

        cmap = aplt.Cmap()
        cmap.for_subplot = True

        assert cmap.config_dict["cmap"] == "jet"
        assert cmap.config_dict["norm"] == "linear"

        cmap = aplt.Cmap(cmap="cold")
        cmap.for_subplot = True

        assert cmap.config_dict["cmap"] == "cold"
        assert cmap.config_dict["norm"] == "linear"

    def test__norm_from_array__uses_input_vmin_and_max_if_input(self):

        cmap = aplt.Cmap(vmin=0.0, vmax=1.0, norm="linear")

        norm = cmap.norm_from_array(array=None)

        assert isinstance(norm, colors.Normalize)
        assert norm.vmin == 0.0
        assert norm.vmax == 1.0

        cmap = aplt.Cmap(vmin=0.0, vmax=1.0, norm="log")

        norm = cmap.norm_from_array(array=None)

        assert isinstance(norm, colors.LogNorm)
        assert norm.vmin == 1.0e-4  # Increased from 0.0 to ensure min isn't inf
        assert norm.vmax == 1.0

        cmap = aplt.Cmap(
            vmin=0.0, vmax=1.0, linthresh=2.0, linscale=3.0, norm="symmetric_log"
        )

        norm = cmap.norm_from_array(array=None)

        assert isinstance(norm, colors.SymLogNorm)
        assert norm.vmin == 0.0
        assert norm.vmax == 1.0
        assert norm.linthresh == 2.0

    def test__norm_from_array__uses_array_to_get_vmin_and_max_if_no_manual_input(self,):

        array = aa.Array.ones(shape_2d=(2, 2), pixel_scales=1.0)
        array[0] = 0.0

        cmap = aplt.Cmap(vmin=None, vmax=None, norm="linear")

        norm = cmap.norm_from_array(array=array)

        assert isinstance(norm, colors.Normalize)
        assert norm.vmin == 0.0
        assert norm.vmax == 1.0

        cmap = aplt.Cmap(vmin=None, vmax=None, norm="log")

        norm = cmap.norm_from_array(array=array)

        assert isinstance(norm, colors.LogNorm)
        assert norm.vmin == 1.0e-4  # Increased from 0.0 to ensure min isn't inf
        assert norm.vmax == 1.0

        cmap = aplt.Cmap(
            vmin=None, vmax=None, linthresh=2.0, linscale=3.0, norm="symmetric_log"
        )

        norm = cmap.norm_from_array(array=array)

        assert isinstance(norm, colors.SymLogNorm)
        assert norm.vmin == 0.0
        assert norm.vmax == 1.0
        assert norm.linthresh == 2.0


class TestColorbar:
    def test__loads_values_from_config_if_not_manually_input(self):

        colorbar = aplt.Colorbar()

        assert colorbar.config_dict["labelsize"] == 1
        assert colorbar.manual_tick_values == None
        assert colorbar.manual_tick_labels == None

        colorbar = aplt.Colorbar(
            labelsize=20, manual_tick_values=(1.0, 2.0), manual_tick_labels=(3.0, 4.0)
        )

        assert colorbar.config_dict["labelsize"] == 20
        assert colorbar.manual_tick_values == (1.0, 2.0)
        assert colorbar.manual_tick_labels == (3.0, 4.0)

        colorbar = aplt.Colorbar()
        colorbar.for_subplot = True

        assert colorbar.config_dict["labelsize"] == 1

        colorbar = aplt.Colorbar(labelsize=10)
        colorbar.for_subplot = True

        assert colorbar.config_dict["labelsize"] == 10

    def test__plot__works_for_reasonable_range_of_values(self):

        figure = aplt.Figure()

        figure.open()
        plt.imshow(np.ones((2, 2)))
        cb = aplt.Colorbar(ticksize=1, fraction=1.0, pad=2.0)
        cb.set()
        figure.close()

        figure.open()
        plt.imshow(np.ones((2, 2)))
        cb = aplt.Colorbar(
            ticksize=1,
            fraction=0.1,
            pad=0.5,
            manual_tick_values=[0.25, 0.5, 0.75],
            manual_tick_labels=[1.0, 2.0, 3.0],
        )
        cb.set()
        figure.close()

        figure.open()
        plt.imshow(np.ones((2, 2)))
        cb = aplt.Colorbar(ticksize=1, fraction=0.1, pad=0.5)
        cb.set_with_color_values(
            cmap=aplt.Cmap().config_dict["cmap"], color_values=[1.0, 2.0, 3.0]
        )
        figure.close()


class TestTicksParams:
    def test__loads_values_from_config_if_not_manually_input(self):
        tick_params = aplt.TickParams()

        assert tick_params.config_dict["labelsize"] == 16

        tick_params = aplt.TickParams(labelsize=24)
        assert tick_params.config_dict["labelsize"] == 24

        tick_params = aplt.TickParams()
        tick_params.for_subplot = True

        assert tick_params.config_dict["labelsize"] == 10

        tick_params = aplt.TickParams(labelsize=25)
        tick_params.for_subplot = True

        assert tick_params.config_dict["labelsize"] == 25


class TestYTicks:
    def test__ticks_loads_values_from_config_if_not_manually_input(self):

        yticks = aplt.YTicks()

        assert yticks.config_dict["labelsize"] == 16
        assert yticks.manual_values == None
        assert yticks.manual_values == None

        yticks = aplt.YTicks(labelsize=24, manual_values=[1.0, 2.0])

        assert yticks.config_dict["labelsize"] == 24
        assert yticks.manual_values == [1.0, 2.0]

        yticks = aplt.YTicks()
        yticks.for_subplot = True

        assert yticks.config_dict["labelsize"] == 10
        assert yticks.manual_values == None

        yticks = aplt.YTicks(labelsize=25, manual_values=[1.0, 2.0])
        yticks.for_subplot = True

        assert yticks.config_dict["labelsize"] == 25
        assert yticks.manual_values == [1.0, 2.0]

    def test__set__works_for_good_values(self):

        array = aa.Array.ones(shape_2d=(2, 2), pixel_scales=1.0)

        units = aplt.Units(use_scaled=True, conversion_factor=None)

        yticks = aplt.YTicks(labelsize=34)

        extent = array.extent_of_zoomed_array(buffer=1)

        yticks.set(
            array=array,
            min_value=extent[2],
            max_value=extent[3],
            units=units,
            use_defaults=False,
        )
        yticks.set(
            array=array,
            min_value=extent[2],
            max_value=extent[3],
            units=units,
            use_defaults=True,
        )

        yticks = aplt.YTicks(labelsize=34)

        units = aplt.Units(use_scaled=False, conversion_factor=None)

        yticks.set(
            array=array,
            min_value=extent[2],
            max_value=extent[3],
            units=units,
            use_defaults=False,
        )
        yticks.set(
            array=array,
            min_value=extent[2],
            max_value=extent[3],
            units=units,
            use_defaults=True,
        )

        yticks = aplt.YTicks(labelsize=34)

        units = aplt.Units(use_scaled=True, conversion_factor=2.0)

        yticks.set(
            array=array,
            min_value=extent[2],
            max_value=extent[3],
            units=units,
            use_defaults=False,
        )
        yticks.set(
            array=array,
            min_value=extent[2],
            max_value=extent[3],
            units=units,
            use_defaults=True,
        )

        yticks = aplt.YTicks(labelsize=34)

        units = aplt.Units(use_scaled=False, conversion_factor=2.0)

        yticks.set(
            array=array,
            min_value=extent[2],
            max_value=extent[3],
            units=units,
            use_defaults=False,
        )
        yticks.set(
            array=array,
            min_value=extent[2],
            max_value=extent[3],
            units=units,
            use_defaults=True,
        )


class TestXTicks:
    def test__ticks_loads_values_from_config_if_not_manually_input(self):
        xticks = aplt.XTicks()

        assert xticks.config_dict["labelsize"] == 17
        assert xticks.manual_values == None
        assert xticks.manual_values == None

        xticks = aplt.XTicks(labelsize=24, manual_values=[1.0, 2.0])

        assert xticks.config_dict["labelsize"] == 24
        assert xticks.manual_values == [1.0, 2.0]

        xticks = aplt.XTicks()
        xticks.for_subplot = True

        assert xticks.config_dict["labelsize"] == 11
        assert xticks.manual_values == None

        xticks = aplt.XTicks(labelsize=25, manual_values=[1.0, 2.0])
        xticks.for_subplot = True

        assert xticks.config_dict["labelsize"] == 25
        assert xticks.manual_values == [1.0, 2.0]

    def test__set__works_for_good_values(self):
        array = aa.Array.ones(shape_2d=(2, 2), pixel_scales=1.0)

        units = aplt.Units(use_scaled=True, conversion_factor=None)

        xticks = aplt.XTicks(labelsize=34)

        extent = array.extent_of_zoomed_array(buffer=1)

        xticks.set(
            array=array,
            min_value=extent[0],
            max_value=extent[1],
            units=units,
            use_defaults=False,
        )
        xticks.set(
            array=array,
            min_value=extent[0],
            max_value=extent[1],
            units=units,
            use_defaults=True,
        )

        xticks = aplt.XTicks(labelsize=34)

        units = aplt.Units(use_scaled=False, conversion_factor=None)

        xticks.set(
            array=array,
            min_value=extent[0],
            max_value=extent[1],
            units=units,
            use_defaults=False,
        )
        xticks.set(
            array=array,
            min_value=extent[0],
            max_value=extent[1],
            units=units,
            use_defaults=True,
        )

        xticks = aplt.XTicks(labelsize=34)

        units = aplt.Units(use_scaled=True, conversion_factor=2.0)

        xticks.set(
            array=array,
            min_value=extent[0],
            max_value=extent[1],
            units=units,
            use_defaults=False,
        )
        xticks.set(
            array=array,
            min_value=extent[0],
            max_value=extent[1],
            units=units,
            use_defaults=True,
        )

        xticks = aplt.XTicks(labelsize=34)

        units = aplt.Units(use_scaled=False, conversion_factor=2.0)

        xticks.set(
            array=array,
            min_value=extent[0],
            max_value=extent[1],
            units=units,
            use_defaults=False,
        )
        xticks.set(
            array=array,
            min_value=extent[0],
            max_value=extent[1],
            units=units,
            use_defaults=True,
        )


class TestTitle:
    def test__loads_values_from_config_if_not_manually_input(self):

        title = aplt.Title()

        assert title.config_dict["label"] == None
        assert title.config_dict["fontsize"] == 11

        title = aplt.Title(label="OMG", fontsize=1)

        assert title.config_dict["label"] == "OMG"
        assert title.config_dict["fontsize"] == 1

        title = aplt.Title()
        title.for_subplot = True

        assert title.config_dict["label"] == None
        assert title.config_dict["fontsize"] == 15

        title = aplt.Title(label="OMG2", fontsize=2)
        title.for_subplot = True

        assert title.config_dict["label"] == "OMG2"
        assert title.config_dict["fontsize"] == 2


class TestYLabel:
    def test__loads_values_from_config_if_not_manually_input(self):

        ylabel = aplt.YLabel()

        assert ylabel._units == None
        assert ylabel.config_dict["fontsize"] == 1

        ylabel = aplt.YLabel(units="hi", fontsize=11)

        assert ylabel._units == "hi"
        assert ylabel.config_dict["fontsize"] == 11

        ylabel = aplt.YLabel()
        ylabel.for_subplot = True

        assert ylabel._units == None
        assert ylabel.config_dict["fontsize"] == 2

        ylabel = aplt.YLabel(units="hi2", fontsize=12)
        ylabel.for_subplot = True

        assert ylabel._units == "hi2"
        assert ylabel.config_dict["fontsize"] == 12

    def test__units_use_plot_in_kpc_if_it_is_passed(self):

        ylabel = aplt.YLabel()

        units = aplt.Units(in_kpc=True)

        assert ylabel._units == None
        assert ylabel.label_from_units(units=units) == "kpc"

        ylabel = aplt.YLabel()

        units = aplt.Units(in_kpc=False)

        assert ylabel._units == None
        assert ylabel.label_from_units(units=units) == "arcsec"

        ylabel = aplt.YLabel(units="hi")

        units = aplt.Units(in_kpc=True)

        assert ylabel._units == "hi"
        assert ylabel.label_from_units(units=units) == "hi"

        ylabel = aplt.YLabel(units="hi")

        units = aplt.Units(in_kpc=False)

        assert ylabel._units == "hi"
        assert ylabel.label_from_units(units=units) == "hi"


class TestXLabel:
    def test__loads_values_from_config_if_not_manually_input(self):
        xlabel = aplt.XLabel()

        assert xlabel._units == None
        assert xlabel.config_dict["fontsize"] == 3

        xlabel = aplt.XLabel(units="hi", fontsize=11)

        assert xlabel._units == "hi"
        assert xlabel.config_dict["fontsize"] == 11

        xlabel = aplt.XLabel()
        xlabel.for_subplot = True

        assert xlabel._units == None
        assert xlabel.config_dict["fontsize"] == 4

        xlabel = aplt.XLabel(units="hi2", fontsize=12)
        xlabel.for_subplot = True

        assert xlabel._units == "hi2"
        assert xlabel.config_dict["fontsize"] == 12

    def test__units_use_plot_in_kpc_if_it_is_passed(self):
        xlabel = aplt.XLabel()

        units = aplt.Units(in_kpc=True)

        assert xlabel._units == None
        assert xlabel.label_from_units(units=units) == "kpc"

        xlabel = aplt.XLabel()

        units = aplt.Units(in_kpc=False)

        assert xlabel._units == None
        assert xlabel.label_from_units(units=units) == "arcsec"

        xlabel = aplt.XLabel(units="hi")

        units = aplt.Units(in_kpc=True)

        assert xlabel._units == "hi"
        assert xlabel.label_from_units(units=units) == "hi"

        xlabel = aplt.XLabel(units="hi")

        units = aplt.Units(in_kpc=False)

        assert xlabel._units == "hi"
        assert xlabel.label_from_units(units=units) == "hi"


class TestLegend:
    def test__legend__from_config_or_via_manual_input(self):

        legend = aplt.Legend()

        assert legend.include == False
        assert legend.config_dict["fontsize"] == 12

        legend = aplt.Legend(include=True, fontsize=11)

        assert legend.include == True
        assert legend.config_dict["fontsize"] == 11

        legend = aplt.Legend()
        legend.for_subplot = True

        assert legend.include == False
        assert legend.config_dict["fontsize"] == 13

        legend = aplt.Legend(include=True, fontsize=14)
        legend.for_subplot = True

        assert legend.include == True
        assert legend.config_dict["fontsize"] == 14

    def test__set_legend_works_for_plot(self):

        figure = aplt.Figure(aspect="auto")

        figure.open()

        line = aplt.LinePlot(linewidth=2, linestyle="-", colors="k", pointsize=2)

        line.plot_y_vs_x(
            y=[1.0, 2.0, 3.0], x=[1.0, 2.0, 3.0], plot_axis_type="linear", label="hi"
        )

        legend = aplt.Legend(include=True, fontsize=1)

        legend.set()

        figure.close()


class TestOutput:
    def test__constructor(self):

        output = aplt.Output()

        assert output.path == None
        assert output._format == None
        assert output.format == "show"
        assert output.filename == None

        output = aplt.Output(path="Path", format="png", filename="file")

        assert output.path == "Path"
        assert output._format == "png"
        assert output.format == "png"
        assert output.filename == "file"

        if path.exists(output.path):
            shutil.rmtree(output.path)

    def test__input_path_is_created(self):

        test_path = path.join(directory, "files", "output_path")

        if path.exists(test_path):
            shutil.rmtree(test_path)

        assert not path.exists(test_path)

        output = aplt.Output(path=test_path)

        assert path.exists(test_path)