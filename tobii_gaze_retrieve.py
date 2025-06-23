# tobii gaze position retrieve
import json
import glob
import cv2
import os, sys
import gzip
import numpy as np
import argparse
import subprocess

class Tobii3Gazedata():
    def __init__(self):
        self.g_data = []
        self.ti = []

    def load(self, fname_gaze):
        self.g_data = []
        self.ti = []

        # load toii data
        with gzip.open(fname_gaze,'rt') as f:
            for line in f:
                d = json.loads(line)
                self.g_data.append(d)
                self.ti.append(d['timestamp'])
        print(self.g_data[2])

    # gaze dataの中からtに一番近いものを見つける    
    def find(self, t):
        idx = np.abs(np.array(self.ti) - t).argmin()
        # print(t,'-->', idx, self.g_data[idx]['timestamp'])
        if np.abs(self.g_data[idx]['timestamp'] - t) > 0.1:
            return None

        return self.g_data[idx]

if __name__ == '__main__':

    # コマンドライン引数を解釈する
    parser = argparse.ArgumentParser(prog="tobii_gaze_retrieve", description="tobii3 gaze output overlay program (viewer/convert)")
    parser.add_argument('INPUTDIR')
    parser.add_argument('-vo', "--vout", action="store_true", help="video output option")
    # parser.add_argument('-vodir','--voutdir', help="video output directory")
    parser.print_help()
    args = parser.parse_args()

    OUTPUT_DIR = "Processed"

    # ffmpeg options
    FFMPEG = "ffmpeg.exe"
    FFMPEG_OPT_AUDIO = "-vn -ac 2 -f mp3 -af aresample=async=1"
    FFMPEG_OPT_MERGE = "-c:v copy -c:a copy -map 0:v:0 -map 1:a:0"

    fname_gaze = os.path.join(args.INPUTDIR,"gazedata.gz")

    g_data = Tobii3Gazedata()
    g_data.load(fname_gaze)

    # read mp4 from video
    infile = os.path.join(args.INPUTDIR,"scenevideo.mp4")
    cap = cv2.VideoCapture(infile)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
    if args.vout is True:
        if os.path.exists(OUTPUT_DIR) is False:
            os.mkdir(OUTPUT_DIR)

        bname = args.INPUTDIR.split(os.sep)[-1]
        outfile = os.path.join("Processed",f"{bname}.mp4")
        outfile2 = os.path.join("Processed",f"{bname}_waudio.mp4")
        # print(outfile)
        
        # video output settings
        fourcc = cv2.VideoWriter_fourcc('m','p','4','v')
        vout = cv2.VideoWriter(outfile, fourcc, fps, (width,height))       
            
    # start processing
    n = 0
    
    while(True):
        ret, frame = cap.read()

        if frame is None:
            break

        if n > 0:
            ti = float(n)/float(fps)
        else:
            ti = 0

        data = g_data.find(ti)
        
        if data is not None:
            if 'gaze2d' in data['data'].keys():
                gx = data['data']['gaze2d'][0]*width
                gy = data['data']['gaze2d'][1]*height
                rad = 20
                print(gx,gy)
                cv2.circle(frame, (int(gx),int(gy)), rad, (0,255,255), thickness=7, lineType=cv2.LINE_AA)
        
        cv2.imshow('monitor', frame)
        
        if args.vout is True:
            vout.write(frame)
        
        k = cv2.waitKey(1)

        if k == 27:
            # ESC to quit
            cv2.destroyAllWindows()
            break
            
        n += 1

    if args.vout is True:
        vout.release()
        print("video is saved as ", outfile)

    cap.release()
    cv2.destroyAllWindows() 

    # extract audio file
    cmd = FFMPEG + ' -i ' + infile + ' ' + FFMPEG_OPT_AUDIO + ' ' + f"__tmp_{bname}.mp3"
    print('Running.. ',cmd)
    subprocess.run(cmd)
    
    # merge to video file
    cmd = FFMPEG + ' -i ' + outfile + ' -i ' + f'__tmp_{bname}.mp3' + ' ' + FFMPEG_OPT_MERGE + ' ' + outfile2
    print('Running.. ',cmd)
    subprocess.run(cmd)  