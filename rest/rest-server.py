from flask import Flask, request, Response, send_file
import os
import redis
import jsonpickle
import hashlib
from minio import Minio
import base64

# Redis setup
redis_url = os.getenv('REDISTOGO_URL') or 'localhost'
redis_port = os.getenv('REDISTOGO_PORT') or 6379
# redis_client = redis.StrictRedis(host=redis_url, port=redis_port, db=0)
redis_client = redis.Redis(host=redis_url, db=0)

# Minio setup
minio_url = os.getenv("MINIOTOGO_HOST") or "localhost:9000"
minio_user = os.getenv("MINIO_USER") or "rootuser"
minio_pwd = os.getenv("MINIO_PASSWD") or "rootpass123"
minio_client = Minio(minio_url, secure=False, access_key=minio_user, secret_key=minio_pwd)


            
# infoKey = "{}.rest.info".format(platform.node())
# debugKey = "{}.rest.debug".format(platform.node())



# def log_debug(message, key=debugKey):
#     print("DEBUG:", message, file=sys.stdout)
#     # redisClient = redis.StrictRedis(host=redisHost, port=redisPort, db=0)
#     redisClient.lpush('logging', f"{debugKey}:{message}")

# def log_info(message, key=infoKey):
#     print("INFO:", message, file=sys.stdout)
#     # redisClient = redis.StrictRedis(host=redisHost, port=redisPort, db=0)
#     redisClient.lpush('logging', f"{infoKey}:{message}")


def redis_list():
    queue_list = redis_client.lrange("toWorker", 0, -1)
    result = []
    for i in queue_list:
        result.append(i.decode())
    return result

        

# intialize the application
app = Flask(__name__)

@app.route('/', methods=['GET'])
def hello():
    return '<h1> Music Separation Server</h1><p> Use a valid endpoint </p>'

@app.route('/apiv1/separate', methods=['POST'])
def separate():
    bucket_name = "queues"
    try:
        resp = request.get_json()
        song_details = resp['callback']['data']['mp3']
        print(song_details)
        hash_object = hashlib.sha256(song_details.encode())
        hex_dig = hash_object.hexdigest()

        redis_queue = redis_list()

        if str(hex_dig)  not in redis_queue:
            file_name = str(hex_dig)+".mp3"
            song = base64.b64decode(resp['mp3'])
            file = open(file_name, "wb")
            file.write(song)

            check_if_buck_present = minio_client.bucket_exists(bucket_name)
            if not check_if_buck_present:
                minio_client.make_bucket(bucket_name)
            
            minio_client.fput_object(bucket_name, str(hex_dig)+".mp3", file_name ,content_type='audio/mpeg')
            redis_client.rpush('toWorker',str(hex_dig))
            os.remove(file_name)
            response = {
                "hash" : str(hex_dig),
                "reason" : "Song enqueued for separation"
            }
        else:
            response = {
                "RedFlag" : "Mp3 is already in the queue and separated"
            }
    except Exception as e:
        print(e)
        response = {'error': 'Could not process the request'}
    
    response_pickled = jsonpickle.encode(response)
    return Response(response=response_pickled, status=200,mimetype="application/json")
    

@app.route('/apiv1/queue', methods=['GET'])
def queue():
    try: 
        result = redis_list()
    
        response = {
            "queue" : result
        }
    except Exception as e:
        print(e)
        response = {
            "queue" :  "Error occured while displaying the queue"
        }

    response_pickled = jsonpickle.encode(response)
    return Response(response=response_pickled, status=200,mimetype="application/json")


@app.route('/apiv1/remove/<string:hash>/<string:track>', methods=['GET'])
def remove(hash, track):
    if track not in ["bass", "drums", "vocals", "other"]:
        return Response(response = jsonpickle.encode({"response" : f"Track type {track}unknown"}),
        status =400, mimetype="application/json")
    else:
        object_name = f"{hash}/{track}.mp3"
        try:
            minio_client.remove_object("output", object_name)
            return Response(response = jsonpickle.encode({"response" : f"Removed track {track} from {hash}"}), status=200,
            mimetype="application/json")
        except Exception as exp:
            print(exp)
            return Response(response = jsonpickle.encode({"response" : f"Unable to remove track {track} from {hash}"}), status=400,
            mimetype="application/json")


@app.route('/apiv1/track/<string:hash>/<string:track>', methods=['GET'])
def track(hash, track):
    if track not in ["bass", "drums", "vocals", "other"]:
        return Response(response = jsonpickle.encode({"track" : f"Track type {track}unknown"}), status=400, mimetype="application/json")
    else:
        object_name = f"{hash}/{track}.mp3"
        minio_client.fget_object("output", object_name, object_name)
        return send_file(object_name,as_attachment=True)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)