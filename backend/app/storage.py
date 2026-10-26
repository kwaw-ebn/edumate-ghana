"""Private S3-compatible file storage; file bytes never enter Postgres."""
import io,os,zipfile
from pathlib import Path
import boto3
from botocore.config import Config
from fastapi import HTTPException
MAX_BYTES=10*1024*1024
MAX_VIDEO_BYTES=50*1024*1024
TYPES={'.mp4':'video/mp4','.pdf':'application/pdf','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.docx':'application/vnd.openxmlformats-officedocument.wordprocessingml.document','.pptx':'application/vnd.openxmlformats-officedocument.presentationml.presentation','.xlsx':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}
def validate_file(name,data):
    suffix=Path(name).suffix.lower()
    if suffix not in TYPES: raise HTTPException(422,'Use MP4, PDF, DOCX, PPTX, XLSX, PNG or JPG')
    limit=MAX_VIDEO_BYTES if suffix=='.mp4' else MAX_BYTES
    if not data or len(data)>limit: raise HTTPException(413,f'File must be between 1 byte and {limit//1024//1024} MB')
    valid=False
    if suffix=='.mp4': valid=len(data)>=12 and data[4:8]==b'ftyp'
    elif suffix=='.pdf': valid=data.startswith(b'%PDF-')
    elif suffix=='.png': valid=data.startswith(b'\x89PNG\r\n\x1a\n')
    elif suffix in ('.jpg','.jpeg'): valid=data.startswith(b'\xff\xd8\xff')
    else:
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                names=z.namelist(); root={'.docx':'word/document.xml','.pptx':'ppt/presentation.xml','.xlsx':'xl/workbook.xml'}[suffix]
                valid=root in names and '[Content_Types].xml' in names and not any('vbaProject' in n for n in names)
                if sum(i.file_size for i in z.infolist())>100*1024*1024: valid=False
        except (zipfile.BadZipFile,KeyError): pass
    if not valid: raise HTTPException(422,'File contents do not match a supported media file or document')
    return TYPES[suffix]
def s3():
    if not os.getenv('AWS_ENDPOINT_URL_S3') or not os.getenv('AWS_ACCESS_KEY_ID'): raise HTTPException(503,'File storage is not configured')
    return boto3.client('s3',endpoint_url=os.environ['AWS_ENDPOINT_URL_S3'],region_name=os.getenv('AWS_REGION','eu-central-1'),config=Config(signature_version='s3v4',s3={'addressing_style':'path'}))
def bucket(): return os.getenv('S3_BUCKET','edumate-resources')
def put(key,data,content_type): s3().put_object(Bucket=bucket(),Key=key,Body=data,ContentType=content_type)
def read(key): return s3().get_object(Bucket=bucket(),Key=key)['Body'].read()
