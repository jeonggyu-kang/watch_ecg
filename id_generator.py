import os
import json
import argparse

def _parse_id_json(json_path):
    if not os.path.isfile(json_path):
        with open(json_path, 'w') as f:
            json.dump({}, f, indent = '\t', ensure_ascii= False)

    with open(json_path, 'r') as f:
        data = json.load(f)

    return data


def _get_name_from_csv(csv_file):
    return '홍길동2'


def _walk_csv(csv_root):
    ret = {}

    for patient_id in os.listdir(csv_root):
        csv_dir = os.path.join(csv_root, patient_id)
        ret[patient_id] = {}
        ret[patient_id]['csv'] = []
        ret[patient_id]['name'] = None

        for csv_file in os.listdir(csv_dir):
            if ret[patient_id]['name'] is None:
                ret[patient_id]['name'] = _get_name_from_csv(os.path.join(csv_dir, csv_file))
            ret[patient_id]['csv'].append(csv_file)


    return ret

class PatientIDGenerator:
    def __init__(self, csv_root_dir, json_path):
        self.csv_root_dir = csv_root_dir
        self.json_path = json_path

        self.patient_dict = _parse_id_json(self.json_path)
        self.new_patient_dict = _walk_csv(self.csv_root_dir)

    def run(self):
        self.patient_dict.update( self.new_patient_dict )
        with open(self.json_path, 'w') as f:
            json.dump(self.patient_dict, f, indent = '\t', ensure_ascii = False)





def opt():
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv_root_dir', type = str, 
                        default='/home/compu/Projects/arrhythmia/diagnosis/patient_ecg')
    parser.add_argument('--id_json', type=str, default='./id_generator.json')
    return parser.parse_args()

def main():
    args = opt()

    app = PatientIDGenerator(
        csv_root_dir = args.csv_root_dir,     # 환자 csv 루트 디렉토리  
        json_path = args.id_json              # 결과 json 저장 경로 
    )
    app.run()

if __name__ == '__main__':
    main()