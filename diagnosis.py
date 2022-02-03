import os
import argparse
import json

import cv2
import numpy as np

from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('agg')

class ECGDrawer:
    def __init__(self, figsize=(10,1.5), tight_layout=True):
        self.figsize = figsize
        self.tight_layout = tight_layout

    def __call__(self, LR_value, data, label, linewidth=0.5):
        if isinstance(data, list):
            data = np.array(data)

        fig = plt.figure(figsize=self.figsize, tight_layout=self.tight_layout)

        # ecg plot
        plt.plot(data, label=label, linewidth=linewidth)
        #plt.title('LR = {}'.format(LR_value))
        plt.legend()
        plt.axis('off')
        fig.canvas.draw()
        fig_arr = np.array( fig.canvas.renderer._renderer )
        fig_arr = fig_arr.reshape( fig.canvas.get_width_height()[::-1] + (4,) )

        plt.close(fig)

        return fig_arr


def _parse_json(json_path):
    with open(json_path, 'r') as f:
        data = json.load(f)

    patient_idx_list = list(range(len(data.keys())))
    
    return data, patient_idx_list

class ECG_GUI:
    def __init__(self, **kwargs):
        self.render_dir = kwargs.get('render_dir')

        self.json_path = kwargs.get('json_path')
        self.patient_dict, self.patient_idx_list = _parse_json(self.json_path)
        
        self.idx_to_id = {}
        for patient_id, idx in zip(self.patient_dict.keys(), self.patient_idx_list):
            self.idx_to_id[idx] = patient_id
        
        self._build_params(**kwargs)

        figsize = kwargs.get('figsize')
        self.ecg_visualizer = ECGDrawer(figsize=figsize)
        
        # set exam case length
        tmp = len(self.patient_dict.keys())
        for p_id in self.patient_dict:
            if self.patient_dict[p_id]['is_annotated']:
                tmp -= 1
        self.length = tmp                

    def _build_params(self, **kwargs):
        self.button_img = cv2.imread(  kwargs.get('button_path')  )
        
        
        self.button_window_size = kwargs.get('buttonsize')
        self.button_img = cv2.resize(self.button_img, self.button_window_size)

        self.ecg_window_name = 'ECG'
        self.button_window_name = 'DashBoard' # window name

        self.key_dict = {
            'a': 'PAC',
            'n': 'NSR',
            'v': 'PVC'
        }
        self.curr_patient_index = 0

    def commit_annotation(self, diagnosis: str):
        print(diagnosis) # debug 
        patient_id = self.idx_to_id[self.curr_patient_index]
        self.patient_dict[patient_id]['annotation_info'].append(diagnosis)
        if len(self.patient_dict[patient_id]['annotation_info']) == 3:
            self.patient_dict[patient_id]['is_annotated'] = True
            self.patient_dict[patient_id]['annotation_time'] = str(datetime.now())
            self.write()

    def write(self):
        with open(self.json_path, 'w') as f:
            json.dump(self.patient_dict, f, indent='\t', ensure_ascii = False)

    def revert_annotation(self):
        patient_id = self.idx_to_id[self.curr_patient_index]
        self.patient_dict[patient_id]['annotation_info'].clear()
        self.patient_dict[patient_id]['is_annotated'] = False
        self.patient_dict[patient_id]['annotation_time'] = None
        self.write()

        print(self.curr_patient_index, patient_id)
       
    def draw_ecg_wave(self, idx, time_step):
        patient_id = self.idx_to_id[idx]

        LR_value = self.patient_dict[patient_id]['LR']
        raw_data = self.patient_dict[patient_id]['raw_ecg_wave_voltage']
        denoised_data = self.patient_dict[patient_id]['denoised_ecg_wave_voltage']

        chunk_size = len(raw_data) // 3
        offset = (time_step-1) * chunk_size
        raw_data2 = raw_data[ offset : offset + chunk_size ]
        denoised_data2 = denoised_data[ offset : offset + chunk_size ]


        # LR, data, label          0 1 2 
        raw = self.ecg_visualizer( 
            LR_value=LR_value[ (time_step-1)*2 ], 
            data=raw_data2, 
            label='Original {}/3'.format(time_step)
        ) 
        denoised = self.ecg_visualizer(
            LR_value=LR_value[ (time_step-1)*2  +1 ],
            data=denoised_data2, 
            label='Denoised {}/3'.format(time_step)
        )

        img = cv2.vconcat([raw, denoised])
        return img 

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
        
    def analysis(self, idx):
        '''
        patient_id
                30 s
                    10s  button (up-raw) / (bottom-denoised)
                    10s  button (up-raw) / (bottom-denoised)
                    10s  button (up-raw) / (bottom-denoised)
        '''
        time_step = 1 # 1, 2, 3
        while True:
            if time_step > 3:
                break

            #patient_ecg_wave_img = self.draw_ecg_wave(idx, time_step) # up(raw)/bottom(denoised)
            patient_ecg_wave_img = self.read_ecg_image(
                idx, time_step, global_step= '{} / {}'.format(self.curr_patient_index+1, self.length
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

        #cv2.imshow(self.ecg_window_name, img)
        # self.patient_idx_list = [0,1,2,3,4,,,,,N]
        self.curr_patient_index = 0
        while True:
            if self.curr_patient_index == len(self.patient_idx_list): # 2
                break
            #print(f'[{self.curr_patient_index+1}/{len(self.patient_idx_list)}] patient')
            print('[{}/{}] patient'.format(
                self.curr_patient_index+1 , len(self.patient_idx_list)))
   
            if not self.is_annotated(self.curr_patient_index):
                ret = self.analysis(self.curr_patient_index)
                if ret == 'EXIT':
                    break
            else:
                self.next_step()


def opt():
    parser = argparse.ArgumentParser()
    parser.add_argument('--master_json', type=str, default='./dummy_ecg.json')
    parser.add_argument('--button', type=str, default='./ecg_button.drawio.png')
    parser.add_argument('--render_dir', type=str, default='./render_vis')
    return parser.parse_args()

def main():
    args = opt()
   
    app = ECG_GUI(
        json_path = args.master_json,
        button_path = args.button,
        render_dir = args.render_dir, # rendering result directory
        figsize = (10,1.5), # ecg window size
        buttonsize=(800, 300) # button size 
    )

    app.run()

if __name__ == '__main__':
    main()