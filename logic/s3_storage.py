"""S3 Storage for file uploads (production)"""
import os
import uuid
from typing import Optional
import boto3
from botocore.exceptions import ClientError


def get_s3_client():
    """Get S3 client (uses IAM role in ECS, or credentials from environment)"""
    return boto3.client('s3', region_name=os.getenv('AWS_REGION', 'us-east-1'))


def save_file_to_s3(content: bytes, filename: str, subdirectory: str) -> Optional[str]:
    """
    Save file to S3 bucket (production) or local storage (development)
    
    Args:
        content: File content as bytes
        filename: Original filename
        subdirectory: Subdirectory within bucket (jd or resumes)
    
    Returns:
        S3 key (path) or local file path
    """
    bucket_name = os.getenv('UPLOADS_BUCKET')
    
    # If no bucket configured, use local storage (development)
    if not bucket_name:
        return save_file_local(content, filename, subdirectory)
    
    try:
        s3_client = get_s3_client()
        
        # Generate unique filename
        file_ext = os.path.splitext(filename)[1] if filename else ".txt"
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        s3_key = f"{subdirectory}/{unique_filename}"
        
        # Upload to S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=content,
            ContentType='application/octet-stream'
        )
        
        return s3_key
        
    except ClientError as e:
        # Fallback to local storage on error
        print(f"S3 upload failed: {e}, falling back to local storage")
        return save_file_local(content, filename, subdirectory)


def save_text_to_s3(text: str, subdirectory: str, extension: str = ".txt") -> Optional[str]:
    """
    Save text content to S3 or local storage
    
    Args:
        text: Text content
        subdirectory: Subdirectory within bucket
        extension: File extension
    
    Returns:
        S3 key or local file path
    """
    return save_file_to_s3(text.encode('utf-8'), f"text{extension}", subdirectory)


def save_file_local(content: bytes, filename: str, subdirectory: str) -> str:
    """Fallback to local file storage (development)"""
    import os
    uploads_dir = "uploads"
    os.makedirs(os.path.join(uploads_dir, subdirectory), exist_ok=True)
    
    file_ext = os.path.splitext(filename)[1] if filename else ".txt"
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(uploads_dir, subdirectory, unique_filename)
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    return file_path
