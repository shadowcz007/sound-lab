"""
Flask server that serves the riffusion model as an API.
"""
 
import json,hashlib
 
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
from PIL import Image

import torch
from accelerate import Accelerator
from transformers import AutoProcessor, MusicgenForConditionalGeneration
from diffusers import StableDiffusionPanoramaPipeline, DDIMScheduler, StableDiffusionPipeline



# from accelerate.utils import write_basic_config
# write_basic_config(mixed_precision='fp16')


def init_audio_model(checkpoint):
    global audio_processor
    global audio_model
    global device

    audio_processor = AutoProcessor.from_pretrained(checkpoint)

    audio_model = MusicgenForConditionalGeneration.from_pretrained(checkpoint)

    # audio_model.to(device)
    audio_model = audio_model.to(torch.device('cpu'))

    # increase the guidance scale to 4.0
    audio_model.generation_config.guidance_scale = 4.0

    # set the max new tokens to 256
    # 1500 - 30s
    audio_model.generation_config.max_new_tokens = 1500

    # set the softmax sampling temperature to 1.5
    audio_model.generation_config.temperature = 1.5


def init_sd_model(model_ckpt,dec="cuda"):
    global sd_model
    global device

    # sd_model = StableDiffusionPanoramaPipeline.from_pretrained(
    #     model_ckpt, 
    #     scheduler=DDIMScheduler.from_pretrained(model_ckpt, subfolder="scheduler"), 
    #     torch_dtype=torch.float16
    # )

    sd_model = StableDiffusionPipeline.from_pretrained(model_ckpt, torch_dtype=torch.float16)

    # sd_model = sd_model.to(torch.device('cpu'))
    sd_model = sd_model.to(device)

def get_save_file_path(text,file_name):

    if os.path.exists('output')==False:
        os.mkdir('output')

    directory='output/'+get_id(text)
    if os.path.exists(directory):
        print("Directory exists")
    else:
        os.mkdir(directory)
        print("Directory does not exist")

    return os.path.join(directory,file_name)


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


def image_to_base64(image, fmt='png') -> str:
    output_buffer = io.BytesIO()
    image.save(output_buffer, format=fmt)
    byte_data = output_buffer.getvalue()
    base64_str = base64.b64encode(byte_data).decode('utf-8')
    return f'data:image/{fmt};base64,' + base64_str

def get_id(text):
    encoded_text = text.encode('utf-8')
    id=hashlib.md5(encoded_text).hexdigest()
    return id

def text_to_audio(text,duration,guidance_scale=3.1):
    global audio_processor
    global audio_model
    # global device

    id=get_id(text)

    device='cpu'

    # audio_model = audio_model.to(torch.device(device))

    inputs = audio_processor(
            text=text,
            # audio=audio,
            # sampling_rate=sampling_rate,
            padding=True,
            return_tensors="pt",
        )

    max_tokens=256 #default=5, le=30
    if duration:
        max_tokens=int(duration*50)
    # print(max_tokens)
    # audio_length_in_s = 256 / sampling_rate

    sampling_rate = audio_model.config.audio_encoder.sampling_rate
    # input_audio
    audio_values = audio_model.generate(**inputs.to(device), 
    do_sample=True, 
    guidance_scale=guidance_scale, 
    max_new_tokens=max_tokens,
    )
    audio=audio_values[0, 0].cpu().numpy()

    output_file=get_save_file_path(text,"_musicgen_out.wav")

    # input_audio   
    wavfile.write(output_file, rate=sampling_rate, data=audio)

    with open(output_file, "rb") as audio_file:
        audio_data = audio_file.read()
        audio_base64 = base64.b64encode(audio_data).decode("utf-8")

    # audio_model = audio_model.to(torch.device('cpu'))
    
    return {
        "output_file":output_file,
        "base64":f'data:audio/wav;base64,'+audio_base64
        }


def callback(step, timestep, latents):
    # 在每个步骤结束时调用的回调函数
    # 这里是一个简单的示例，打印当前步骤和时间步数
    print(f"Step: {step}, Timestep: {timestep}")


def text_to_img(text,num_images_per_prompt=1):
    global sd_model
    global device
    
    # sd_model = sd_model.to(torch.device(device))

    # images = sd_model(
    #     prompt=text,
    #     num_images_per_prompt=num_images_per_prompt,
    #     num_inference_steps=20,
    #     callback_steps=5,
    #     callback=callback
    #     ).images
    
    images = sd_model(
        prompt=text,
        num_images_per_prompt=num_images_per_prompt,
        num_inference_steps=20,
        callback_steps=5,
        callback=callback
        ).images
    
    im_files=[]
    for index, im in enumerate(images):
        f=get_save_file_path(text,"_image"+str(index)+".png")
        im.save(f)

        image = Image.open(f)
        image_base64 = image_to_base64(image,'png')
        
        im_files.append({
            "output_file":f,
            "base64":image_base64
        })

    # sd_model = sd_model.to(torch.device('cpu'))

    return im_files


# Global variable for the model  
audio_processor = None
audio_model = None
sd_model = None
device=None

# Flask app with CORS
app = flask.Flask(__name__)
CORS(app)

# 获取当前脚本文件的路径
current_path = os.path.dirname(os.path.abspath(__file__))
# 构建文件路径
musicgen_model_path =os.path.abspath(os.path.join(current_path, "..", "model", "musicgen-small"))

sd_model_path =os.path.abspath(os.path.join(current_path, "..", "model", "sd-1.5-deliberate_v2"))


def run_app(
    *,
    dec:str='cuda',
    host: str = "127.0.0.1",
    port: int = 3013,
    debug: bool = False,
    ssl_certificate: T.Optional[str] = None,
    ssl_key: T.Optional[str] = None,
):

    global device
    # device = accelerator.device
    device = dec if torch.cuda.is_available() else "cpu"
    init_audio_model(musicgen_model_path)
    init_sd_model(sd_model_path)

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

    global audio_model
    global audio_processor

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

    

    prompt=""
    if 'prompt' in json_data:
        prompt=json_data['prompt']

    title=''
    if 'title' in json_data:
        title=json_data['title']

    num_images_per_prompt=3
    if 'num_images_per_prompt' in json_data:
        num_images_per_prompt=json_data['num_images_per_prompt']

    temperature=1
    if 'temperature' in json_data:
        temperature=json_data['temperature']

    seed=-1
    if 'seed' in json_data:
        seed=json_data['seed']

    guidance_scale=3.1
    if 'guidance_scale' in json_data:
        guidance_scale=json_data['guidance_scale']

    # audio=[]
    # if 'audio' in json_data:
    #     bs=json_data['audio']
        
    #     for b in bs:
    #         if 'url' in b:
    #             base64_string=b['url']
    #         else:
    #             base64_string=b
            
    #         base64_string = base64_string.split(",")[1]

    #         #格式
    #         audio_format = get_audio_format(base64_string)
    #         print(audio_format)
    #         if audio_format!='wav':
    #             audio_mono=convert_to_wav(base64_string)
    #         else:
    #             audio_mono = base64_audio_to_numpy(base64_string)
            
    #         s=audio_mono[: len(audio_mono) // (2*len(bs))]
    #         # print(s.shape)
    #         audio.append(s)
    
    
    # if len(audio)>0:
    #     inputs = audio_processor(
    #         text=text,
    #         audio=audio,
    #         sampling_rate=sampling_rate,
    #         padding=True,
    #         return_tensors="pt",
    #     )
    # else:
    
    audio=text_to_audio(prompt,json_data['duration'])

    images=text_to_img(prompt,num_images_per_prompt=num_images_per_prompt)
    
    # audio_length_in_s = 256 / sampling_rate

    #print(audio_base64)
    # audio_bytes = audio.tobytes()
    # audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

    response =json.dumps({"audio":audio,"images":images,"prompt":prompt,"title":title}) 

    return response



if __name__ == "__main__":
    import argh

    argh.dispatch_command(run_app)
