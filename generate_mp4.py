# -*- coding: utf-8 -*-
"""
Created on Mon Nov 25 11:13:34 2024

@author: Lenovo
"""
# -----------------------------------------#
# 项目文件夹都会叫这个名字
project_name = '1.0' 

# ppt的名称，不需要带后缀
ppt = "1.0" 

# 是否需要生成音频
voiceGen = 1 # 1是需要生成音频，0是已经有每页对应的音频，可以直接生成视频

# 是否需要一次性生成所有音频
allVoice = 0 # 1是需要一次性生成所有音频，0是只需要生成指定页面音频
# 1：适合新文件音频的生成，在生成过程中无法打断，但每页平均用时更短，操作无忧。且所有音频生成完后，可以根据音频效果，重新生成指定页面音频；
# 0：适合对已有音频进行微调，操作更自由，但每页平均用时更长;

# 参考音频的名称，不需要带后缀
ref_audio_name = "Ref_wav" 

 # 参考音频对应的文本
ref_text = "各位热爱心理学的小伙伴们，大家好。我叫蒋挺，来自北师大心理学部。从今天开始，我会跟大家分享一些有趣的心理学知识，一起开启体验心理学的奇幻之旅。"

# 如果本页ppt没有备注，默认停留时长（单位：秒）
moren = 2 
# -----------------------------------------#

# import argparse
import contextlib
import wave
import win32com.client
# 如果没有这个包，需要手动下载：pip install -i https://pypi.tuna.tsinghua.edu.cn/simple pypiwin32
import os
import time
import sys
import subprocess
import struct
from pydub import AudioSegment
from moviepy import VideoFileClip, AudioFileClip
# 如果没有这个包，需要手动下载：pip install moviepy
import psutil
# from TTS.src.f5_tts.infer.utils_infer import load_vocoder

# In[程序所需变量]
#-- model related --#
# conda_env_name = 'f5-tts' # 默认使用F5-TTS这个语音生成模型的conda虚拟环境，现在放到.bat文件里了
script_path = r"TTS\src\f5_tts\infer" # 是相对路径，所以本代码必须摆在和TTS同一层的位置
script_name_quan = "infer_cli_quan.py"
script_name_fen = "infer_cli.py"
model_name = 'F5-TTS' # F5-TTS | E2-TTS
# ref_audio = r"Wav/ref_Wav/cheerful.wav" # 参考音频
# ref_text = "各位热爱心理学的小伙伴们，大家好。我叫蒋挺，来自北师大心理学部。从今天开始，我会跟大家分享一些有趣的心理学知识，一起开启体验心理学的奇幻之旅。" # 参考音频对应的文本
#-- .pptx->.bat --#
toml = "Toml" # toml_folder
toml_Folder = f"Toml/{project_name}" # toml文件的项目文件夹
ppt_folder = r"ppt"   # ppt所在的地址
ppt_ori_name = f"{ppt}.pptx" # ppt初始名字
ppt_name = f"{ppt}_generated.pptx" # ppt后来名字
page = 2 # todo:debug时使用
#-- mp4 generation  --#
mp4_Folder = "MP4" # mp4输出的地址
mp4_name = f"{ppt}_ori.MP4" # 中间过程版mp4的名称
mp4_final_name = f"{ppt}.mp4" # 最终版mp4的名称
wav = "Wav" # wav_folder
wav_Folder = f"Wav/{project_name}"     # wav文件的项目文件夹 
shuaxin = 3 # 多少秒播报一次视频生成状态
# moren = 2 # 如果本页ppt没有备注，默认停留时长
#-- 备注txt generation  --#
txt_Folder = "TXT" #txt输出的地址
zimu_name = f"zimu_{ppt}.txt" # txt的名称
jiaoben_name = f"JiaoBen_{ppt}.txt" # txt_NAME

# -- path preparations -- #
ref_audio = f"ref_Wav/{ref_audio_name}.wav"
path_current = os.path.dirname(os.path.realpath(__file__))
ppt_ori_path = os.path.join(path_current, ppt_folder, ppt_ori_name)
ppt_path = os.path.join(path_current, wav_Folder, ppt_name)
mp4_path = os.path.join(path_current,wav_Folder,mp4_name)
mp4_final_path = os.path.join(path_current,mp4_Folder,mp4_final_name)
txt_path = os.path.join(path_current,txt_Folder)
jiaoben_path = os.path.join(txt_path,jiaoben_name)
zimu_path = os.path.join(txt_path,zimu_name)

# In[函数集合]
# -------------------- 设置ppt参数 -------------------- #
def set_powerpoint(powerpoint):
    powerpoint.Visible = True
    powerpoint.WindowState = 1 # minimize ppt
    powerpoint.Left   = 50 # 距离左边缘的像素
    powerpoint.Top    = 50 # 距离上边缘的像素
    powerpoint.Width  = 300 # 宽度
    powerpoint.Height = 200 # 高度
    
    return powerpoint

# -------------------- 关闭ppt -------------------- #
def exit_powerpoint(ppt, powerpoint):
    ppt.Close()
    powerpoint.Quit()
    kill_ffmpeg_process()

# -------------------- 生成指定时长的空白语音 -------------------- #
def generate_silent_wav(file_path,duration,sample_rate = 44100, num_channels = 1, sample_width = 2):
    num_frames = int(sample_rate*duration) # 总采样点数
    silent_frame = struct.pack("<h",0)   # 16位静音样本
    silent_data = silent_frame * num_channels * num_frames
    
    with wave.open(file_path, "w") as wav_file:
        wav_file.setnchannels(num_channels) # 通道数
        wav_file.setsampwidth(sample_width) # 采样宽度
        wav_file.setframerate(sample_rate)  # 采样率
        # 写入静音数据
        wav_file.writeframes(silent_data)
        
# -------------------- 生成语音列表 -------------------- #
def generate_audio_sequence(n):
    audio_files = []
    
    audio_files.append(f"{wav_Folder}/0_guodu.wav")
    
    for i in range(1, n):
        audio_files.append(f"{wav_Folder}/{i}.wav")
        audio_files.append(f"{wav_Folder}/{i}_guodu.wav")
        
    audio_files.append(f"{wav_Folder}/{n}.wav")
    
    return audio_files

# -------------------- 拼接多段语音 -------------------- #
def concatenate_audio(files, output_file):
    combined = AudioSegment.from_file(files[0])
    
    for file in files[1:]:
        audio = AudioSegment.from_file(file)
        combined += audio
        
    combined.export(output_file, format="wav")
    
# -------------------- 拼接视频和音频 -------------------- #
def merge_audio_with_video(video_file, audio_file, output_file):
    video = VideoFileClip(video_file)
    audio = AudioFileClip(audio_file)
    
    try:
        video.audio = audio
        video.write_videofile(output_file, codec="libx264")
    finally:
        video.close()

# -------------------- 确保ffmpeg进程结束 -------------------- #
def kill_ffmpeg_process():
    for proc in psutil.process_iter(['name']):
        if proc.info['name']=='ffmpeg':
            proc.terminate()

# In[检查PPT备注格式]
# -------------------- 检查ppt备注格式，去掉\n -------------------- #
kill_ffmpeg_process()
print("现在开始检查ppt备注……\n")

# 创建文件夹
if not os.path.exists(wav):
    os.mkdir(wav)
if not os.path.exists(wav_Folder):
    os.mkdir(wav_Folder)
if not os.path.exists(txt_Folder):
    os.mkdir(txt_Folder)
if not os.path.exists(mp4_Folder):
    os.mkdir(mp4_Folder)

# open ppt
powerpoint = win32com.client.Dispatch("PowerPoint.Application")
powerpoint = set_powerpoint(powerpoint)
ppt = powerpoint.Presentations.Open(ppt_ori_path)
# exit_powerpoint(ppt, powerpoint)
# time.sleep(2)

# powerpoint = win32com.client.Dispatch("PowerPoint.Application")
# powerpoint = set_powerpoint(powerpoint)
# ppt = powerpoint.Presentations.Open(ppt_ori_path)
# status = 1
# while status:
#     powerpoint = win32com.client.Dispatch("PowerPoint.Application")
#     powerpoint = set_powerpoint(powerpoint)
#     ppt = powerpoint.Presentations.Open(ppt_ori_path)
#     try:
#         notes_text = ppt.Slides(1).NotesPage.Shapes.Placeholders(2).TextFrame.TextRange.Text
#         if notes_text
#         status = 0
#     except:
#         status = 1

# 设置脚本文件
file = open(jiaoben_path, 'a', encoding="utf-8")
file.truncate(0); # 清空txt文件

# 修改每页ppt的备注
for index, slide in enumerate(ppt.Slides):
    if slide.NotesPage.Shapes.Placeholders(2).TextFrame.HasText:
        notes_text = slide.NotesPage.Shapes.Placeholders(2).TextFrame.TextRange.Text
        # 替换各类分隔符为。
        updated_text = notes_text.replace(" ","")
        updated_text = updated_text.replace("\x0b","。")
        updated_text = updated_text.replace("\r","。")
        updated_text = updated_text.replace("。。","。")
        updated_text = updated_text.replace("\n","")
        # 写入脚本文件
        slide_num = f'-{index+1}-\n'
        file.write(slide_num)
        file.write(updated_text)
        file.write('\n')
        # 继续替换分隔符
        updated_text = updated_text.replace("、","，")
        updated_text = updated_text.replace("“","")
        updated_text = updated_text.replace("”","")
        updated_text = updated_text.replace("《","")
        updated_text = updated_text.replace("》","")
        # updated_text = updated_text.replace("！","。")
        # updated_text = updated_text.replace("？","。")
        updated_text = updated_text.replace("——","。")
        updated_text = updated_text.replace("；","，")
        slide.NotesPage.Shapes.Placeholders(2).TextFrame.TextRange.Text = updated_text
    else:
        print(f"第{index+1}页没有备注，为保障音频文件的正常生成，请检查第{index+1}页\n")
file.close()

# 让用户自行判断是否继续
print("ppt备注已检查完毕，如果这行字是你看到的第一行字，那就是一切都好~")
print("-------------------------")
print("如果不是，请按照提示检查对应页PPT")
print("-------------------------")
user_input = input("如果需要调整ppt，请输入 yes ，反之，可以按回车键继续：")
if user_input.lower() == "yes":
    exit_powerpoint(ppt, powerpoint)
    sys.exit(0)
    
# 保存&关闭
ppt.saveAs(ppt_path)

# In[PPT备注导出成.toml文件]    
# -------------------- PPT备注导出成.toml文件 -------------------- #
if voiceGen==0:
    exit_powerpoint(ppt, powerpoint)
else:
    # create toml folder
    if not os.path.exists(toml):
        os.mkdir(toml)
    if not os.path.exists(toml_Folder):
        os.mkdir(toml_Folder)
    
    # 记录ppt页数
    page = 0
    for index, slide in enumerate(ppt.Slides, start=1): 
        # set .toml file
        tomlFileName = f'{index}.toml'
        tomlPathName = os.path.join(toml_Folder,tomlFileName)
        page = page+1
        # 如果之前有.toml文件，则删除
        if os.path.exists(tomlPathName):
            os.remove(tomlPathName)
        # 如果有备注
        if slide.NotesPage.Shapes.Placeholders(2).TextFrame.HasText:
            # 打开.toml文件，写入信息
            file = open(tomlPathName, 'a', encoding="utf-8");
            file.truncate(0); # 清空原始文件
            # model = "F5-TTS"
            # ref_audio = "infer/examples/basic/cheerful.wav"
            # ref_text = "各位热爱心理学的小伙伴们，大家好。我叫蒋挺，来自北师大心理学部。从今天开始，我会跟大家分享一些有趣的心理学知识，一起开启体验心理学的奇幻之旅。"
            # gen_text = "终于成功啦，恭喜自己！"
            # gen_file = ""
            # remove_silence = false
            # output_dir = "tests/chapter01"
            # output_name = "haha.wav"
            file.write(f'model="{model_name}"\n')
            file.write(f'ref_audio = "{ref_audio}"\n')
            file.write(f'ref_text = "{ref_text}"\n')
            file.write('speed = 1.0\n')
            file.write(f'gen_text = "{slide.NotesPage.Shapes.Placeholders(2).TextFrame.TextRange.Text}"\n')
            file.write('gen_file = ""\n')
            file.write('remove_silence = false\n')
            file.write(f'output_dir = "{wav_Folder}"\n')
            file.write(f'output_name = "{index}.wav"\n')
            file.close()
     
    # 生成Prepare.toml
    tomlFileName = "Prepare.toml"
    tomlPathName = os.path.join(toml_Folder,tomlFileName)
    file = open(tomlPathName, 'a', encoding="utf-8");
    file.truncate(0); # 清空原始文件
    file.write(f'model="{model_name}"\n')
    file.write(f'pages = {page}\n')
    file.write(f'toml_Folder = "{toml_Folder}"\n')
    file.write(f'ref_audio = "{ref_audio}"\n')
    file.write(f'ref_text = "{ref_text}"\n')
    file.write('gen_file = ""\n')
    file.write('speed = 1.0\n')
    file.write('remove_silence = false\n')
    file.write(f'output_dir = "{wav_Folder}"\n')
    file.close()

    exit_powerpoint(ppt, powerpoint)

# In[生成音频]
    # -------------------- 生成音频 -------------------- #        
    conda_env_python = r"C:\Users\Lenovo\anaconda3\envs\f5-tts\python.exe"
    
    path_current = os.path.dirname(os.path.realpath(__file__))
    script_path = os.path.join(path_current, script_path)
    script_file_quan = os.path.join(script_path,script_name_quan)
    script_file_fen = os.path.join(script_path,script_name_fen)
    
    if allVoice:
        # 如果需要一次性生成所有页面对应音频
        print("\n")
        print("您已设定一次性生成所有页面对应音频（allVoice = 1）")
        print("如果只需要生成特定页音频，请关闭本页面，打开generate_mp4.py,设置：allVoice=0")
        time.sleep(2)
        print("-------------------------")
        print("正在生成所有页面对应的音频……")
        print("-------------------------")
        
        # 一次性生成所有音频,再让用户选择哪些页面对应的音频需要微调
        toml_path = os.path.join(path_current,f"{toml_Folder}\Prepare.toml")
        command = f"python {script_file_quan} --config {toml_path} --currentpath {path_current} --load_vocoder_from_local"
        subprocess.run(command, shell=True, check=True)

    else:
        # 如果只需要生成某几个页面对应音频，就逐个处理
        print("\n")
        print("您已设定生成特定页音频（allVoice = 0）")
        print("如果需要一次性生成全部音频，请关闭本页面，打开generate_mp4.py,设置：allVoice=1")
        print("-------------------------")
        print("模型准备中……")
        print("-------------------------")
        
        toml_path = os.path.join(path_current,f"{toml_Folder}\Prepare.toml")
        command = f"python {script_file_fen} --config {toml_path} --currentpath {path_current} --load_vocoder_from_local"
        subprocess.run(command, shell=True, check=True)

# In[处理音频和视频]
powerpoint = win32com.client.Dispatch("PowerPoint.Application")
powerpoint = set_powerpoint(powerpoint)
ppt_new = powerpoint.Presentations.Open(ppt_path)

# ppt页数
page = ppt_new.Slides.Count

# --------- 1.0 提取备注为字幕格式 --------- #
file = open(zimu_path, 'a', encoding="utf-8");
file.truncate(0); # 清空txt文件

text_lines = []

# 提取备注，输出为字幕文本格式
for i, slide in enumerate(ppt_new.Slides):
    if slide.NotesPage.Shapes.Placeholders(2).TextFrame.HasText:
        beizhu_tmp = slide.NotesPage.Shapes.Placeholders(2).TextFrame.TextRange.Text
        beizhu_tmp = beizhu_tmp.replace("。”","\n")
        beizhu_tmp = beizhu_tmp.replace("，”","\n")
        beizhu_tmp = beizhu_tmp.replace("。","\n")
        beizhu_tmp = beizhu_tmp.replace("，","\n")
        if beizhu_tmp.endswith("\n"):
            beizhu_tmp = beizhu_tmp.rstrip("\n")
        file.write(beizhu_tmp)
        file.write("\n")
        text_lines = text_lines + beizhu_tmp.split('\n')

file.close()

# --------- 2.0 设置ppt停留时间，并根据过渡动画时间生成过渡音频 --------- #

# 载入音频时长，并调整ppt停留时长
print("\n-------------------------")
print("每页ppt的停留和过渡时长如下：")
for i, slide in enumerate(ppt_new.Slides):
    # 设置过渡音频path
    guodu_name = f"{i}_guodu.wav"
    guodu_file = os.path.join(wav_Folder, guodu_name)
    # 根据是否有过渡动画，设置过渡音频
    entry_effect = slide.SlideShowTransition.EntryEffect
    if entry_effect != 0: # 0就是没有过渡动画
        guodu = slide.SlideShowTransition.Duration    # 记录过渡效果的持续时间
        generate_silent_wav(guodu_file, duration=guodu)
        print(f"第{i}页和下一页间的过渡动画时长为：{guodu}秒")
    else:
        generate_silent_wav(guodu_file,duration = 0)
    
    # 设置音频path
    wav_name = f"{i+1}.wav"
    wav_file = os.path.join(wav_Folder, wav_name)
    # 载入音频时长
    if os.path.exists(wav_file):
        with contextlib.closing(wave.open(wav_file,'r')) as f:
            frames = f.getnframes()
            rate = f.getframerate()
            wav_len = frames / float(rate)
            slide_durations = wav_len # 确定slide停留秒数，默认停留0秒
        print(f"第{i+1}页pp将停留：：{slide_durations}秒")
    else:
        slide_durations = moren # 默认停留时长
        generate_silent_wav(wav_file,duration=moren) # 没有备注的页面，生成默认停留时长的音频
        print(f"第{i+1}页PPT没有对应的.wav文件，默认停留时长为{moren}秒")
        
    # 设置每页PPT的停留时长
    slide.SlideShowTransition.AdvanceOnTime = True # 启用计时
    slide.SlideShowTransition.AdvanceTime = slide_durations # 设置每一页的总停留时间（包括动画时间）    
    
ppt_new.save()

# --------- 3.0 导出视频 --------- #    
# 导出视频
kill_ffmpeg_process()
if os.path.exists(mp4_path):
    print(f"\n已有同名视频，将重新生成视频：{mp4_path}")
    user_input = input("输入 yes 则继续，直接输入回车键则退出：")
    if user_input.lower() == "yes":
        os.remove(mp4_path)
        ppt_new.CreateVideo(mp4_path, UseTimingsAndNarrations=True, VertResolution=1080, FramesPerSecond=30, Quality=100)
    else:
        exit_powerpoint(ppt_new, powerpoint)
        sys.exit(0)
else:
    ppt_new.CreateVideo(mp4_path, UseTimingsAndNarrations=True, VertResolution=1080, FramesPerSecond=30, Quality=100)

# 等待视频导出
print(f"……正在导出视频至：{mp4_path}")
while True:
    time.sleep(shuaxin)
    file_size = os.path.getsize(mp4_path)
    if file_size != 0:
        print(f"Video export finished: {mp4_path}")
        break
    else:
        print(f"……正在导出视频至：{mp4_path}")
    
exit_powerpoint(ppt_new, powerpoint)

# --------- 4.0 拼接音频 --------- #  
audio_files = generate_audio_sequence(page)
con_file = f"{wav_Folder}/combined.wav"
concatenate_audio(audio_files, con_file)

# --------- 5.0 拼接音频与视频 --------- #  
merge_audio_with_video(mp4_path, con_file, mp4_final_path)
kill_ffmpeg_process()

