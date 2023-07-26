"""
Flask server that serves the riffusion model as an API.
"""
 
import json
 
import time
import typing as T
from pathlib import Path

import flask
 
from flask_cors import CORS

import random,io,os
import base64
import numpy as np
from scipy.io import wavfile
from pydub import AudioSegment
from pydub.utils import mediainfo

from transformers import AutoProcessor, MusicgenForConditionalGeneration
import torch

def get_audio_format(base64_audio):
    audio_bytes = base64.b64decode(base64_audio)
    with open("temp_audio_file", "wb") as file:
        file.write(audio_bytes)
    audio_info = mediainfo("temp_audio_file")
    audio_format = audio_info["codec_name"]
    os.remove("temp_audio_file")
    return audio_format

def convert_to_wav(mp3_base64_audio):
    audio_bytes = base64.b64decode(mp3_base64_audio)
    mp3_path="temp_mp3_audio_file"
    wav_path="temp_wav_audio_file"
    with open(mp3_path, "wb") as file:
        file.write(audio_bytes)
    audio = AudioSegment.from_mp3(mp3_path)
    audio.export(wav_path, format="wav")

    sample_rate, audio_data = wavfile.read(wav_path)
    # print(audio_data.ndim)
    if audio_data.ndim > 1:
        audio_data = audio_data[:, 0]  # 只取左声道，即单通道
    # print(audio_data)
    # audio_data = audio_data.astype(np.float32) / 32767.0  # 归一化到[-1.0, 1.0]范围
    os.remove(mp3_path)
    os.remove(wav_path)
    return audio_data


def base64_audio_to_numpy(base64_audio):
    audio_bytes = base64.b64decode(base64_audio)
    audio_io = io.BytesIO(audio_bytes)
    print(audio_io)
    sample_rate, audio_data = wavfile.read(audio_io)
    print(audio_data.ndim)
    if audio_data.ndim > 1:
        audio_data = audio_data[:, 0]  # 只取左声道，即单通道
    print(audio_data)
    # audio_data = audio_data.astype(np.float32) / 32767.0  # 归一化到[-1.0, 1.0]范围
    
    return audio_data



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


    print(model.config.audio_encoder.sampling_rate)


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

    sampling_rate = model.config.audio_encoder.sampling_rate


    text=[]
    if 'text' in json_data:
        text=json_data['text']

    audio=[]
    if 'audio' in json_data:
        bs=json_data['audio']
        
        for b in bs:
            if 'url' in b:
                base64_string=b['url']
            else:
                base64_string=b
            
            base64_string = base64_string.split(",")[1]

            #格式
            audio_format = get_audio_format(base64_string)
            print(audio_format)
            if audio_format!='wav':
                audio_mono=convert_to_wav(base64_string)
            else:
                audio_mono = base64_audio_to_numpy(base64_string)
            
            s=audio_mono[: len(audio_mono) // (2*len(bs))]
            # print(s.shape)
            audio.append(s)
    
    
    if len(audio)>0:
        inputs = processor(
            text=text,
            audio=audio,
            sampling_rate=sampling_rate,
            padding=True,
            return_tensors="pt",
        )
    else:
        inputs = processor(
            text=text,
            # audio=audio,
            # sampling_rate=sampling_rate,
            padding=True,
            return_tensors="pt",
        )

    max_tokens=256 #default=5, le=30
    if 'duration' in json_data:
        max_tokens=int(json_data['duration']*50)
    print(max_tokens,sampling_rate)
    # audio_length_in_s = 256 / sampling_rate


    temperature=1
    if 'temperature' in json_data:
        temperature=json_data['temperature']

    seed=-1
    if 'seed' in json_data:
        seed=json_data['seed']

    guidance_scale=3.1
    if 'guidance_scale' in json_data:
        guidance_scale=json_data['guidance_scale']

    # input_audio

    audio_values = model.generate(**inputs.to(device), 
    do_sample=True, 
    guidance_scale=guidance_scale, 
    max_new_tokens=max_tokens,
    )

    audio=audio_values[0, 0].cpu().numpy()

    
    wavfile.write("musicgen_out.wav", rate=sampling_rate, data=audio)

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
