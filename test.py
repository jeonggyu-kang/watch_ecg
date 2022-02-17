import json
from collections import OrderedDict
import random 

def make_dummy_data():
    low = random.randrange(-10, 10)
    
    ecg_fake1 = [ x for x in range(low, low+30)]
    ecg_fake2 = [ x for x in range(low, low-30, -1)]
    random.shuffle(ecg_fake1)
    random.shuffle(ecg_fake2)
    
    assert len(ecg_fake1) == len(ecg_fake2)

    #random.randrange
    dummy_dict = {"LR" : [1,2,3,4,5,6],
                "raw_ecg_wave_voltage" : ecg_fake1,
                "denoised_ecg_wave_voltage" : ecg_fake2,
                "is_printed" : False,
                "is_annotated" : False,
                "annotation_info": [],
                "annotation_time": None
                "recorded_time" : ""   # 기록된 날짜, 측정 일시 (애플, 삼성)
    }
    return dummy_dict

ecg = {}
ecg['patient1'] = make_dummy_data()
ecg['patient2'] = make_dummy_data()
ecg['patient3'] = make_dummy_data()
ecg['patient4'] = make_dummy_data()
ecg['patient5'] = make_dummy_data()
ecg['patient6'] = make_dummy_data()
ecg['patient7'] = make_dummy_data()

print(json.dumps(ecg, ensure_ascii=False, indent="\t") )

with open('./dummy_ecg.json', 'w') as f:
    json.dump(ecg, f, indent='\t', ensure_ascii = False)