from flask import Flask, jsonify, render_template, Response
import cv2
from mediapipe import solutions as mp
import math
import numpy as np
import subprocess

app = Flask(__name__)

recording = False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/flip_recording')
def record():
    global recording
    if(recording):
        recording = False
        return 'Recording stopped'
    else : 
        recording = True
        return 'Recording started'
    
def set_volume(vol):
    """Set system volume using pactl."""
    volume = int(vol)
    subprocess.call(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{volume}%"])

def model(img, hands):

    results = hands.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

    if results.multi_hand_landmarks :
        for hand in results.multi_hand_landmarks :
            coList = []
            for id, co in enumerate(hand.landmark) :
                h, w, c = img.shape
                #print(id, co )
                cx, cy = (int)(co.x*w), (int)(co.y*h)
                coList.append([id, cx, cy])
                #print(coList)
                
            if coList :
                x1, y1 = coList[4][1], coList[4][2]
                x2, y2 = coList[8][1], coList[8][2]
                cv2.circle(img, (x1,y1), 10, (255,0,0), cv2.FILLED)
                cv2.circle(img, (x2,y2), 10, (255,0,0), cv2.FILLED)
                cv2.line(img, (x1,y1), (x2, y2), (255,0,255),3 )
                length = math.hypot(x2-x1,y2-y1)
                vol = np.interp(length,[50,150])
                set_volume(vol)
                # volume.SetMasterVolumeLevel(vol, None)
                volBar = np.interp(length, [50,150], [400,150])
                volPer = np.interp(length,[50,150],[0,100])
                cv2.rectangle(img,(50,150),(85,400),(123,213,122),3)
                cv2.rectangle(img,(50,int(volBar)), (85,400), (122,12,122), cv2.FILLED )
                cv2.putText(img,str(int(volPer)), (40,450), cv2.FONT_HERSHEY_PLAIN, 4, (255,155,300), 3 )
                #print(length)
            #mp_drawing.draw_landmarks(img, hand, mp_hands.HAND_CONNECTIONS)
    
def find_available_camera():
    for index in range(10):
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            cap.release()
            return index
    return -1

def get_volume_range():
    try:
        # Use subprocess to execute commands
        result = subprocess.run(['amixer', 'sget', 'Master'], capture_output=True, text=True)
        
        # Parse the output to find the volume range
        output = result.stdout
        
        # Example parsing (adjust based on actual output format)
        if 'Mono: Playback' in output:
            # Example parsing for ALSA output
            min_volume = output.split('Mono: Playback ')[1].split(' ')[0]
            max_volume = output.split('Limits: Playback ')[1].split(' ')[0]
            return jsonify({
                'min_volume': min_volume,
                'max_volume': max_volume
            })
        else:
            return jsonify({
                'error': 'Unable to parse volume information'
            }), 500
    
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

def generate_frames():
    # comtypes.CoInitialize()
    # devices = AudioUtilities.GetSpeakers()
    # interface = devices.Activate(
    # IAudioEndpointVolume._iid_, comtypes.CLSCTX_ALL, None)
    # volume = cast(interface, POINTER(IAudioEndpointVolume))
    # volRange = volume.GetVolumeRange()
    # minVol = volRange[0]
    # maxVol = volRange[1]
    mp_drawing = mp.drawing_utils
    mp_hands = mp.hands
    hands = mp_hands.Hands()

    # volume_range = get_volume_range()

    global recording

    camera_index = find_available_camera()
    if camera_index == -1:
        return "No available camera found.", 500
    
    print(camera_index)

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print("Error: Could not open video device.")
        return

    while True:
        success, img = cap.read()
        if not success :
            break
        img = cv2.flip(img, 1)
        if(recording):   
            model(img, hands)

        ret, buffer = cv2.imencode('.jpg', img)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype = 'multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(debug=True)



