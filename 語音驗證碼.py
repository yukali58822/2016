import sounddevice as sd
import scipy.io.wavfile
import speech_recognition as sr


def recognize_audio(file_path="temp.wav"):
    r = sr.Recognizer()
    with sr.AudioFile(file_path) as source:
        audio = r.record(source)

    try:
        text = r.recognize_google(audio, language="zh-TW")  # 使用 Google Web Speech API，繁體中文
        return text
    except sr.UnknownValueError:
        print("無法辨識語音內容")
        return ""
    except sr.RequestError as e:
        print(f"無法連線到 Google API: {e}")
        return ""


def record_audio_from_virtual_cable(duration=5, fs=44100, device_name_keyword="CABLE", output_file="temp.wav"):
    # 列出所有裝置，找出符合VB-Audio Cable的裝置index
    devices = sd.query_devices()
    input_device_index = None
    for i, dev in enumerate(devices):
        if device_name_keyword.lower() in dev['name'].lower() and dev['max_input_channels'] > 0:
            input_device_index = i
            print(f"找到輸入裝置: {dev['name']}，index={i}")
            break
    if input_device_index is None:
        raise RuntimeError(f"找不到含有'{device_name_keyword}'且可輸入的音訊裝置")

    sd.default.device = (None, input_device_index)  # 設定輸入裝置
    audio = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
    sd.wait()
    scipy.io.wavfile.write(output_file, fs, audio)

    return recognize_audio(output_file)

