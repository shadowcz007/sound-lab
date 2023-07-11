"""
Flask server that serves the riffusion model as an API.
"""
 
import json
 
import time
import typing as T
from pathlib import Path

 
import flask
 
from flask_cors import CORS

import random
import base64

from transformers import AutoProcessor, MusicgenForConditionalGeneration
import torch
import scipy

# Global variable for the model  
processor = None
model = None
device = None

# Flask app with CORS
app = flask.Flask(__name__)
CORS(app)

def run_app(
    *,
    checkpoint: str = "facebook/musicgen-small",
    dec: str = "cuda",
    host: str = "127.0.0.1",
    port: int = 3013,
    debug: bool = False,
    ssl_certificate: T.Optional[str] = None,
    ssl_key: T.Optional[str] = None,
):
    
    global processor
    global model
    global device

    processor = AutoProcessor.from_pretrained(checkpoint)

    model = MusicgenForConditionalGeneration.from_pretrained(checkpoint)

    device = dec if torch.cuda.is_available() else "cpu"
    model.to(device)

    # increase the guidance scale to 4.0
    model.generation_config.guidance_scale = 4.0

    # set the max new tokens to 256
    # 1500 - 30s
    model.generation_config.max_new_tokens = 1500

    # set the softmax sampling temperature to 1.5
    model.generation_config.temperature = 1.5


    args = dict(
        debug=debug,
        threaded=False,
        host=host,
        port=port,
    )

    if ssl_certificate:
        assert ssl_key is not None
        args["ssl_context"] = (ssl_certificate, ssl_key)

    app.run(**args)  # type: ignore


@app.route("/run_inference/", methods=["POST"])
def run_inference():
    """
    Execute the model as an API.

    Inputs:
        Serialized JSON of the InferenceInput dataclass

    Returns:
        Serialized JSON of the InferenceOutput dataclass
    """
    start_time = time.time()

    global device
    global model
    global processor

    # logging.info(flask.request.data)
    # Parse the payload as JSON
    json_data = json.loads(flask.request.data)

    # "seed_image_id": "og_beat",
    # seed_image_id == None ,写一个随机选取种子图的方法
    # if "seed_image_id" not in json_data:
    #     json_data["seed_image_id"]= random.choice([
    #         "vibes",
    #         "og_beat",
    #         "motorway",
    #         "mask_top_third_95",
    #         "mask_top_third_75",
    #         "mask_gradient_top_fifth_75",
    #         "mask_gradient_top_70",
    #         "mask_gradient_dark",
    #         "mask_beat_lines_80",
    #         "marim",
    #         "agile"
    #     ])
    
     

    inputs = processor(
        text=json_data['text'],
        padding=True,
        return_tensors="pt",
    )

    audio_values = model.generate(**inputs.to(device), do_sample=True, guidance_scale=3, max_new_tokens=256)

    audio=audio_values[0, 0].cpu().numpy()

    sampling_rate = model.config.audio_encoder.sampling_rate
    scipy.io.wavfile.write("musicgen_out.wav", rate=sampling_rate, data=audio)

    with open("musicgen_out.wav", "rb") as audio_file:
        audio_data = audio_file.read()
        audio_base64 = base64.b64encode(audio_data).decode("utf-8")

    #print(audio_base64)
    # audio_bytes = audio.tobytes()
    # audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

    response =json.dumps({"audio":"data:audio/wav;base64," + audio_base64}) 

 
    return response



if __name__ == "__main__":
    import argh

    argh.dispatch_command(run_app)
