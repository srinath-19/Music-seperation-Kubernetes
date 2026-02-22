# Music Separation on Kubernetes

![Music separation architecture](images/music_separation.png)

This repository contains my Kubernetes-based **Music-Separation-as-a-Service (MSaaS)** project. I built a containerized pipeline that accepts audio files, queues processing jobs, separates tracks with Demucs, and stores results in object storage for retrieval.

## Project Overview

I implemented this system as a set of cooperating services:

- **rest**: API frontend that accepts analysis requests and query operations, then enqueues work in Redis. See [rest/README.md](rest/README.md).
- **worker**: Background processor that consumes queued jobs, runs source separation, and uploads output tracks to object storage. See [worker/README.md](worker/README.md).
- **redis**: Queue and lightweight coordination backend. See [redis/README.md](redis/README.md).
- **minio**: S3-compatible object storage used for input and output assets. See [minio/README.md](minio/README.md).
- **logs**: Optional log subscriber service for runtime debugging. See [logs/README.md](logs/README.md).

## Source Separation Model

The worker uses [Demucs](https://github.com/facebookresearch/demucs), an open-source waveform source separation model from Meta/Facebook Research. Because inference is compute and memory intensive, jobs run asynchronously through the queue.

## Architecture and Data Flow

1. A client submits an audio request to the REST API.
2. The REST service stores request metadata and pushes a job onto a Redis list.
3. A worker consumes the queued task and downloads the source object from MinIO.
4. Demucs generates separated stems.
5. The worker uploads generated tracks to the output bucket.
6. The client retrieves output metadata or downloads separated files.

## Storage Layout

I use two buckets:

- `queue`: source audio objects to process.
- `output`: separated stems named like `<songhash>-<track>.mp3`.

![Buckets](images/buckets.png)
![Output bucket example](images/output-bucket.png)

## Running Locally for Development

I included a convenience script to deploy foundational services and enable port-forwarding:

```bash
./deploy-local-dev.sh
```

This helps me iterate on `rest` and `worker` code locally while still using Kubernetes-hosted Redis and MinIO.

### Manual Port-Forwarding Example

```bash
kubectl port-forward --address 0.0.0.0 service/redis 6379:6379 &
kubectl port-forward --namespace minio-ns svc/myminio-proj 9000:9000 &
```

With these forwards active, local services can connect to `localhost:6379` (Redis) and `localhost:9000` (MinIO).

## Resource Notes

Demucs can require significant memory (often multiple GB depending on clip length and model settings). During early testing, I recommend:

- starting with short samples,
- running a single worker,
- monitoring pod resource usage with `kubectl describe node` and pod logs.

## Sample Requests

I included helper clients for exercising the API:

- `sample-requests.py`
- `short-sample-request.py`

Use short clips first to validate the end-to-end path before scaling to larger files.

## Deployment Notes

For repeatable Kubernetes rollouts, I prefer versioned container image tags over `latest`. In an edit/deploy/debug loop, update the image tag and restart or redeploy pods to ensure new code is running.
