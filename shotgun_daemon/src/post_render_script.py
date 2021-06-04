import os
import boto3

print "------------------------Running post-render-script------------------------------"

output_path = os.environ.get('CONDUCTOR_OUTPUT_PATH', None)
s3_bucket = os.environ.get('CONDUCTOR_S3_BUCKET', None)
s3_path_root = os.environ.get('CONDUCTOR_S3_PATH', None)


if output_path is None:
    raise Exception("Environment variable 'CONDUCTOR_OUTPUT_PATH' is not defined.")

if s3_bucket is None:
    raise Exception("Environment variable 'CONDUCTOR_S3_BUCKET' is not defined.")

print "Scanning output path '{}'".format(output_path)
src_paths = []
for root, dir_list, file_list in os.walk(output_path):

    for filename in file_list:
        src_paths.append(os.path.join(root, filename))
        
file_count = len(src_paths)
print "Transferring {} files to s3 bucket".format(file_count)

s3 = boto3.client('s3')

for index, path in enumerate(src_paths):
    
    file_size = os.path.getsize(path)    
    frame = path.split(".")[-2]
    dest_path = s3_path_root % int(frame)
    
    print "[{}/{}] Uploading {} ({}) to {}".format(index+1, file_count, path, file_size, dest_path)
    s3.upload_file(path, s3_bucket, dest_path)

print "Transfer to s3 complete."