#  Transfer powerpoint into videos with unique sound, with F5-TTS
## demo of this tool
https://github.com/user-attachments/assets/d68b0dd9-5791-4040-831a-1224712ed079

## Installation
### step 1: set up virtual environment
'''
conda create -n f5-tts python=3.10
conda activate f5-tts
'''

### step 2: pip related tools
pip install torch==2.3.0+cu118 torchaudio==2.3.0+cu118 --extra-index-url https://download.pytorch.org/whl/cu118
pip install -r requirements.txt

### Step 3: download this tool and unzip it

### Step 4: entering the folder where you put this tool
cd TTS
pip install -e .

### Backup [If you are not using NVIDIA]:
#AMD:pip install torch==2.5.1+rocm6.2 torchaudio==2.5.1+rocm6.2 --extra-index-url https://download.pytorch.org/whl/rocm6.2
#Intel GPU: pip install torch torchaudio --index-url https://download.pytorch.org/whl/test/xpu
#Apple Silicon: pip install torch torchaudio


