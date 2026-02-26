from pyscript import document, window, when
import json
from plotting import PlotManager, color_list
from trf_files import unpack_trf
from tsv_files import unpack_tsv
from av_files import unpack_av
from settings_files import unpack_settings
from pyscript.js_modules import Files
from pyodide.ffi import create_proxy
from settings import *
import time

plotter = PlotManager(plot_settings['xmin'], plot_settings['xmax'], plot_settings['dbrange'], plot_settings['log'])

fileReader = Files.Files.new()

full_list = []
filtered_list = []
active_list = []

def remove_file(file_name):
    global active_list
    file_list_el = document.getElementById("file-list")
    items = file_list_el.getElementsByTagName("li")

    for li in items:
        label = li.querySelector("label")
        if label and label.innerText == file_name:
            file_list_el.removeChild(li)
            break

    if file_name in active_list:
        active_list.remove(file_name)


async def build_list(files_list):
    global active_list
    for i, file_object in enumerate(files_list):
        relative_path = file_object.webkitRelativePath
        file_name = relative_path.split("/")[-1]

        if file_name in active_list:
            add_file = False
        else:
            add_file = True
            if file_name.endswith(".trf"):
                contents = await fileReader.readFileObject(file_object, asText=False)
                contents = json.loads(contents)
                loaded_trf = unpack_trf(bytes(contents))
                start = loaded_trf["Start_Freq"]
                df = loaded_trf["Hz_Resolution"]
                length = int(loaded_trf["fLength"])
                frequencies = [start + i * df for i in range(length)]
                frf = loaded_trf["data"]
                #magnitudes = [abs(f) for f in frf]
            elif file_name.endswith(".tsv"):
                contents = await fileReader.readFileObject(file_object, asText=True)
                frequencies, frf = unpack_tsv(contents)
                #magnitudes = [abs(f) for f in frf]
            elif file_name.endswith(".AvR") or file_name.endswith(".AvC"):
                contents = await fileReader.readFileObject(file_object, asText=False)
                contents = json.loads(contents)
                loaded_av = unpack_av(bytes(contents))
                start = loaded_av["Start_Freq"]
                df = loaded_av["Hz_Resolution"]
                length = int(loaded_av["fLength"])
                frequencies = [start + i * df for i in range(length)]
                frf = loaded_av["data"]
            else:
                add_file = False
            
        if add_file:
            await add_to_list(frequencies, frf, file_name)
            

async def add_to_list(frequencies, frf, file_name):
    file_list_el = document.getElementById("file-list")
    color = color_list[len(active_list) % len(color_list)]
    plotter.add_frf(frf, frequencies, name=file_name, color=color)
    active_list.append(file_name)
    # Create a list item
    li = document.createElement("li")
    # Create checkbox
    checkbox = document.createElement("input")
    checkbox.type = "checkbox"
    checkbox.id = file_name
    checkbox.checked = True
    checkbox.value = file_name
    
    # Define the checkbox change handler
    def checkbox_handler(event):
        checkbox = event.target
        file_name = checkbox.id
        if checkbox.checked:
            print(f"{file_name} checked")
            plotter.show_trace(file_name)
        else:
            print(f"{file_name} unchecked")
            plotter.hide_trace(file_name)

    checkbox.addEventListener("change", create_proxy(checkbox_handler))

    # Create label for checkbox
    label = document.createElement("label")
    label.htmlFor = checkbox.id
    label.innerText = file_name
    label.style.marginLeft = "6px"  # small gap between checkbox and text

    # add color picker
    picker = document.createElement("input")
    picker.type = "color"
    picker.value = color
    picker.dataset.id = file_name
    
    def on_color_change(event):
        picker = event.target
        file_name = picker.dataset.id
        color = picker.value
        plotter.set_color(file_name, color)
    
    picker.addEventListener("input", create_proxy(on_color_change))

    # Append checkbox and label to the list item
    li.appendChild(checkbox)
    li.appendChild(label)
    li.appendChild(picker)

    file_list_el.appendChild(li)

def find_file(file_name, file_list):
    file_object = None
    for file in file_list:
        name = file.webkitRelativePath.split("/")[-1]
        if file_name == name:
            file_object = file
            break
    return file_object

@when('change','#fileRead')
async def on_read_file(event):
    global full_list
    files_list = document.getElementById('fileRead').files
    full_list = [files_list.item(i) for i in range(files_list.length)]
    folder_name = files_list.item(0).webkitRelativePath.split("/")[0]
    #document.getElementById("name_input").value = folder_name

    file_info = document.getElementById("folder-info")
    file_info.innerHTML = f"<b>Folder:</b> {folder_name}"

    settings_file = find_file("LastSettings.txt", full_list)
    if settings_file is None:
        settings_file = find_file("Settings.txt", full_list)
    if settings_file is not None:
        contents = await fileReader.readFileObject(settings_file, asText=True)
        settings = unpack_settings(contents)
        await load_settings(settings)

@when("click", "#load-all")
async def load_all(event):
    await build_list(full_list)

@when("click", "#see-all")
def show_all(event):
    file_list_el = document.getElementById("file-list")
    checkboxes = file_list_el.querySelectorAll("input[type='checkbox']")
    
    for checkbox in checkboxes:
        if not checkbox.checked:
            checkbox.checked = True
            # Manually dispatch the change event to trigger the handler
            event = window.Event.new("change")
            checkbox.dispatchEvent(event)

@when("click", "#see-none")
def hide_all(event):
    file_list_el = document.getElementById("file-list")
    checkboxes = file_list_el.querySelectorAll("input[type='checkbox']")
    
    for checkbox in checkboxes:
        if checkbox.checked:
            checkbox.checked = False
            # Manually dispatch the change event to trigger the handler
            event = window.Event.new("change")
            checkbox.dispatchEvent(event)

@when("click", "#reduce")
def reduce(event):
    file_list_el = document.getElementById("file-list")
    checkboxes = file_list_el.querySelectorAll("input[type='checkbox']")
    
    for checkbox in checkboxes:
        if not checkbox.checked:
            file_name = checkbox.id
            remove_file(file_name)
            plotter.delete_trace(file_name)

@when("click", "#clear")
def clear(event):
    global active_list
    file_list_el = document.getElementById("file-list")
    
    # Remove all child elements (li items)
    while file_list_el.firstChild:
        file_list_el.removeChild(file_list_el.firstChild)
    
    # Clear active_list
    active_list.clear()
    
    # Clear plot
    plotter.clear_plot()  # You should implement this in your Plotter class

@when("click", "#search")
def show_modal(event=None):
    apply_filter()
    document.getElementById("search-modal").style.display = "block"

def apply_filter(event=None):
    clear_filter()
    name_filter1 = document.getElementById("name-filter1").value.lower()
    name_filter2 = document.getElementById("name-filter2").value.lower()
    name_filter3 = document.getElementById("name-filter3").value.lower()
    name_filters = [name_filter1, name_filter2, name_filter3]
    name_filters = [f for f in name_filters if f != ""]
    
    type_filter = []
    if document.getElementById("trf").checked:
        type_filter.append(".trf")
    if document.getElementById("tsv").checked:
        type_filter.append(".tsv")
    if document.getElementById("avc").checked:
        type_filter.append(".avc")
    if document.getElementById("avr").checked:
        type_filter.append(".avr")
    if type_filter == []:
        type_filter = ""

    filtered = []
    for i, file_object in enumerate(full_list):
        file_name = file_object.webkitRelativePath.split("/")[-1].lower()
        if not name_filters or any(f in file_name for f in name_filters):
            if (type_filter == "" or file_name.endswith(tuple(type_filter))):
                filtered.append(i)

    file_list_el = document.getElementById("filtered-list")
    for index in filtered:
        file_object = full_list[index]
        relative_path = file_object.webkitRelativePath
        file_name = relative_path.split("/")[-1]

        # Create a list item
        li = document.createElement("li")
        # Create checkbox
        checkbox = document.createElement("input")
        checkbox.type = "checkbox"
        checkbox.id = f"filter:{file_name}"
        checkbox.checked = False
        checkbox.value = index
        
        # Define the checkbox change handler
        def checkbox_handler(event):
            global filtered_list
            checkbox = event.target
            file_name = checkbox.id
            index = int(checkbox.value)
            if checkbox.checked:
                print(f"{file_name} checked")
                filtered_list.append(full_list[index])
            else:
                print(f"{file_name} unchecked")
                filtered_list.remove(full_list[index])
        checkbox.addEventListener("change", create_proxy(checkbox_handler))

        # Create label for checkbox
        label = document.createElement("label")
        label.htmlFor = checkbox.id
        label.innerText = file_name
        label.style.marginLeft = "6px"  # small gap between checkbox and text

        # Append checkbox and label to the list item
        li.appendChild(checkbox)
        li.appendChild(label)

        file_list_el.appendChild(li)
        
@when("click", "#add-files")
async def add_files(event):
    global filtered_list
    await build_list(filtered_list)
    hide_modal()

def clear_filter():
    global filtered_list
    file_list_el = document.getElementById("filtered-list")
    # Remove all child elements (li items)
    while file_list_el.firstChild:
        file_list_el.removeChild(file_list_el.firstChild)
    filtered_list.clear()

def hide_modal(event=None):
    document.getElementById("search-modal").style.display = "none"
    clear_filter()
    
document.getElementById("close-modal").addEventListener("click", create_proxy(hide_modal))

def setup_listeners():
    input_ids = ["trf", "tsv", "avc", "avr", "name-filter1", "name-filter2", "name-filter3"]
    for id in input_ids:
        el = document.getElementById(id)
        el.addEventListener("change", create_proxy(apply_filter))
        el.addEventListener("input", create_proxy(apply_filter))  # For text inputs

setup_listeners()

@when("click", "#select-all")
def select_all(event):
    file_list_el = document.getElementById("filtered-list")
    checkboxes = file_list_el.querySelectorAll("input[type='checkbox']")
    for checkbox in checkboxes:
        if not checkbox.checked:
            checkbox.checked = True
            event = window.Event.new("change")
            checkbox.dispatchEvent(event)

@when("click", "#deselect-all")
def deselect_all(event):
    file_list_el = document.getElementById("filtered-list")
    checkboxes = file_list_el.querySelectorAll("input[type='checkbox']")
    for checkbox in checkboxes:
        if checkbox.checked:
            checkbox.checked = False
            event = window.Event.new("change")
            checkbox.dispatchEvent(event)

def on_resize(event):
    plotter.resize()
window.addEventListener("resize", create_proxy(on_resize))

@when("click", "#acquire")
def open_acquire_page(event):
    window.open("https://noahsaxenian.pyscriptapps.com/auto-obieapp2/latest/", "_blank")

@when("click", "#analyze")
def open_analysis_page(event):
    window.open("https://noahsaxenian.pyscriptapps.com/mode-shape-viewer/latest/", "_blank")

@when('change','#settings-file')
async def read_settings_file(event):
    contents = await fileReader.read("settings-file", asText=True)
    settings = unpack_settings(contents)
    await load_settings(settings)

async def load_settings(settings):
    #print(settings)
    x_range = settings.get('X Range')
    if x_range:
        document.getElementById("xmin").value = x_range[3][2]
        document.getElementById("xmax").value = x_range[3][1]
    document.getElementById("dbrange").value = settings.get('dB Spread', 70)
    save_settings()


def save_settings(event=None):
    # Read values from inputs
    val = document.getElementById("xmin").value
    xmin = float(val) if val.strip() != "" else None
    val = document.getElementById("xmax").value
    xmax = float(val) if val.strip() != "" else None
    val = document.getElementById("dbrange").value
    dbrange = float(val) if val.strip() != "" else None
    logX = document.getElementById("logX").checked

    save_plot_settings(xmin, xmax, dbrange, logX)
    plotter.plot_settings(xmin, xmax, dbrange, logX)
    plotter.redraw()

# fill settings
document.getElementById("xmin").value = plotter.xmin
document.getElementById("xmax").value = plotter.xmax
document.getElementById("dbrange").value = plotter.dBrange
document.getElementById("logX").checked = plotter.log
# save on change
document.getElementById("xmin").addEventListener("change", create_proxy(save_settings))
document.getElementById("xmax").addEventListener("change", create_proxy(save_settings))
document.getElementById("dbrange").addEventListener("change", create_proxy(save_settings))
document.getElementById("logX").addEventListener("change", create_proxy(save_settings))

### setup bands select
bands = None
band_text = ""
def populate_bands_dropdown():
    global bands
    bands = fetch_bands()
    select_el = document.getElementById("bands")
    select_el.innerHTML = "" #clear
    for label, value in bands.items():
        if label == "CURRENT":
            continue
        option = document.createElement("option")
        if value == "":
            option.text = label
        else:
            option.text = f"{label} ({value})"
        option.value = label
        select_el.add(option)
    # set current selection
    current = bands.get("CURRENT")
    select_el = document.getElementById("bands")
    for i in range(select_el.options.length):
        if select_el.options.item(i).value == current:
            select_el.selectedIndex = i
            break
    band_text = bands.get(current)
    plotter.plot_bands(band_text)
populate_bands_dropdown()

@when("change", "#bands")
def set_bands(event):
    global bands
    band_label = document.getElementById("bands").value
    band_text = bands.get(band_label)
    print(band_label, band_text)
    plotter.plot_bands(band_text)
    # update current selection
    bands["CURRENT"] = band_label
    localStorage.setItem("bands", json.dumps(bands))

@when("click", "#band-btn")
def show_band_editor(event=None):
    document.getElementById("bands-modal").style.display = "block"

@when("click", "#close-bands")
def hide_band_editor(event=None):
    populate_bands_dropdown()
    document.getElementById("bands-modal").style.display = "none"

@when("change", "#plot-dropdown")
def set_plot_type(event):
    plot_type = document.getElementById("plot-dropdown").value
    plotter.set_plot_type(plot_type)

async def load_recent_test():
    stored_data = fetch_stored_test()
    now = time.time()
    if stored_data is not None:
        data_time = stored_data.pop('time')
        if now - data_time < 60:                           # only load if from test in the last minute
            frequencies = stored_data.pop('frequencies')
            for name, data in stored_data.items():
                print(name)
                real = data[0]
                imag = data[1]
                frf = [r + 1j * i for r, i in zip(real, imag)]
                await add_to_list(frequencies, frf, name)
        else:
            print('old data')
    else:
        print('no stored data')

load_recent_test()