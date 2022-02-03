import json

with open('./ss.json', 'r') as f:
    data = json.load(f)



new_data = {}

for key in data:
    new_data[key] = {
        'annotation_info' : [],
        'annotation_time' : None,
        'is_printed' : None,
        'is_annotated' : None
    }

    new_data[key]['LR'] = data[key]['LR']
    new_data[key]['raw_ecg_wave_voltage'] = data[key]['ecg_file_list']
    new_data[key]['denoised_ecg_wave_voltage'] = data[key]['denoised_ech_file_list']

    # print(len(data[key]['ecg_file_list']))
    # print(len(data[key]['denoised_ech_file_list']))

    # break

with open('./master_ecg.json', 'w') as f:     
    json.dump(new_data, f, indent = '\t', ensure_ascii = False)   


