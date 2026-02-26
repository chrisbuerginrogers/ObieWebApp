const divider = document.getElementById('divider');
const left = document.getElementById('sidebar');
const right = document.getElementById('main-content');
const container = document.getElementById('container');

divider.addEventListener('mousedown', () => {
    document.addEventListener('mousemove', resize);
    document.addEventListener('mouseup', () => {
        document.removeEventListener('mousemove', resize);
        });
        //Plotly.Plots.resize('plot');
    });

function resize(e) {
    const containerWidth = container.offsetWidth;
    const leftWidth = e.clientX / containerWidth * 100;

    left.style.flex = `0 0 ${leftWidth}%`;
    right.style.flex = `1 1 ${100 - leftWidth}%`;
    setTimeout(() => {
        Plotly.Plots.resize('plot');
    }, 0);
}
