"""Local-mode backends — no MuAPI calls, runs on your machine.

Used when the pipeline is invoked with mode="local". Requires the optional
deps in requirements-local.txt (yt-dlp, faster-whisper, openai,
opencv, moviepy) plus an OpenAI key or a running Ollama server for highlight ranking.
"""
