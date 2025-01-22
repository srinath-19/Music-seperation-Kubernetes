import os, sys
import redis
from minio import Minio
import time
import platform


# Redis setup
redis_url = os.getenv('REDISTOGO_URL') or 'localhost'
redis_port = os.getenv('REDISTOGO_PORT') or 6379
# r = redis.StrictRedis(host=redis_url, port=redis_port, db=0)
redis_client = redis.StrictRedis(host=redis_url, db=0)

# Minio setup
minio_url = os.getenv("MINIOTOGO_HOST") or "localhost:9000"
minio_user = os.getenv("MINIO_USER") or "rootuser"
minio_pwd = os.getenv("MINIO_PASSWD") or "rootpass123"
minio_client = Minio(minio_url, secure=False, access_key=minio_user, secret_key=minio_pwd)

infoKey = "{}.rest.info".format(platform.node())
debugKey = "{}.rest.debug".format(platform.node())



def log_debug(message, key=debugKey):
    print("DEBUG:", message, file=sys.stdout)
    # redisClient = redis.StrictRedis(host=redisHost, port=redisPort, db=0)
    redis_client.lpush('logging', f"{debugKey}:{message}")

def log_info(message, key=infoKey):
    print("INFO:", message, file=sys.stdout)
    # redisClient = redis.StrictRedis(host=redisHost, port=redisPort, db=0)
    redis_client.lpush('logging', f"{infoKey}:{message}")

output_bucket = "output"
while True:
    try:
        work = redis_client.blpop("toWorker", timeout=0)
        queue = work[1].decode('utf-8')
        file_name = queue +".mp3"
        data  = minio_client.fget_object('queues', file_name, file_name)
        print("fetched from the queues")
        minio_client.remove_object('queues',queue+".mp3")
        check_minio_bucket = minio_client.bucket_exists(output_bucket)
        print("deleted the song from the queue")
        time.sleep(10)
        if not check_minio_bucket:
            minio_client.make_bucket(output_bucket)
        
        command = f"python3 -m demucs.separate --mp3 --out /data/output \
        {file_name}"
        os.system(command)

        file_path = f"/data/output/mdx_extra_q/{queue}/"
        for file in os.listdir(file_path):
            print(file)
            minio_client.fput_object(output_bucket, f"{queue}/" + file, file_path + file)

        os.remove(queue+".mp3")
        path = f"/data/output/mdx_extra_q/{queue}/*.mp3"
        os.remove(path)
    except Exception as exp:
        print(f"Exception raised in log loop: {str(exp)}")
        