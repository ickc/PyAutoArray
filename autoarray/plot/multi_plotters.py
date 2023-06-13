from typing import Tuple

from autoarray.plot.wrap.base.ticks import YTicks
from autoarray.plot.wrap.base.ticks import XTicks


class MultiFigurePlotter:
    def __init__(self, plotter_list, subplot_shape: Tuple[int, int] = None):
        self.plotter_list = plotter_list
        self.subplot_shape = subplot_shape

    def subplot_of_figure(self, func_name, figure_name, filename_suffix="", **kwargs):
        number_subplots = len(self.plotter_list)

        self.plotter_list[0].open_subplot_figure(
            number_subplots=number_subplots, subplot_shape=self.subplot_shape
        )

        for i, plotter in enumerate(self.plotter_list):
            func = getattr(plotter, func_name)

            if figure_name is None:
                func(**{**{}, **kwargs})
            else:
                func(**{**{figure_name: True}, **kwargs})

        if self.plotter_list[0].mat_plot_1d is not None:
            self.plotter_list[0].mat_plot_1d.output.subplot_to_figure(
                auto_filename=f"subplot_{figure_name}{filename_suffix}"
            )
        if self.plotter_list[0].mat_plot_2d is not None:
            self.plotter_list[0].mat_plot_2d.output.subplot_to_figure(
                auto_filename=f"subplot_{figure_name}{filename_suffix}"
            )
        self.plotter_list[0].close_subplot_figure()

    def subplot_of_multi_yx_1d(self, filename_suffix="", **kwargs):
        number_subplots = len(self.plotter_list)

        self.plotter_list[0].plotter_list[0].open_subplot_figure(
            number_subplots=number_subplots, subplot_shape=self.subplot_shape
        )

        for i, plotter in enumerate(self.plotter_list):
            for plott in plotter.plotter_list:
                plott.mat_plot_1d.set_for_subplot(is_for_subplot=True)
                plott.mat_plot_1d.number_subplots = number_subplots
                plott.mat_plot_1d.subplot_shape = self.subplot_shape
                plott.mat_plot_1d.subplot_index = i + 1

            func = getattr(plotter, "figure_1d")
            func(
                **{
                    **{
                        "func_name": "figure_1d",
                        "figure_name": None,
                        "is_for_subplot": True,
                    },
                    **kwargs,
                }
            )

        self.plotter_list[0].plotter_list[0].mat_plot_1d.output.subplot_to_figure(
            auto_filename=f"subplot_{filename_suffix}"
        )
        self.plotter_list[0].plotter_list[0].close_subplot_figure()


class MultiYX1DPlotter:
    def __init__(self, plotter_list, color_list=None, legend_labels=None):
        self.plotter_list = plotter_list

        if color_list is None:
            color_list = 10 * ["k", "r", "b", "g", "c", "m", "y"]

        self.color_list = color_list
        self.legend_labels = legend_labels

    def figure_1d(self, func_name, figure_name, is_for_subplot=False, **kwargs):
        if not is_for_subplot:
            self.plotter_list[0].mat_plot_1d.figure.open()

        for i, plotter in enumerate(self.plotter_list):
            plotter.set_mat_plot_1d_for_multi_plot(
                is_for_multi_plot=True, color=self.color_list[i], yticks=self.yticks, xticks=self.xticks
            )

            if self.legend_labels is not None:
                plotter.mat_plot_1d.yx_plot.label = self.legend_labels[i]

            func = getattr(plotter, func_name)

            if figure_name is None:
                func(**{**{}, **kwargs})
            else:
                func(**{**{figure_name: True}, **kwargs})

            plotter.set_mat_plot_1d_for_multi_plot(is_for_multi_plot=False, color=None)

        if not is_for_subplot:
            self.plotter_list[0].mat_plot_1d.output.subplot_to_figure(
                auto_filename=f"multi_{figure_name}"
            )
            self.plotter_list[0].mat_plot_1d.figure.close()

    @property
    def yticks(self):
        min_value = min([min(plotter.y) for plotter in self.plotter_list])
        max_value = max([max(plotter.y) for plotter in self.plotter_list])

        return YTicks(manual_min_max_value=(min_value, max_value))

    @property
    def xticks(self):
        min_value = min([min(plotter.x) for plotter in self.plotter_list])
        max_value = max([max(plotter.x) for plotter in self.plotter_list])

        return XTicks(manual_min_max_value=(min_value, max_value))
