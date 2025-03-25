import os
from datetime import datetime

f = os.path.dirname(os.path.realpath(__file__))
f2 = os.path.dirname(f)
f3 = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../../.."))
current_time = datetime.now()
hms = f"{current_time.hour:02d}{current_time.minute:02d}{current_time.second:02d}"

print(f)
print(f2)
print(f3)
print(hms)