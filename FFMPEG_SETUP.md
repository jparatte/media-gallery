# Video Editor Setup

## FFmpeg Installation

The video editing feature requires FFmpeg to be installed on your system.

### macOS
```bash
# Using Homebrew
brew install ffmpeg
```

### Ubuntu/Debian
```bash
sudo apt update
sudo apt install ffmpeg
```

### Windows
1. Download FFmpeg from https://ffmpeg.org/download.html
2. Extract and add to PATH environment variable

### Verify Installation
```bash
ffmpeg -version
```

## Usage

1. Navigate to the Gallery view
2. Click on any video to open fullscreen mode
3. Click the "Edit" button (only visible for videos)
4. Use the video editor to:
   - Set start and end times for your clip
   - Preview the selected portion
   - Choose whether to keep or delete the original
   - Save the trimmed video

The new video will inherit the like count from the original and be saved with a descriptive filename.
