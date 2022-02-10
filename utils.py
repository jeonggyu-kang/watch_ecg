from abc import ABC, abstractmethod
import os
import json
import pandas as pd


# TODO : 진단명 -> 환자가 이해할 수 있는 단어로 변환
class Jargon2HumanWord:
    jargon_dict = {
        'PAC' : '정상',
        'NSR' : '심방조기수축',
        'PVC' : '심실조기수축',
        'artifact' : '파형 흔들림4',
    }

# TODO : key value 추가하기
class DiagnosisKeyMapper:
    key_dict = {
        'a': 'PAC',
        'n': 'NSR',
        'v': 'PVC',
        'z': 'artifact'
    }


def parse_json(json_path):
    with open(json_path, 'r') as f:
        data = json.load(f)

    patient_idx_list = list(range(len(data.keys())))
    
    return data, patient_idx_list

def parse_csv(csv_file):
    return pd.read_csv(csv_file)

def get_attribute_from_dataframe(df, p_id=None, dict_key=None):
    if p_id is None:
        p_id = dict_key.split('_')[0]
        
    row = df.loc[df['id'] == p_id]
    patient_name = row['name'].to_list()
    
    return patient_name[0]




class BaseAttribute(ABC):
    @abstractmethod
    def __call__(self):
        pass
    @abstractmethod
    def _build_organization_param(self):
        pass

    def _get_color_font_scale(self, attribute_type):
        color = None; font = None; scale = None
        if 'color' in self.color_font_scale[attribute_type]:
            color = self.color_font_scale[attribute_type]['color']
        if 'font' in self.color_font_scale[attribute_type]:
            font = self.color_font_scale[attribute_type]['font']
        if 'scale' in self.color_font_scale[attribute_type]:
            scale = self.color_font_scale[attribute_type]['scale']
        return color, font, scale



class PatientSpecificAttribute(BaseAttribute):
    def __init__(self, **kwargs):
        self.attribute_dict = {
            'recorded_time' : kwargs.get('recorded_time'),
            'jargon' : kwargs.get('jargon'),
            'ecg_images' : kwargs.get('ecg_images'),
        }
        self.render_dir = kwargs.get('render_dir')
        self._build_organization_param()
        
    def _build_organization_param(self):
        jargon_w = 80
        recorded_time_w = 5
        self.location_dict = {
            'recorded_time' : [(recorded_time_w, 8), (recorded_time_w, 54)],
            'jargon'        : [
                (jargon_w, 10), (jargon_w, 20), (jargon_w, 30),
                (jargon_w, 40), (jargon_w, 50), (jargon_w, 60)
            ],
            'ecg_images'    : [(5,20), (5,33), (5,46), (5,66), (5,79), (5,92)],
        }
        self.size_dict = {
            'ecg_images' : (350, 90),
        }

        # TODO : refactor 
        self.color_font_scale = {
            'recorded_time' : {
                'size' : 8
            },
            'jargon' : {
                'size' : 14,
                'color' : (0,0,0) # Red or Blue
            },
        }
    
    def _get_color_font_scale_by_jargon(self, k, stat):
        color, font, scale = self._get_color_font_scale(k)
        if stat == '정상':
            color = (0,0,255)
        elif stat in ['심방조기수축', '심실조기수축']:
            color = (255,0,0)
        else:
            color = (0,0,0)

        return color, font, scale

    def __call__(self, pdf, method, first_row):
        if first_row:
            offset = 0
        else:
            offset = 3

        for k, v in self.attribute_dict.items():
            if k in self.size_dict.keys(): # image
                if isinstance(v, list):
                    for i, img in enumerate(v):
                        method.drawImage(
                            pdf = pdf,
                            image_path = os.path.join(self.render_dir, img),
                            location = self.location_dict[k][i+offset],
                            size = self.size_dict[k]
                        )
                else:
                    raise TypeError('{} must be list, but got {}'.format(k, type(v)))
                    exit(1)
            else: # text 
                if isinstance(v, str): # recorded date
                    color, font, scale = self._get_color_font_scale(k)
                    method.drawText(
                        pdf = pdf,
                        text = v,
                        location = self.location_dict[k][ offset % 2 ],
                        color = color,
                        font = font,
                        scale = scale
                    )
                elif isinstance(v, list):    # jargon
                    for i, jargon in enumerate(v):
                        human_word = Jargon2HumanWord.jargon_dict[jargon]
                        color, font, scale = self._get_color_font_scale_by_jargon(k, human_word)
                        method.drawText(
                            pdf = pdf,
                            text = human_word,
                            location = self.location_dict[k][i+offset],
                            color = color,
                            font = font,
                            scale = scale
                        )
                else:
                    raise TypeError('{} must be list or str, but got {}'.format(k, type(v)))
                    exit(1)
                
        return 




class CommonAttribute(BaseAttribute):
    def __init__(self, **kwargs):
        self.attribute_dict = {
            'title' : kwargs.get('title'),
            'page' : str(1 + kwargs.get('cover_page')),
            'board' : kwargs.get('board'),
            'legend_board' : kwargs.get('legend_board'),
            'logo' : kwargs.get('logo'),
            'diagnosis' : [],
        }
        
        self._build_organization_param() # location setup

    def _build_organization_param(self):
        self.shape_dict = {
            'ecg_rect' : 'rect',
        }
        
        self.location_dict = {
            'ecg_rect' : (5, 70),
            'diagnosis' : (90, 90),
            'title'  : (5, 5),
            'name'   : (80, 5),
            #'recorded_time' : (90, 90),
            'page' : (90, 90),
            'logo' : (45, 95), 
            'board' : (45, 80), 
            'legend_board' : (70, 10),
        }

        self.size_dict = {
            'logo' : (100, 20), # width, height
            'board' : (300, 600),
            'ecg_rect' : (300, 600)
        }

        # TODO : refactor 
        self.color_font_scale = {
            'title' : {
                'size' : 16,
            },
            'diagnosis' : {
                'size' : 14,
            },
            'name' : {
                'size' : 12
            },
            'page' : {
                'size' : 10
            },
            'legend_board' : {
                'size' : 10
            }
        }
    def _get_color_font_scale(self, attribute_type):
        color = None; font = None; scale = None
        if 'color' in self.color_font_scale[attribute_type]:
            color = self.color_font_scale[attribute_type]['color']
        if 'font' in self.color_font_scale[attribute_type]:
            font = self.color_font_scale[attribute_type]['font']
        if 'scale' in self.color_font_scale[attribute_type]:
            scale = self.color_font_scale[attribute_type]['scale']
        return color, font, scale

    def update_attribute(self, key, value):
        if key == 'page':
            self.attribute_dict['page'] += '/{}'.format(value)
        else:
            self.attribute_dict.update({str(key):value})
        
    def _next_page(self):
        cur_pp, max_pp = map(int, self.attribute_dict['page'].split('/'))
        cur_pp += 1
        self.attribute_dict['page'] = '{}/{}'.format(cur_pp, max_pp)

    def __call__(self, pdf, method):
        for k, v in self.shape_dict.items():
            if v == 'rect':
                method.rect(
                    pdf = pdf,
                    location = self.location_dict[k],
                    size = self.size_dict[k]
                )
            else:
                raise ValueError
                exit(1)


        for k, v in self.attribute_dict.items():
            if k in self.size_dict.keys(): # image
                method.drawImage(
                    pdf = pdf,
                    image_path = v,
                    location = self.location_dict[k],
                    size = self.size_dict[k]
                )
            else: # text 
                color, font, scale = self._get_color_font_scale(k)
                method.drawText(
                    pdf = pdf,
                    text = v,
                    location = self.location_dict[k],
                    color = color,
                    font = font,
                    scale = scale
                )
                
            if k == 'page':
                self._next_page()


# A-2106161442_ecg_2021-06-16_18.csv": {