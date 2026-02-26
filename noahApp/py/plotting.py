from pyodide.ffi import to_js
from pyscript import document
from js import Plotly, Object
import math
import numpy as np

color_list = [
    "#1f77b4",  # muted blue
    "#ff7f0e",  # safety orange
    "#2ca02c",  # cooked asparagus green
    "#d62728",  # brick red
    "#9467bd",  # muted purple
    "#8c564b",  # chestnut brown
    "#e377c2",  # raspberry yogurt pink
    "#7f7f7f",  # middle gray
    "#bcbd22",  # curry yellow-green
    "#17becf",  # blue-teal
    "#393b79",  # dark slate blue
    "#637939",  # olive green
    "#8c6d31",  # dark goldenrod
    "#843c39",  # dark brick red
    "#7b4173",  # dark mauve
    "#3182bd",  # bright steel blue
    "#e6550d",  # dark orange
    "#31a354",  # medium sea green
    "#756bb1",  # medium purple
    "#636363"   # dark gray
]

class PlotManager:
    def __init__(self, xmin=None, xmax=None, dBrange=None, log=True):

        self.xmin = xmin
        self.xmax = xmax
        self.dBrange = dBrange
        self.log = log
        self.band_text = ""

        self.plot_type = "magnitude"

        self.raw_data = {}
        
        self.traces = []
        self.layout = {
            'title': {
                'text': 'FRF','x': 0.5, 'xanchor': 'center'
            },
            'xaxis': {
                'type': 'log',
                'autorange': True,
                'title': {'text': 'frequency (Hz)', 'standoff': 20},
                'showticklabels': True,  
            },
            'yaxis': {
                'autorange': True, 
                'type': 'linear',  
                'title': {'text': 'amplitude (dB)', 'standoff': 10},
                'showticklabels': True,
            },
            'showlegend': False,
        }

        self.plot_settings(self.xmin, self.xmax, self.dBrange, self.log)
        layout_js = to_js(self.layout, dict_converter=Object.fromEntries)
        traces_js = to_js(self.traces, dict_converter=Object.fromEntries)
        Plotly.newPlot('plot', traces_js, layout_js)

    def plot_settings(self, xmin, xmax, dBrange, log):
        self.xmin = xmin
        self.xmax = xmax
        self.dBrange = dBrange
        self.log = log
        if self.plot_type != "real_imag":
            if xmin is None and xmax is None:
                self.layout['xaxis']['autorange'] = True
            else:
                self.layout['xaxis']['autorange'] = False
                if self.traces:
                    if xmin is None:
                        xmin = min(min(trace['x']) for trace in self.traces if trace['x'])
                    if xmax is None:
                        xmax = max(max(trace['x']) for trace in self.traces if trace['x'])
                if log:
                    if xmin > 0:
                        xmin = math.log10(xmin)
                    elif xmin < 0:
                        xmin = -math.log10(abs(xmin))
                    xmax = math.log10(xmax)
                self.layout['xaxis']['range'] = [xmin, xmax]

            if log:
                self.layout['xaxis']['type'] = 'log'
            else:
                self.layout['xaxis']['type'] = 'linear'

            self.layout['xaxis']['scaleanchor'] = None
            self.layout['yaxis']['scaleratio'] = None
        else:
            self.layout['xaxis']['autorange'] = True
            self.layout['xaxis']['type'] = 'linear'
            # enforce equal aspect ratio for real vs imag
            self.layout['xaxis']['scaleanchor'] = 'y'
            self.layout['yaxis']['scaleratio'] = 1

        if self.plot_type == "magnitude":
            if dBrange is None:
                self.layout['yaxis']['autorange'] = True
            else:
                self.layout['yaxis']['autorange'] = False
                if self.traces:
                    ymax = max(max(trace['y']) for trace in self.traces if trace['y'])
                    print(ymax)
                else:
                    ymax = 30
                ymin = ymax - dBrange
                self.layout['yaxis']['range'] = [ymin, ymax]
        else:
            self.layout['yaxis']['autorange'] = True

        #layout_js = to_js(self.layout, dict_converter=Object.fromEntries)
        #Plotly.relayout('plot', layout_js)

    def trace_type(self, trace):
        name = trace['file_id']
        frf = self.raw_data[name][0]
        frequencies = self.raw_data[name][1]
        if self.plot_type == "phase_rad":
            x = frequencies
            y = np.angle(frf).tolist()
        elif self.plot_type == "phase_deg":
            x = frequencies
            y = np.angle(frf, deg=True).tolist()
        elif self.plot_type == "magnitude":
            x = frequencies
            y = [20*math.log10(abs(f)) for f in frf]
        elif self.plot_type == "real_imag":
            x = np.real(frf).tolist()
            y = np.imag(frf).tolist()
        trace['x'] = x
        trace['y'] = y
        return trace

    def set_plot_type(self, type):
        self.traces = [
            trace for trace in self.traces
            if not trace.get('file_id', '').endswith("_banded")
            and not trace.get('file_id', '').endswith("_centroid")
        ]
        self.plot_type = type
        for trace in self.traces:
            trace = self.trace_type(trace)
        self.plot_settings(self.xmin, self.xmax, self.dBrange, self.log)
        self.layout['xaxis']['title']['text'] = 'frequency (Hz)'
        if self.plot_type == "magnitude":
            self.layout['yaxis']['title']['text'] = "amplitude (dB)"
        elif self.plot_type == "phase_rad":
            self.layout['yaxis']['title']['text'] = "phase (rad)"
        elif self.plot_type == "phase_deg":
            self.layout['yaxis']['title']['text'] = "phase (deg)"
        elif self.plot_type == "real_imag":
            self.layout['yaxis']['title']['text'] = "imaginary part"
            self.layout['xaxis']['title']['text'] = "real part"
        band_text = document.getElementById("bands").value
        self.plot_bands(self.band_text)
        

    def add_frf(self, frf, frequencies, name='FRF', color='blue'):
        self.raw_data[name] = (frf, frequencies)
        FRF = {
            'x': [], 'y': [],
            'type': 'scatter',
            'name': name, 
            'line': {'width': 1, 'color': color},
            'file_id': name,
            'visible': True,
        }
        FRF = self.trace_type(FRF)
        self.traces.append(FRF)
        self.plot_settings(self.xmin, self.xmax, self.dBrange, self.log)
        band_text = document.getElementById("bands").value
        self.plot_bands(self.band_text)
        #traces_js = to_js(self.traces, dict_converter=Object.fromEntries)
        #layout_js = to_js(self.layout, dict_converter=Object.fromEntries)
        #Plotly.newPlot('plot', traces_js, layout_js)

    def get_index(self, trace_name):
        trace_index = None
        for i, trace in enumerate(self.traces):
            if trace.get('file_id') == trace_name:
                trace_index = i
                break
        band_index = None
        for i, trace in enumerate(self.traces):
            if trace.get('file_id') == f"{trace_name}_banded":
                band_index = i
                break
        centroid_index = None
        for i, trace in enumerate(self.traces):
            if trace.get('file_id') == f"{trace_name}_centroid":
                centroid_index = i
                break
                
        return [trace_index, band_index, centroid_index]

    def set_color(self, trace_name, color):
        indices = self.get_index(trace_name)
        for trace_index in indices:
            if trace_index is None:
                continue
            trace = self.traces[trace_index]
        
            if 'line' in trace:  # line plot
                trace['line']['color'] = color
                js_visibility = to_js({'line.color': color}, dict_converter=Object.fromEntries)
        
            elif 'marker' in trace:  # markers only
                trace['marker']['color'] = color
                js_visibility = to_js({'marker.color': color}, dict_converter=Object.fromEntries)

            js_idx = to_js([trace_index], dict_converter=Object.fromEntries)
            Plotly.restyle('plot', js_visibility, js_idx)

    def hide_trace(self, trace_name):
        indices = self.get_index(trace_name)
        for trace_index in indices:
            if trace_index is not None:
                self.traces[trace_index]['visible'] = False
                js_visibility = to_js({'visible': False}, dict_converter=Object.fromEntries)
                js_idx = to_js([trace_index], dict_converter=Object.fromEntries)
                Plotly.restyle('plot', js_visibility, js_idx)
            else:
                print(f"No trace associated with {trace_name}")

    def show_trace(self, trace_name):
        indices = self.get_index(trace_name)
        for trace_index in indices:
            if trace_index is not None:
                self.traces[trace_index]['visible'] = True
                js_visibility = to_js({'visible': True}, dict_converter=Object.fromEntries)
                js_idx = to_js([trace_index], dict_converter=Object.fromEntries)
                Plotly.restyle('plot', js_visibility, js_idx)
            else:
                print(f"No trace associated with {trace_name}")

    def delete_trace(self, trace_name):
        indices = self.get_index(trace_name)
        for trace_index in indices[::-1]: # reverse to remove the band on first
            if trace_index is not None:     
                self.traces.pop(trace_index)
                Plotly.deleteTraces('plot', trace_index)
            else:
                print(f"No trace associated with {trace_name}")
        if trace_name in self.raw_data:
            del self.raw_data[trace_name]

    def redraw(self):
        layout_js = to_js(self.layout, dict_converter=Object.fromEntries)
        traces_js = to_js(self.traces, dict_converter=Object.fromEntries)
        Plotly.newPlot('plot', traces_js, layout_js)

    def resize(self):
        Plotly.Plots.resize('plot');

    def clear_plot(self):
        self.traces.clear()
        layout_js = to_js(self.layout, dict_converter=Object.fromEntries)
        traces_js = to_js(self.traces, dict_converter=Object.fromEntries)
        Plotly.newPlot('plot', traces_js, layout_js)

    def plot_bands(self, band_text):
        #first get ride of bands and c
        self.traces = [
            trace for trace in self.traces
            if not trace.get('file_id', '').endswith("_banded")
            and not trace.get('file_id', '').endswith("_centroid")
        ]
        self.band_text = band_text
        if band_text == "" or self.plot_type == "real_imag":
            for trace in self.traces:
                trace['opacity'] = 1  # set opacity
            self.redraw()
        else:
            band_limits = band_text.split("-")
            band_limits = [float(band) for band in band_limits]
            print(band_limits)
            band_traces = []
            centroid_traces = []
            for trace in self.traces:
                # build up banded trace
                banded_frf = trace.copy()
                banded_frf['file_id'] = f"{trace['file_id']}_banded"
                color = trace['line']['color']
                frequencies = np.array(trace['x'])
                mag_db = np.array(trace['y'])
                magnitudes = 10**(mag_db/20) # convert to linear for averaging
                indices = [np.abs(frequencies - b).argmin() for b in band_limits]
                banded_freqs = frequencies[indices[0]:indices[-1]].tolist()
                banded_mags = []
                centroid_freqs = []
                centroid_mags = []
                for i in range(len(indices)-1):
                    mag_slice = magnitudes[indices[i]:indices[i+1]]
                    freq_slice = frequencies[indices[i]:indices[i+1]]
                    mean = 20*math.log10(np.mean(mag_slice)) #back to db
                    band = [mean] * len(mag_slice)
                    banded_mags.extend(band)
                    centroid = np.sum(np.array(freq_slice) * np.array(mag_slice)) / np.sum(mag_slice)
                    centroid_freqs.append(centroid)
                    centroid_mags.append(mean)
                banded_frf['x'] = banded_freqs
                banded_frf['y'] = banded_mags
                trace['opacity'] = 0.1
                banded_frf['opacity'] = 1
                band_traces.append(banded_frf)

                centroid_trace = {
                    'x': centroid_freqs, 'y': centroid_mags,
                    'type': 'scatter',
                    'mode': 'markers',
                    'name': f"{trace['file_id']}_centroid", 
                    'marker': {'width': 3, 'color': color},
                    'file_id': f"{trace['file_id']}_centroid",
                    'visible': trace['visible']
                }
                centroid_traces.append(centroid_trace)

            self.traces.extend(band_traces)
            self.traces.extend(centroid_traces)
            self.redraw()