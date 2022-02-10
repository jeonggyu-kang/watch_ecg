import os
import argparse
import json

import cv2
import numpy as np

from datetime import datetime

from render import RenderFigure
from utils import parse_json, DiagnosisKeyMapper



class ECG_GUI:
    def __init__(self, **kwargs):
        self._render(**kwargs) # rendering
        self._build_params(**kwargs) 
        self._build_common(**kwargs)

        self.json_path = kwargs.get('master_json')
        self.patient_dict, self.patient_idx_list = parse_json(self.json_path)
        
        self.idx_to_id = {}
        for patient_id, idx in zip(self.patient_dict.keys(), self.patient_idx_list):
            self.idx_to_id[idx] = patient_id

        self._set_sample_length(**kwargs) # 작업해야 하는 샘플 개수를 결정


    def _build_common(self, **kwargs):
        self.save_every = kwargs.get('save_every')
        if self.save_every is None:
            self.save_every = 20

        self.global_iter_cnt = 0

    def _set_sample_length(self, **kwargs):
        # set exam case length
        cnt = 0
        for p_id in self.patient_dict:
            if self.patient_dict[p_id]['is_annotated']:
                cnt += 1

        self.length = len(self.patient_dict.keys()) - cnt
        self.num_already_done = cnt     

    def _render(self, **kwargs):
        self.render_dir = kwargs.get('render_dir')
        RenderFigure(
            json = kwargs.get('master_json'),
            render_dir = kwargs.get('render_dir'),
            force_render = kwargs.get('force_render')
        )()

    def _build_params(self, **kwargs):
        self.button_img = cv2.imread(  kwargs.get('button_path')  )
                
        self.button_window_size = kwargs.get('buttonsize')
        self.button_img = cv2.resize(self.button_img, self.button_window_size)

        self.ecg_window_name = 'ECG'
        self.button_window_name = 'DashBoard' # window name

        
        self.key_dict = DiagnosisKeyMapper.key_dict

        self.curr_patient_index = 0


    def commit_annotation(self, diagnosis: str):
        print(diagnosis) # debug 
        patient_id = self.idx_to_id[self.curr_patient_index]
        self.patient_dict[patient_id]['annotation_info'].append(diagnosis)
        if len(self.patient_dict[patient_id]['annotation_info']) == 3:
            self.patient_dict[patient_id]['is_annotated'] = True
            self.patient_dict[patient_id]['annotation_time'] = str(datetime.now())
            self.write()

    def write(self, force_save=False):
        if force_save:
            with open(self.json_path, 'w') as f:
                json.dump(self.patient_dict, f, indent='\t', ensure_ascii = False)
            self._reset_global_iter_cnt()
            return 

        if (self.global_iter_cnt+1) % self.save_every == 0:
            with open(self.json_path, 'w') as f:
                json.dump(self.patient_dict, f, indent='\t', ensure_ascii = False)
            self._reset_global_iter_cnt()

    def _next_global_iter_cnt(self):
        self.global_iter_cnt += 1

    def _reset_global_iter_cnt(self):
        self.global_iter_cnt = 0

    def revert_annotation(self):
        patient_id = self.idx_to_id[self.curr_patient_index]
        self.patient_dict[patient_id]['annotation_info'].clear()
        self.patient_dict[patient_id]['is_annotated'] = False
        self.patient_dict[patient_id]['annotation_time'] = None
        #self.write()
        
        self._reset_global_iter_cnt()
       

    def read_ecg_image(self, idx, time_step, global_step=None):
        patient_id = self.idx_to_id[idx]

        raw_LR_value      = self.patient_dict[patient_id]['LR'][(time_step-1)*2] 
        denoised_LR_value = self.patient_dict[patient_id]['LR'][(time_step-1)*2  +1]
        file_name = self.patient_dict[patient_id]['img_name'][time_step-1]  #file name
        file_path = os.path.join(self.render_dir, file_name) #full path

        img = cv2.imread(file_path)
        height, width, _ = img.shape

        origin = (10, 30)
        origin_pbar = (width-80, 30)
        origin_raw_lr = (width//2, 35)
        origin_denoised_lr = (width//2, height//2+35) #! TBD

        color = (0,0,0)        
        img = cv2.putText(img, str(patient_id), origin, cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        if global_step is not None:
            img = cv2.putText(img, str(global_step), origin_pbar, cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        img = cv2.putText(img, str(raw_LR_value), origin_raw_lr, cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        img = cv2.putText(img, str(denoised_LR_value), origin_denoised_lr, cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        return img
        
    def analysis(self, idx): # current patient index (not always starts from 0)
        
        time_step = 1 # 1, 2, 3
        while True:
            if time_step > 3:
                break
            
            patient_ecg_wave_img = self.read_ecg_image( # self.num_already_done
                idx, time_step, global_step= '{} / {}'.format(self.curr_patient_index+1 - self.num_already_done, self.length
            ))
            cv2.imshow(self.ecg_window_name, patient_ecg_wave_img)
            cv2.imshow(self.button_window_name, self.button_img)

            user_key = cv2.waitKey(0) & 0xff 

            if user_key == 27: # ESC
                return 'EXIT'
            elif user_key == 127: # backspace
                self.revert_annotation() 
                self.prev_step()
                print('back space')
                return 'PREV'
            else:
                for key in self.key_dict:
                    if user_key == ord(key):
                        time_step += 1
                        self.commit_annotation(self.key_dict[key])
                        break
        
        self.next_step() # next patient ecg wave
        self._next_global_iter_cnt()
        return 'NEXT'


    def next_step(self):
        self.curr_patient_index += 1
        

    def prev_step(self):
        self.curr_patient_index -= 1
        if self.curr_patient_index < 0:
            self.curr_patient_index = 0

    def is_annotated(self, idx):
        patient_id = self.idx_to_id[idx]
        return self.patient_dict[patient_id]['is_annotated'] == True
            
    def run(self):
        cv2.namedWindow(self.ecg_window_name, cv2.WINDOW_NORMAL)
        cv2.namedWindow(self.button_window_name, cv2.WINDOW_NORMAL)

        self.curr_patient_index = 0
        while True:
            if self.curr_patient_index == len(self.patient_idx_list):
                break

            print('[{}/{}] patient'.format(self.curr_patient_index+1 , len(self.patient_idx_list)))
   
            if not self.is_annotated(self.curr_patient_index):
                ret = self.analysis(self.curr_patient_index)
                if ret == 'EXIT':
                    break
            else:
                self.next_step()

        self.write(force_save=True)

def opt():
    parser = argparse.ArgumentParser()
    parser.add_argument('--master_json', type=str, default='./sample2.json')               # master json 파일 경로
    parser.add_argument('--button', type=str, default='./resource/ecg_button.drawio.png')    # user ux ui 버튼 이미지
    parser.add_argument('--render_dir', type=str, default='./render_vis')                    # # 렌더링 결과가 저장될 경로
    return parser.parse_args()

def main():
    args = opt()
   
    app = ECG_GUI(
        master_json = args.master_json,
        render_dir = args.render_dir, 
        button_path = args.button,
        figsize = (10,1.5),     # ecg window size
        buttonsize=(800, 300),  # button size 
        force_render = False,   #! True로 설정시 렌더링 초기화 (전체 영상 다시 생성)
        save_every = 20,        #! 자동 세이브 period (환자 20명작업 마다 자동 세이브)
    )

    app.run()

if __name__ == '__main__':
    main()