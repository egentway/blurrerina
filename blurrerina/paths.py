from datetime import datetime
from pathlib import Path

def make_output_filename():
    datestr = datetime.now().strftime(r'%Y%m%d_%H%M%S')
    return f"output_{datestr}.mp4"


base_path = Path("/app/volume")
input_file = base_path / "data" / "input.mp4"
output_file = base_path / "output" / make_output_filename()
config_file = base_path / "config" / "config_infer_primary.txt"
models_path = base_path / "models"