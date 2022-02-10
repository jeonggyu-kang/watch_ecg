import os
import json
import argparse
import cv2

import numpy as np 
from tqdm import tqdm
import matplotlib.pyplot as plt
import matplotlib
#matplotlib.use("MacOSX")
matplotlib.use('agg')

from utils import parse_json


class ECGDrawer:
    '''
        plt로 ecg wave 그리고 np.ndarray로 변환하여 리턴하는 기능
    '''
    def __init__(self, figsize=(10,1.5), tight_layout=True):
        self.figsize = figsize
        self.tight_layout = tight_layout

    def __call__(self, LR_value, data, label, linewidth=0.5):
        '''
            LR 값, ecg np.ndarray, 레이블 정보
        '''
        if isinstance(data, list):
            data = np.array(data)

        fig = plt.figure(figsize=self.figsize, tight_layout=self.tight_layout)

        # ecg plot
        plt.plot(data, label=label, linewidth=linewidth)
        
        plt.legend()
        plt.axis('off')
        fig.canvas.draw()
        fig_arr = np.array( fig.canvas.renderer._renderer )
        fig_arr = fig_arr.reshape( fig.canvas.get_width_height()[::-1] + (4,) )

        plt.close(fig)

        return fig_arr

class RenderFigure:
    def __init__(self, json, render_dir, **kwargs):
        self.json_path = json
        self.render_dir = render_dir
        os.makedirs(self.render_dir, exist_ok=True)

        self.patient_dict, self.patient_idx_list = parse_json(self.json_path)

        self.ecg_visualizer = ECGDrawer(figsize=(10,1.5))

        self.idx_to_id = {}
        for patient_id, idx in zip(self.patient_dict.keys(), self.patient_idx_list):
            self.idx_to_id[idx] = patient_id

        self.force_render = kwargs.get('force_render')
        if self.force_render is None:
            self.force_render = False

    def draw_ecg_wave(self, patient_id, time_step):
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
        height, width, _ = img.shape
        pt1 = (0, height//2)
        pt2 = (width-1, height//2)
        color = (0,0,0)
        img = cv2.line(img, pt1, pt2, color)
        return img

    def __call__(self):
        pbar = tqdm(total=len(self.patient_dict.keys()))
        for i, p_id in enumerate(self.patient_dict):
            if not self.force_render:
                if 'img_name' in self.patient_dict[p_id]:
                    if len(self.patient_dict[p_id]['img_name']) > 0:
                        continue
            
            self.patient_dict[p_id]['img_name'] = []
            for time_step in range(1, 4):
                img = self.draw_ecg_wave(p_id, time_step)
                # iamge path
                file_name = str(p_id) + '-' + str(time_step) + '.png'
                # write file
                cv2.imwrite(os.path.join(self.render_dir, file_name), img)
                # apply to json
                self.patient_dict[p_id]['img_name'].append(file_name)
                
            pbar.update()

        with open(self.json_path, 'w') as f:
            json.dump(self.patient_dict, f, indent='\t', ensure_ascii = False)


def opt():
    parser = argparse.ArgumentParser()
    parser.add_argument('--master_json', type=str, default='./dummy_ecg.json')  # 입력 master json파일 경로 
    parser.add_argument('--render_dir', type=str, default='./render_vis')       # 렌더링 결과가 저장될 경로
    return parser.parse_args()

def main():
    args = opt()

    RenderFigure(
        json = args.master_json,
        render_dir = args.render_dir
    )()


if __name__ == '__main__':
    main()