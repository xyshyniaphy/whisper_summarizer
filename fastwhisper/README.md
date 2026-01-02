# fastwhisper Base Image

This directory contains the Dockerfile for the base image used by the backend service.

## What's Included

The `whisper-summarizer-fastwhisper-base:latest` image contains:

- **NVIDIA CUDA 12.9.1 cuDNN Runtime** - GPU acceleration support
- **Python 3.12** with `uv` package manager
- **faster-whisper** library with pre-downloaded `large-v3-turbo` model (~3GB)
- **CJK fonts** for Chinese/Japanese/Korean character support

## Build the Base Image

```bash
# From project root
./build_fastwhisper_base.sh

# Or manually
docker build -t whisper-summarizer-fastwhisper-base:latest -f fastwhisper/Dockerfile .
```

## Build Time

- **First build**: ~10-15 minutes (downloads ~3GB model + dependencies)
- **Subsequent builds**: Uses Docker cache, much faster

## Image Size

Approximately **5-7 GB** (includes CUDA cuDNN runtime + 3GB model)

## Why a Separate Base Image?

1. **Faster backend rebuilds**: Model is pre-downloaded, no need to download on each build
2. **Consistent environment**: Same base for development and production
3. **Versioning**: Can tag different versions of the base image for rollbacks
4. **Resource savings**: Model download happens once during base image build, not on every backend build

## Updating the Base Image

If you need to update the model or dependencies:

```bash
# Rebuild without cache
docker build --no-cache -t whisper-summarizer-fastwhisper-base:latest -f fastwhisper/Dockerfile .
```

## Backend Usage

The backend Dockerfile uses this base image:

```dockerfile
ARG BASE_IMAGE=whisper-sumisper-fastwhisper-base:latest
FROM ${BASE_IMAGE}
```

You can override the base image at build time:

```bash
docker build --build-arg BASE_IMAGE=whisper-summarizer-fastwhisper-base:v1.0.0 -t backend:test .
```
