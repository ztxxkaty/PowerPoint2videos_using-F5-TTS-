import argparse
import codecs
import os
import re
from datetime import datetime
from importlib.resources import files
from pathlib import Path

import numpy as np
import soundfile as sf
import tomli
from cached_path import cached_path
from omegaconf import OmegaConf

from f5_tts.infer.utils_infer import (
    mel_spec_type,
    target_rms,
    cross_fade_duration,
    nfe_step,
    cfg_strength,
    sway_sampling_coef,
    speed,
    fix_duration,
    infer_process,
    load_model,
    load_vocoder,
    preprocess_ref_audio_text,
    remove_silence_for_generated_wav,
)
from f5_tts.model import DiT, UNetT

# 载入固定参数
parser = argparse.ArgumentParser(
    prog="python3 infer-cli.py",
    description="Commandline interface for E2/F5 TTS with Advanced Batch Processing.",
    epilog="Specify options above to override one or more settings from config.",
)
parser.add_argument(
    "-c",
    "--config",
    type=str,
    # default=os.path.join(files("f5_tts").joinpath("infer/examples/basic"), "basic.toml"),
    # default = "D:\\Project_ppt2video2025\\一键实现PPT--MP4_4.0\\Toml/1.0\\Prepare.toml",
    # default = "D:/Project_ppt2video2025/一键实现PPT--MP4_4.0/Toml/1.0/Prepare.toml",
    help="The configuration file, default see infer/examples/basic/basic.toml",
)
parser.add_argument(
    "-cp",
    "--currentpath",
    # default = os.path.dirname(os.path.realpath(__file__)),
    # default = "D:/Project_ppt2video2025/一键实现PPT--MP4_4.0",
    help="current path of the folder",
)
parser.add_argument(
    "-m",
    "--model",
    type=str,
    help="The model name: F5-TTS | E2-TTS",
)
parser.add_argument(
    "-mc",
    "--model_cfg",
    type=str,
    help="The path to F5-TTS model config file .yaml",
)
parser.add_argument(
    "-p",
    "--ckpt_file",
    type=str,
    help="The path to model checkpoint .pt, leave blank to use default",
)
parser.add_argument(
    "-v",
    "--vocab_file",
    type=str,
    help="The path to vocab file .txt, leave blank to use default",
)
parser.add_argument("-r", "--ref_audio", type=str, help="Reference audio file < 15 seconds.")
parser.add_argument("-s", "--ref_text", type=str, default="666", help="Subtitle for the reference audio.")
# parser.add_argument(
#     "-f",
#     "--gen_file",
#     type=str,
#     help="The file with text to generate, will ignore --gen_text",
# )
# parser.add_argument(
#     "--save_chunk",
#     action="store_true",
#     help="To save each audio chunks during inference",
# )
parser.add_argument(
    "--remove_silence",
    action="store_true",
    help="To remove long silence found in ouput",
)
parser.add_argument(
    "--load_vocoder_from_local",
    action="store_true",
    default = True,
    help="To load vocoder from local dir, default to ../checkpoints/vocos-mel-24khz",
)
parser.add_argument(
    "--vocoder_name",
    type=str,
    choices=["vocos", "bigvgan"],
    help=f"Used vocoder name: vocos | bigvgan, default {mel_spec_type}",
)
parser.add_argument(
    "--target_rms",
    type=float,
    help=f"Target output speech loudness normalization value, default {target_rms}",
)
parser.add_argument(
    "--cross_fade_duration",
    type=float,
    help=f"Duration of cross-fade between audio segments in seconds, default {cross_fade_duration}",
)
parser.add_argument(
    "--nfe_step",
    type=int,
    help=f"The number of function evaluation (denoising steps), default {nfe_step}",
)
parser.add_argument(
    "--cfg_strength",
    type=float,
    help=f"Classifier-free guidance strength, default {cfg_strength}",
)
parser.add_argument(
    "--sway_sampling_coef",
    type=float,
    help=f"Sway Sampling coefficient, default {sway_sampling_coef}",
)
parser.add_argument(
    "--speed",
    type=float,
    help=f"The speed of the generated audio, default {speed}",
)
parser.add_argument(
    "--fix_duration",
    type=float,
    help=f"Fix the total duration (ref and gen audios) in seconds, default {fix_duration}",
)
parser.add_argument(
    "-t",
    "--gen_text",
    type=str,
    help="Text to generate.",
)
parser.add_argument(
    "-o",
    "--output_dir",
    type=str,
    help="The path to output folder",
)
parser.add_argument(
    "-w",
    "--output_name",
    # default="infer_cli_out.wav",
    type=str,
    help="The name of output file",
)
parser.add_argument(
    "-toml",
    "--toml_Folder",
    # default = os.path.join(files("f5_tts").joinpath("infer/examples/basic")),
    type=str,
    help="the folder contains toml",
)


args = parser.parse_args()
config = tomli.load(open(args.config, "rb"))

curr_path  = args.currentpath if args.currentpath else config["currentpath"]
toml_Folder = args.toml_Folder if args.toml_Folder else config["toml_Folder"]
ref_audio = args.ref_audio if args.ref_audio else config["ref_audio"]
ref_audio = f"{curr_path}/{ref_audio}"
ref_text = args.ref_text if args.ref_text != "666" else config["ref_text"]


if ref_text == "666":
    print("!! ref_text is missing !!")
    user_input = input("建议补充完ref_text后重新生成")


model = args.model or config.get("model", "F5-TTS")
model_cfg = args.model_cfg or config.get("model_cfg", str(files("f5_tts").joinpath("configs/F5TTS_Base_train.yaml")))
ckpt_file = args.ckpt_file or config.get("ckpt_file", "")
vocab_file = args.vocab_file or config.get("vocab_file", "")

# patches for pip pkg user
if "infer/examples/" in ref_audio:
    ref_audio = os.path.join(curr_path,f"{ref_audio}")
if "voices" in config:
    for voice in config["voices"]:
        voice_ref_audio = config["voices"][voice]["ref_audio"]
        if "infer/examples/" in voice_ref_audio:
            config["voices"][voice]["ref_audio"] = os.path.join(curr_path,f"{voice_ref_audio}")

output_dir = args.output_dir if args.output_dir else config["output_dir"]
remove_silence = args.remove_silence or config.get("remove_silence", False)
load_vocoder_from_local = args.load_vocoder_from_local or config.get("load_vocoder_from_local", False)

vocoder_name = args.vocoder_name or config.get("vocoder_name", mel_spec_type)
target_rms = args.target_rms or config.get("target_rms", target_rms)
cross_fade_duration = args.cross_fade_duration or config.get("cross_fade_duration", cross_fade_duration)
nfe_step = args.nfe_step or config.get("nfe_step", nfe_step)
cfg_strength = args.cfg_strength or config.get("cfg_strength", cfg_strength)
sway_sampling_coef = args.sway_sampling_coef or config.get("sway_sampling_coef", sway_sampling_coef)
speed = args.speed or config.get("speed", speed)
fix_duration = args.fix_duration or config.get("fix_duration", fix_duration)

# load vocoder
if vocoder_name == "vocos":
    # vocoder_local_path = "../checkpoints/vocos-mel-24khz"
    vocoder_local_path = os.path.join(curr_path, r"TTS\src\f5_tts\infer\vocos-mel-24khz")
    # vocoder_local_path = "vocos-mel-24khz"
elif vocoder_name == "bigvgan":
    vocoder_local_path = "../checkpoints/bigvgan_v2_24khz_100band_256x"

vocoder = load_vocoder(vocoder_name=vocoder_name, is_local=load_vocoder_from_local, local_path=vocoder_local_path)


# load TTS model

if model == "F5-TTS":
    model_cls = DiT
    model_cfg = OmegaConf.load(model_cfg).model.arch
    if not ckpt_file:  # path not specified, download from repo
        if vocoder_name == "vocos":
            repo_name = "F5-TTS"
            exp_name = "F5TTS_Base"
            ckpt_step = 1200000
            ckpt_file = str(cached_path(f"hf://SWivid/{repo_name}/{exp_name}/model_{ckpt_step}.safetensors"))
            # ckpt_file = f"ckpts/{exp_name}/model_{ckpt_step}.pt"  # .pt | .safetensors; local path
        elif vocoder_name == "bigvgan":
            repo_name = "F5-TTS"
            exp_name = "F5TTS_Base_bigvgan"
            ckpt_step = 1250000
            ckpt_file = str(cached_path(f"hf://SWivid/{repo_name}/{exp_name}/model_{ckpt_step}.pt"))

elif model == "E2-TTS":
    assert args.model_cfg is None, "E2-TTS does not support custom model_cfg yet"
    assert vocoder_name == "vocos", "E2-TTS only supports vocoder vocos yet"
    model_cls = UNetT
    model_cfg = dict(dim=1024, depth=24, heads=16, ff_mult=4)
    if not ckpt_file:  # path not specified, download from repo
        repo_name = "E2-TTS"
        exp_name = "E2TTS_Base"
        ckpt_step = 1200000
        ckpt_file = str(cached_path(f"hf://SWivid/{repo_name}/{exp_name}/model_{ckpt_step}.safetensors"))
        # ckpt_file = f"ckpts/{exp_name}/model_{ckpt_step}.pt"  # .pt | .safetensors; local path

print(f"Using {model}...")
ema_model = load_model(model_cls, model_cfg, ckpt_file, mel_spec_type=vocoder_name, vocab_file=vocab_file)


# inference process
def main_process(ref_audio, ref_text, gen_text, remove_silence, speed,  wave_path):

    main_voice = {"ref_audio": ref_audio, "ref_text": ref_text}
    if "voices" not in config:
        voices = {"main": main_voice}
    else:
        voices = config["voices"]
        voices["main"] = main_voice
    for voice in voices:
        print("Voice:", voice)
        print("ref_audio ", voices[voice]["ref_audio"])
        voices[voice]["ref_audio"], voices[voice]["ref_text"] = preprocess_ref_audio_text(
            voices[voice]["ref_audio"], voices[voice]["ref_text"]
        )
        print("ref_audio_", voices[voice]["ref_audio"], "\n\n")

    generated_audio_segments = []
    reg1 = r"(?=\[\w+\])"
    chunks = re.split(reg1, gen_text)
    reg2 = r"\[(\w+)\]"
    for text in chunks:
        if not text.strip():
            continue
        match = re.match(reg2, text)
        if match:
            voice = match[1]
        else:
            print("No voice tag found, using main.")
            voice = "main"
        if voice not in voices:
            print(f"Voice {voice} not found, using main.")
            voice = "main"
        text = re.sub(reg2, "", text)
        ref_audio_ = voices[voice]["ref_audio"]
        ref_text_ = voices[voice]["ref_text"]
        gen_text_ = text.strip()
        print(f"Voice: {voice}")
        audio_segment, final_sample_rate, spectragram = infer_process(
            ref_audio_,
            ref_text_,
            gen_text_,
            ema_model,
            vocoder,
            mel_spec_type=vocoder_name,
            target_rms=target_rms,
            cross_fade_duration=cross_fade_duration,
            nfe_step=nfe_step,
            cfg_strength=cfg_strength,
            sway_sampling_coef=sway_sampling_coef,
            speed=speed,
            fix_duration=fix_duration,
        )
        generated_audio_segments.append(audio_segment)

    if generated_audio_segments:
        final_wave = np.concatenate(generated_audio_segments)
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(wave_path, "wb") as f:
            sf.write(f.name, final_wave, final_sample_rate)
            # Remove silence
            if remove_silence:
                remove_silence_for_generated_wav(f.name)
            print(f.name)

    if generated_audio_segments:
        final_wave = np.concatenate(generated_audio_segments)

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(wave_path, "wb") as f:
            sf.write(f.name, final_wave, final_sample_rate)
            # Remove silence
            if remove_silence:
                remove_silence_for_generated_wav(f.name)
            print(f.name)

def main():   
    while True:
        print("-------------------------")
        user_input = input("如果有不满意的音频，请输入其序号，如：1\n如果对所有音频都满意，请输入任意字母，如n：")
        try:
            number = int(user_input)
            # toml_name = f"{curr_path}/{toml_Folder}/{number}.toml"
            toml_name = f"{curr_path}/{toml_Folder}/{number}.toml"
            if os.path.exists(toml_name):
                config = tomli.load(open(toml_name, "rb"))
                gen_text = args.gen_text if args.gen_text else config["gen_text"]
                gen_text = gen_text + '啊。'
                output_name = args.output_name if args.output_name else config["output_name"]
                wave_path = f"{curr_path}/{output_dir}/{number}_adjusted.wav"  #parameter
                
                print("-------------------------")
                print(f"现在正在重新生成第{number}页音频……")
                # check begins
                # print(f"toml_path:{toml_name}")
                # print(f"wave_path:{wave_path}")
                # print(f"ref_audio:{ref_audio}")
                # print(f"ref_text:{ref_text}")
                # check end
                main_process(ref_audio, ref_text, gen_text, remove_silence, speed, wave_path)
                
                print(f"第{number}页音频已生成\n")
            else:
                print(f"tomal:name{toml_name}")
                print("请确保您输入的序号是在已生成音频范围内的\n")
        except ValueError:
            print("-------------------------")
            user_input = input("您没有输入序号，如果确认音频都已满意，请输入yes，直接输入回车键则继续调试：")
            if user_input.lower() == "yes":
                break


if __name__ == "__main__":
    main()
