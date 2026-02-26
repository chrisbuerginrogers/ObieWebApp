//  from ChatGPT

function readFile(file, mode = 'arrayBuffer') {
    return new Promise((resolve, reject) => {
        if (!(file instanceof Blob)) {
            reject(new Error('Invalid file: must be a Blob or File'));
            return;
        }

        const reader = new FileReader();

        reader.onload = (event) => resolve(event.target.result);
        reader.onerror = (error) => reject(error);

        if (mode === 'text') {
            reader.readAsText(file);
        } else {
            reader.readAsArrayBuffer(file);
        }
    });
}

export class Files {
    constructor() {
        this.file = null;
        this.content = null;
    }

    async read(name, { asText = false } = {}) {
        try {
            const fileInput = document.getElementById(name);
            const file = fileInput?.files?.[0];
            if (!file) throw new Error('No file selected');

            this.content = await readFile(file, asText ? 'text' : 'arrayBuffer');

            return asText
                ? this.content
                : JSON.stringify(Array.from(new Uint8Array(this.content)));
        } catch (error) {
            console.error(`Error reading file: ${error.message}`);
        }
    }

    async readFileObject(file, { asText = false } = {}) {
        try {
            this.content = await readFile(file, asText ? 'text' : 'arrayBuffer');

            return asText
                ? this.content
                : JSON.stringify(Array.from(new Uint8Array(this.content)));
        } catch (error) {
            console.error(`Error reading file object: ${error.message}`);
        }
    }
}


export class FileSaver {
    constructor(baseFolder = "my_files") {
        this.baseFolder = baseFolder;
        this.baseDirHandle = null;
    }

    // Prompt user to choose the root directory and create the base folder
    async chooseDirectory() {
        try {
            this.baseFolder = document.querySelector("#name_input").value || "my_files";
            const rootHandle = await window.showDirectoryPicker();
            this.baseDirHandle = await rootHandle.getDirectoryHandle(this.baseFolder, { create: true });
            console.log(`Base folder "${this.baseFolder}" is ready.`);
        } catch (error) {
            console.error("Error choosing directory:", error);
        }
    }

    // Save to a subdirectory inside the base folder
    async saveFile(content, fileName, subDir = "") {
        if (!this.baseDirHandle) {
            console.warn("Directory not chosen. Call chooseDirectory() first.");
            return;
        }
    
        try {
            let targetDir = this.baseDirHandle;
    
            // If a subDir is specified, create or get it
            if (subDir) {
                targetDir = await this._getOrCreateSubDir(targetDir, subDir);
            }
    
            const fileHandle = await targetDir.getFileHandle(fileName, { create: true });
            const writable = await fileHandle.createWritable();
    
            let blob;

            // Case 1: String (text or TSV)
            if (typeof content === "string") {
                blob = new Blob([content], { type: "text/plain" });
            }

            // Case 2: Python bytes object (Pyodide)
            else if (typeof content === "object") {
                console.log("saving wav");
                const uint8 = content.toJs(); // Convert to Uint8Array
                blob = new Blob([uint8], { type: "audio/wav" });
            }
    
            // Case 3: Already a BlobPart (e.g., Uint8Array or Blob)
            else {
                console.log("this is wrong");
                blob = new Blob([content]);
            }
    
            await writable.write(blob);
            await writable.close();
    
            console.log(`File "${fileName}" saved in "${subDir || this.baseFolder}"`);
        } catch (error) {
            console.error("Error saving file:", error);
        }
    }

    // Helper to walk or create nested subdirectories
    async _getOrCreateSubDir(dirHandle, path) {
        const folders = path.split("/").filter(Boolean);
        let current = dirHandle;

        for (const folder of folders) {
            current = await current.getDirectoryHandle(folder, { create: true });
        }

        return current;
    }
}
