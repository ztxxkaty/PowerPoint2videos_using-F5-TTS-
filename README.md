#  Transfer powerpoint into videos with unique sound, with F5-TTS

## demo of this tool
https://github.com/user-attachments/assets/d68b0dd9-5791-4040-831a-1224712ed079

## Installation

### step 1: Create a virtual environment using conda and pip related tools
```bash
# Create conda env
conda create -n f5-tts python=3.10
```
```bash
# Activate conda env
conda activate f5-tts
```
```bash
# Install Pytorch for NVIDIA GPU, if you are using other devices, please refer to the "Backup" part
pip install torch==2.3.0+cu118 torchaudio==2.3.0+cu118 --extra-index-url https://download.pytorch.org/whl/cu118
```
```bash
# Install related packages
pip install -r requirements.txt
```

### Step 2: Download this tool and unzip it, and then enter the folder to download model-related packages
```bash
# enter the model folder
cd TTS
```
```bash
# Install model-related packages
pip install -e .
```
### Step 3: Download pre-trained model and put it in the target folder:
Download from https://huggingface.co/SWivid/F5-TTS/tree/main/F5TTS_Base
```
model_1200000.safetensors
```
The target folder is:
```
TTS/ckpts/F5TTS_Base
```
or you can search "Put_Model_Here" in the tool folder to find the place to put model~
### Step 4: Change the content of run.bat
replace the directory of activate.bat with your own path
```bash
CALL "C:\Users\%USERNAME%\anaconda3\Scripts\activate.bat" f5-tts
```
You can find the path by searching "activate.bat" in your computer
### Step 5: Check out below information in "generate_mp4.py" and change them to meet your own requirements
```
generate_mp4.py
```
![generate_mp4](https://github.com/user-attachments/assets/4d70f9d8-5f0d-4c21-ad4e-a5600b200ea6)

### Finally: run the "run.bat"
```
click the run.bat
```

--------------------------
Backup [ If you are not using NVIDIA ]:
```bash
#AMD:
pip install torch==2.5.1+rocm6.2 torchaudio==2.5.1+rocm6.2 --extra-index-url https://download.pytorch.org/whl/rocm6.2
#Intel GPU:
pip install torch torchaudio --index-url https://download.pytorch.org/whl/test/xpu
#Apple Silicon:
pip install torch torchaudio
```

# Acknowledgements

- [F5-TTS](https://github.com/SWivid/F5-TTS) wonderful job, especially in the field of voice clone
  - @article{chen-etal-2024-f5tts,
      title={F5-TTS: A Fairytaler that Fakes Fluent and Faithful Speech with Flow Matching}, 
      author={Yushen Chen and Zhikang Niu and Ziyang Ma and Keqi Deng and Chunhui Wang and Jian Zhao and Kai Yu and Xie Chen},
      journal={arXiv preprint arXiv:2410.06885},
      year={2024}}


