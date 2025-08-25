"""
S3 service for handling EO attachments and PDF processing.
"""

import os
import boto3
from typing import Optional, Tuple
from botocore.exceptions import ClientError, NoCredentialsError
import PyPDF2
import pdfplumber
from io import BytesIO

class S3Service:
    def __init__(self, bucket_name: Optional[str] = None):
        """
        Initialize S3 service.
        
        Args:
            bucket_name: S3 bucket name. If None, uses AWS_S3_BUCKET env var.
        """
        self.bucket_name = bucket_name or os.getenv("AWS_S3_BUCKET")
        if not self.bucket_name:
            raise ValueError("S3 bucket name must be provided or set in AWS_S3_BUCKET env var")
        
        # Initialize S3 client
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=os.getenv("AWS_REGION", "us-east-1")
            )
        except NoCredentialsError:
            # Try using IAM roles if no explicit credentials
            self.s3_client = boto3.client('s3')
    
    def upload_file(self, file_path: str, s3_key: str) -> bool:
        """
        Upload a file to S3.
        
        Args:
            file_path: Local path to the file
            s3_key: S3 key (path) for the file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.s3_client.upload_file(file_path, self.bucket_name, s3_key)
            return True
        except ClientError as e:
            print(f"Error uploading file to S3: {e}")
            return False
    
    def upload_bytes(self, data: bytes, s3_key: str, content_type: str = "application/octet-stream") -> bool:
        """
        Upload bytes data to S3.
        
        Args:
            data: Bytes data to upload
            s3_key: S3 key (path) for the file
            content_type: MIME type of the data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=data,
                ContentType=content_type
            )
            return True
        except ClientError as e:
            print(f"Error uploading bytes to S3: {e}")
            return False
    
    def download_file(self, s3_key: str, local_path: str) -> bool:
        """
        Download a file from S3.
        
        Args:
            s3_key: S3 key (path) of the file
            local_path: Local path to save the file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.s3_client.download_file(self.bucket_name, s3_key, local_path)
            return True
        except ClientError as e:
            print(f"Error downloading file from S3: {e}")
            return False
    
    def download_bytes(self, s3_key: str) -> Optional[bytes]:
        """
        Download bytes data from S3.
        
        Args:
            s3_key: S3 key (path) of the file
            
        Returns:
            bytes: File data if successful, None otherwise
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            return response['Body'].read()
        except ClientError as e:
            print(f"Error downloading bytes from S3: {e}")
            return None
    
    def get_file_url(self, s3_key: str, expires_in: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL for file access.
        
        Args:
            s3_key: S3 key (path) of the file
            expires_in: URL expiration time in seconds
            
        Returns:
            str: Presigned URL if successful, None otherwise
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            print(f"Error generating presigned URL: {e}")
            return None
    
    def file_exists(self, s3_key: str) -> bool:
        """
        Check if a file exists in S3.
        
        Args:
            s3_key: S3 key (path) of the file
            
        Returns:
            bool: True if file exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False


class PDFProcessor:
    """Utility class for processing PDF files and extracting text."""
    
    @staticmethod
    def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
        """
        Extract text from PDF bytes using pdfplumber (more reliable than PyPDF2).
        
        Args:
            pdf_bytes: PDF file as bytes
            
        Returns:
            str: Extracted text from PDF
        """
        try:
            text_parts = []
            with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            
            return "\n".join(text_parts)
        except Exception as e:
            print(f"Error extracting text with pdfplumber: {e}")
            # Fallback to PyPDF2
            return PDFProcessor._extract_text_pypdf2(pdf_bytes)
    
    @staticmethod
    def _extract_text_pypdf2(pdf_bytes: bytes) -> str:
        """
        Fallback method using PyPDF2 for text extraction.
        
        Args:
            pdf_bytes: PDF file as bytes
            
        Returns:
            str: Extracted text from PDF
        """
        try:
            text_parts = []
            pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_bytes))
            
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            
            return "\n".join(text_parts)
        except Exception as e:
            print(f"Error extracting text with PyPDF2: {e}")
            return ""
    
    @staticmethod
    def extract_text_from_s3(s3_service: S3Service, s3_key: str) -> str:
        """
        Extract text from a PDF stored in S3.
        
        Args:
            s3_service: S3Service instance
            s3_key: S3 key of the PDF file
            
        Returns:
            str: Extracted text from PDF
        """
        pdf_bytes = s3_service.download_bytes(s3_key)
        if pdf_bytes:
            return PDFProcessor.extract_text_from_pdf_bytes(pdf_bytes)
        return ""


def process_eo_attachment(s3_key: str, bucket_name: Optional[str] = None) -> Tuple[bool, str]:
    """
    Process an EO attachment from S3 and extract text.
    
    Args:
        s3_key: S3 key of the attachment
        bucket_name: S3 bucket name (optional)
        
    Returns:
        Tuple[bool, str]: (success, extracted_text_or_error_message)
    """
    try:
        s3_service = S3Service(bucket_name)
        
        if not s3_service.file_exists(s3_key):
            return False, f"File not found in S3: {s3_key}"
        
        # Extract text from PDF
        extracted_text = PDFProcessor.extract_text_from_s3(s3_service, s3_key)
        
        if not extracted_text.strip():
            return False, "No text could be extracted from the PDF"
        
        return True, extracted_text
        
    except Exception as e:
        return False, f"Error processing attachment: {str(e)}" 