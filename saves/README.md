# 📂 Minecraft Save Files Directory

Place your Minecraft world files, configuration, or plugins in this directory.

## 🗂️ Expected Directory Layout
```text
saves/
├── world/                 # Main overworld save folder (contains level.dat, region/, etc.)
├── world_nether/          # (Optional) Nether dimension folder
├── world_the_end/         # (Optional) The End dimension folder
├── server.properties      # (Optional) Custom server configuration properties
├── whitelist.json         # (Optional) User whitelist configuration
└── ops.json               # (Optional) Operators configuration
```

## 🚀 How to Upload Saves to GCE
Once your files are placed in this directory, run the helper script from the root workspace directory:
```bash
./scripts/upload-saves.sh
```

## 📥 How to Backup Saves from GCE
To download the current world files from your GCE instance to this local `saves/` folder:
```bash
./scripts/download-saves.sh
```
