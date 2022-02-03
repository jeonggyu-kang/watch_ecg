import os
import json
import argparse
import cv2

from tqdm import tqdm # progress bar 

from diagnosis import ECGDrawer, _parse_json

class RenderFigure:
    def __init__(self, json, render_dir):
        self.json_path = json
        self.render_dir =render_dir
        os.makedirs(self.render_dir, exist_ok=True)

        self.patient_dict, self.patient_idx_list = _parse_json(self.json_path)

        self.ecg_visualizer = ECGDrawer(figsize=(10,1.5))

        self.idx_to_id = {}
        for patient_id, idx in zip(self.patient_dict.keys(), self.patient_idx_list):
            self.idx_to_id[idx] = patient_id

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

    def run(self):
        pbar = tqdm(total=len(self.patient_dict.keys()))
        for i, p_id in enumerate(self.patient_dict):
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
    parser.add_argument('--master_json', type=str, default='./dummy_ecg.json')
    parser.add_argument('--render_dir', type=str, default='./render_vis')
    return parser.parse_args()

def main():
    # [1] master_json 경로 
    # [2] redner 결과를 저장 경로 
    args = opt()

    app = RenderFigure(
        json = args.master_json,
        render_dir = args.render_dir
    )

    app.run()

if __name__ == '__main__':
    main()