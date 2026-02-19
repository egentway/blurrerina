import shutil
from pathlib import Path
import blurrerina.paths as paths

def scavenge_tensorrt_model():
    """
    If not present, DeepStream creates the model in the TensorRT .engine format 
    in the current folder. To avoid needing regenerating it each time, it's necessary
    to move it to a persistent location pointed at by nvinfer's configuration file.
    """

    for model_file in Path().glob("*.engine"):
        shutil.copy(model_file, paths.models_path / model_file.name)