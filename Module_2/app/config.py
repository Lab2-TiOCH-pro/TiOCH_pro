MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_EXTS = ['docx', 'pdf', 'xlsx', 'csv', 'html', 'txt', 'json', 'xml']
ALLOWED_CONTENT_TYPES = [
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/pdf",                                                         # .pdf
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",       # .xlsx
    "text/csv",                                                                 # .csv
    "text/html",                                                                # .html
    "text/plain",                                                               # .txt
    "application/json",                                                        # .json
    "application/xml"                                                          # .xml
]