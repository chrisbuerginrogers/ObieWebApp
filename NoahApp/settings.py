from js import localStorage
import json

plot_settings = localStorage.getItem('plot_settings')
if plot_settings is None:
    plot_settings = {
        'xmin': 100,
        'xmax': 10000,
        'dbrange': 100,
        'log': True
    }
    localStorage.setItem('plot_settings', json.dumps(plot_settings))
else:
    plot_settings = json.loads(plot_settings)

def save_plot_settings(xmin, xmax, dbrange, log):
    plot_settings = {
        'xmin': xmin,
        'xmax': xmax,
        'dbrange': dbrange,
        'log': log
    }
    localStorage.setItem('plot_settings', json.dumps(plot_settings))

def fetch_bands():
    bands = localStorage.getItem('bands')
    if bands is None:
        bands = {
            "No Bands": "",
            "sample1": "200-7000",
            "sample2": "200-780-1740-2930-7000",
            "CURRENT": "No Bands"
        }
        localStorage.setItem('bands', json.dumps(bands))
    else:
        bands = json.loads(bands)
    return bands

def fetch_stored_test():
    stored_data = localStorage.getItem('recent_test')
    if stored_data is not None:
        stored_data = json.loads(stored_data)
    return stored_data