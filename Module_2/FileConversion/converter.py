import json
from enum import Enum
import re
from starlette.datastructures import UploadFile
from pypdf import PdfReader
from docx import Document
import pandas as pd
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup


class FileConversion:
    class TypeOfFile(Enum):
        DOCX = "DOCX"
        XLSX = "XLSX"
        CSV = "CSV"
        PDF = "PDF"
        HTML = "HTML"
        TXT = "TXT"
        JSON = "JSON"
        XML = "XML"

    __file: UploadFile
    __extension: str
    __content_type: str

    def __init__(self, file: UploadFile, extension: str, content_type: str):
        self.__file = file
        self.__extension = extension
        self.__content_type = content_type

    def get_text(self) -> str:
        match self.__extension, self.__content_type:
            case 'docx', "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                return self.__extract_docx()
            case 'xlsx', "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                return self.__extract_xlsx()
            case 'csv', "text/csv":
                return self.__extract_csv()
            case 'pdf', "application/pdf":
                return self.__extract_pdf()
            case 'html', "text/html":
                return self.__extract_html()
            case 'txt', "text/plain":
                return self.__extract_txt()
            case 'json', "application/json":
                return self.__extract_json()
            case 'xml', "application/xml":
                return self.__extract_xml()
            case _:
                return ""

    def __extract_docx(self) -> str:
        doc = Document(self.__file.file)
        fulltext = []
        for paragraph in doc.paragraphs:
            fulltext.append(f" {paragraph.text}")

        text = ''.join(fulltext)
        clean_text = re.sub(r'\s+', ' ', text).strip()
        return clean_text

    def __extract_xlsx(self) -> str:
        df = pd.read_excel(self.__file.file, sheet_name=None)

        text = ""
        for sheet in df.values():
            text += " ".join(sheet.astype(str).fillna("").values.flatten())

        clean_text = re.sub(r'\s+', ' ', text).strip()
        del df
        return clean_text

    def __extract_csv(self) -> str:
        df = pd.read_csv(self.__file.file)
        text = " ".join(df.astype(str).fillna("").values.flatten())
        clean_text = re.sub(r'\s+', ' ', text).strip()
        del df
        return clean_text

    def __extract_pdf(self) -> str:
        reader = PdfReader(self.__file.file)
        text = ''
        for page in reader.pages:
            text += page.extract_text()

        clean_text = re.sub(r'\s+', ' ', text).strip()
        return clean_text

    def __extract_html(self) -> str:
        soup = BeautifulSoup(self.__file.file, 'html.parser')
        text = soup.get_text()
        clean_text = re.sub(r'\s+', ' ', text).strip()
        return clean_text

    def __extract_txt(self) -> str:
        text = self.__file.file.read().decode('utf-8')
        clean_text = re.sub(r'\s+', ' ', text).strip()
        return clean_text

    def __extract_json(self) -> str:
        def extract_text(obj):
            texts = []
            if isinstance(obj, dict):
                for value in obj.values():
                    texts.extend(extract_text(value))
            elif isinstance(obj, list):
                for item in obj:
                    texts.extend(extract_text(item))
            elif isinstance(obj, str):
                texts.append(obj)
            return texts

        data = json.loads(self.__file.file.read())
        text = " ".join(extract_text(data))

        clean_text = re.sub(r'\s+', ' ', text).strip()
        return clean_text

    def __extract_xml(self) -> str:
        def extract_text(elem):
            texts = []
            if elem.text:
                texts.append(elem.text)
            for child in elem:
                texts.extend(extract_text(child))
            if elem.tail:
                texts.append(elem.tail)
            return texts

        tree = ET.parse(self.__file.file)
        root = tree.getroot()

        text = " ".join(extract_text(root))
        clean_text = re.sub(r'\s+', ' ', text).strip()

        return clean_text

