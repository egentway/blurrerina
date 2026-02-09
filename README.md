# YOLO DeepStream Blurring Pipeline for Jetson Orin Nano

Questo progetto implementa una pipeline DeepStream per rilevare e sfocare (blur) elementi in video dashcam utilizzando YOLOv8.

## Struttura
- `Dockerfile`: Configurazione del container con DeepStream 6.3 e pyds.
- `main.py`: Pipeline GStreamer Python.
- `config_infer_primary_yolo.txt`: Configurazione per nvinfer (YOLOv8).
- `volume/`: Cartella montata che deve contenere `data/input.mp4` e `models/bestV8n.pt`.

## Istruzioni per l'uso

1. **Preparazione**:
   Assicurati di avere i modelli nella cartella `volume/models/`. Se vuoi ricostruire l'engine (raccomandato per compatibilità):
   - Inserisci `bestV8n.onnx` in `volume/models/`.
   - Modifica `config_infer_primary_yolo.txt` impostando `onnx-model=volume/models/bestV8n.onnx` e commentando `model-engine-file`.

2. **Build**:
   ```bash
   docker-compose build
   ```

3. **Run**:
   ```bash
   docker-compose up
   ```
   Il video elaborato sarà salvato in `volume/output/output.mp4`.

## Note Tecnici
- La pipeline utilizza `nvdsblur` per un'efficienza ottimale su GPU.
- Il parser personalizzato per YOLOv8 viene compilato automaticamente durante la build del Dockerfile partendo dal repository `marcoslucianops/DeepStream-Yolo`.
- I parametri di codifica sono ottimizzati per dashcam (4Mbps H264).
