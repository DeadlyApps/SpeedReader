# SpeedReader
Python based tool to use text to speech to read books or study material quickly.

# History
In college my now father in law was using a text to speech program and talking about how he can listen to books at 500 WPM and recommended it to me. It was a pivotal point in my education because I realized I could listen & read a document at 500 words per minute and internalize the information. I began to receive better grades and was able to get ‘A’ letter grades on tests composed of 3 months of materials by listening for 2 hours. I later wrote a speed reader for myself that I used for 10 years and now I felt like it was time to write an updated version in python. I suggest trying it at low speeds first, then increasing the speed as you feel comfortable. Start at 200, and increment by 25 each time you use it until you find that your level of understanding is decreasing then take it slower till you reach 500 WPM. 

I believe if you are an auditory learning this tool can be massively helpful to you.

# Setup
## Run Locally Setup
Tested with Python 3.7

install requirements.txt
pyttsx3==2.71 due to a bug detailed here: https://github.com/nateshmbhat/pyttsx3/issues/78

## Convert to EXE
Py2exe needs to be updated manually to fix this bug: https://github.com/pyinstaller/pyinstaller/issues/3268

pyinstaller --clean --onefile --windowed SpeedReader.spec
