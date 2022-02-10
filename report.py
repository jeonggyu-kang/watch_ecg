from abc import ABC, abstractmethod
import argparse
import os

from PyPDF2 import PdfFileWriter, PdfFileReader, PdfFileMerger

from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from utils import parse_json, parse_csv, get_attribute_from_dataframe
from utils import PatientSpecificAttribute, CommonAttribute

pdfmetrics.registerFont(TTFont("NanumGothicLight", "NanumGothicLight.ttf"))

class BasePDF(ABC):
    @abstractmethod
    def drawText():
        pass

    @abstractmethod
    def drawImage():
        pass

    @abstractmethod
    def makePDF():
        pass

class PDF(BasePDF): # reportlab 의존성 
    A4_width_in_inch  = (8 + 5/16)*inch
    A4_height_in_inch = (11  + 11/16)*inch

    @staticmethod
    def rect(pdf, location, size, fill=False):
        if True: # TODO : make it optional
            location = PDF.get_coords_by_ratio(location)

        pdf.rect(location[0], location[1], size[0], size[1], stroke=True, fill=fill)


    @staticmethod    
    def drawText(pdf, text, location, scale=None, color=None, font=None):
        if scale is None:
            scale = 16
        if color is None:
            color = (0,0,0)

        if font is None:
            pdf.setFont('NanumGothicLight', scale)
        else:
            pdf.setFont(font, scale)

        if True: # TODO : make it optional
            location = PDF.get_coords_by_ratio(location)

        # set color
        pdf.setFillColor(color)

        report = pdf.beginText(location[0], location[1])
        
        if isinstance(text, list):
            for line in text:
                report.textLine(line)
        elif isinstance(text, str):
            report.textLine(text)

        pdf.drawText(report)

    @staticmethod  
    def drawImage(pdf, image_path, location, size):
        '''
            args:
                image_path (str) : path to the image file.
                location (tuple or list) : coords of content to be displayed. (x, y)
                size (tuple or list) : size of content to be displayed. (width, height)
        '''
        if True: # TODO : make it optional
            location = PDF.get_coords_by_ratio(location)
        pdf.drawImage(image_path, location[0], location[1], width=size[0], height=size[1])

    @staticmethod
    def makePDF(pdf_path):
        return Canvas(pdf_path)

    @staticmethod
    def get_coords_by_ratio(location):
        '''
            args:
                location (tuple or list) : percetange ratio in common CS coords system.        
        '''
        target_x = (location[0] / 100.0) * PDF.A4_width_in_inch
        target_y = PDF.A4_height_in_inch * (1.0 - (location[1]/100.0))
        return (target_x, target_y)


class ECGReport:
    def __init__(self, **kwargs):
        self._build_common(**kwargs)
        
        self.json_path = kwargs.get('master_json')
        self.patient_master_dict, _ = parse_json(self.json_path)
        self.technician_df = parse_csv(kwargs.get('technician_csv'))
        os.makedirs(self.pdf_root, exist_ok=True)
        
    def _build_common(self, **kwargs):
        self.common_attribute = CommonAttribute(**kwargs.get('meta'))

        self.cover_page = kwargs.get('meta')['cover_page']
        self.cover_pdf  = kwargs.get('meta')['cover']

        self.render_dir = kwargs.get('render_dir')
        self.pdf_root = kwargs.get('pdf_root')
        self.method = kwargs.get('pdf_method')


    def _get_patient_attribute(self, json_key, attribute_type):
        return self.patient_master_dict[json_key][attribute_type]
    
    def _get_patient_keys(self, unique_id):
        ret = []
        for k, v in self.patient_master_dict.items():
            try:
                if unique_id == v['patient_id']:
                    ret.append(k)
            except KeyError:
                if unique_id in k:
                    ret.append(k)

        return ret

    def _make_pdf(self, unique_p_id, p_name):
        pdf_path = os.path.join(self.pdf_root, str(p_name) + str(unique_p_id))
        pdf_path += '.pdf'
        pdf = self.method.makePDF(pdf_path)
        return pdf, pdf_path

    def write_json(self):
        with open(self.json_path, 'w') as f:
            json.dump(self.patient_master_dict, f, indent='\t', ensure_ascii = False)

    def _convert_to_pdf(self, pdf, repeatables, write_common_attribute=False):
        # add one time attributes
        if write_common_attribute:
            self.common_attribute(pdf, self.method)
        
        # add repeatables attributes
        is_first_row = write_common_attribute
        repeatables(pdf, self.method, is_first_row)

    def run(self, unique_p_id):
        # set patient name
        p_name = get_attribute_from_dataframe(df = self.technician_df, p_id=unique_p_id)
        self.common_attribute.update_attribute('name', p_name)

        # make pdf
        pdf, pdf_path = self._make_pdf(unique_p_id, p_name)

        # brute-force search (query: unique patient id)
        json_keys = self._get_patient_keys(unique_p_id)
        # # of total pages
        total_pages = int( len(json_keys) / 2  + 0.5) + self.cover_page
        self.common_attribute.update_attribute('page', total_pages)
                
        for i, key in enumerate(json_keys):
   
            self._convert_to_pdf(
                pdf = pdf,
                repeatables = PatientSpecificAttribute(
                    recorded_time = self._get_patient_attribute(key, 'recorded_time'),
                    ecg_images = self._get_patient_attribute(key, 'img_name'),
                    jargon = self._get_patient_attribute(key, 'annotation_info'),
                    render_dir = self.render_dir
                ),
                write_common_attribute = (i%2 == 0)
            )

            if i%2 != 0:
                pdf.showPage()
            # mark flag
            self.patient_master_dict[key]['is_printed'] = True
           
        pdf.save()
        self._merge_pdf(pdf_path)

        #! update json 
        #self.write_json()
        return 

    def _merge_pdf(self, contents_pdf_path):
        merger = PdfFileMerger()
        merger.append(PdfFileReader(open(self.cover_pdf, 'rb')))
        merger.append(PdfFileReader(open(contents_pdf_path, 'rb')))
        
        try:
            merger.write('(final)'+contents_pdf_path)
        except:
            print('Can not merge pdf files.')
            exit(1)



        
        

        

def opt():
    parser = argparse.ArgumentParser()
    
    ''' ------------------------------ input 파일 경로 ------------------------------ '''
    #parser.add_argument('--master_json', type=str, default='./dummy_ecg.json')      # master json 파일
    parser.add_argument('--master_json', type=str, default='./sample2.json')        # master json 파일
    parser.add_argument('--technician_csv', type=str, default='./technician.csv')   # technician csv 파일
    parser.add_argument('--render_dir', type=str, default='./render_vis')           # 렌더링 이미지가 저장되어 있는 경로

    ''' ------------------------------ 리소스 ------------------------------ '''
    parser.add_argument('--title', type=str, default='Watch형 심전도 연구과제')          # 환자 리포트 타이틀
    parser.add_argument('--logo', type=str, default='./resource/logo.png')
    parser.add_argument('--board', type=str, default='./resource/board.png')
    parser.add_argument('--legend_board', type=str, default='부정맥 유무 판독')
    parser.add_argument('--cover', type=str, default='./resource/cover.pdf')
    ''' ------------------------------ output 경로 ------------------------------ '''
    parser.add_argument('--pdf_dir', type=str, default='./pdf_results')             # 결과 PDF 파일이 저장될 경로
    
    return parser.parse_args()

def main():
    args = opt()

    #! (목요일) 환자 unique patient ID 입력 -> 모든 csv parsing 후 report 생성
    args.patient_id = 'A-2106161442' # unique patient id
    
    app = ECGReport(
        master_json = args.master_json,       # master json 파일
        technician_csv = args.technician_csv, # technician csv 파일
        pdf_method = PDF,                     # PDF 생성 방법 (library)
        pdf_root = args.pdf_dir,              # PDF 저장 디렉터리
        render_dir = args.render_dir,         # 렌더링 이미지가 저장되어 있는 경로
        meta = dict(
            cover=args.cover,   # 커버 PDF
            cover_page= 1,      # 커버 PDF 페이지 수 TODO : parse from given pdf
            title=args.title,   # 검사지 제목
            logo =args.logo,    # 병원 로고
            board=args.board,    # 그레이 보드 (진단명 출력)
            legend_board=args.legend_board # 그레이 보드 범례
        )   
    )

    app.run(args.patient_id) # 환자 ID를 입력 

if __name__ == '__main__':
    main()