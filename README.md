# Gallery - Image and Video Collection Viewer

A Flask-based web application for managing and viewing collections of images and videos with an intuitive interface and interactive features.

## Features

- **Drag & Drop Upload**: Upload multiple images and videos simultaneously (up to 2GB per file)
- **Masonry Gallery**: Beautiful responsive layout displaying 10 random files
- **Random Viewer**: Single file viewer with like/dislike functionality
- **Compare Mode**: Side-by-side comparison with voting and King of the Hill mode
- **Adventure Mode**: Sequential media slideshow with customizable parameters
- **Video Editing**: Basic trimming functionality for video files
- **File Management**: Delete files directly from fullscreen view
- **Like System**: Track preferences with positive/negative counters
- **Organized Storage**: Files automatically organized into subfolders for better performance
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Real-time Updates**: Smooth interactions powered by HTMX

## Quick Start

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python app.py
```

3. Open your browser and navigate to `http://localhost:5000`

## Usage

### Uploading Files
- Visit the main gallery page
- Drag and drop images/videos onto the upload area, or click to select files
- Supported formats: Images (JPG, PNG, GIF, WebP, BMP) and Videos (MP4, AVI, MOV, WebM, MKV)

### Gallery View
- Browse 10 randomly selected files in a masonry layout
- Click "Refresh Gallery" to load 10 new random files
- View file names, types, and current like counts

### Random Viewer
- Navigate to the Random Viewer page
- Use thumbs up/down buttons to rate files
- After each rating, a new random file automatically loads

### Compare Mode
- Side-by-side comparison of two random files
- Vote for your preferred file (winner gets +1, loser gets -1)
- Optional "matching types" mode (images vs images, videos vs videos)
- "King of the Hill" mode where winner stays and only loser is replaced

### Adventure Mode
- Sequential slideshow experience with customizable parameters:
  - **Popularity Level**: Set minimum like count for included media
  - **Number of Steps**: Choose how many files to display (1-100)
  - **File Type**: Filter by images, videos, or both
- Automatic progression: Images display for 3 seconds, videos play until completion
- Fullscreen viewing available by clicking on media
- Pause/resume and stop controls
- Progress tracking with visual progress bar

## Technology Stack

- **Backend**: Flask 3.0.0 with SQLAlchemy ORM
- **Database**: SQLite (no setup required)
- **Frontend**: HTML templates with Tailwind CSS
- **Interactions**: HTMX for dynamic updates
- **File Processing**: Pillow and python-magic for file handling

## Project Structure

```
gallery/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── templates/            # Jinja2 templates
│   ├── base.html         # Base template with navigation
│   ├── gallery.html      # Main gallery page
│   ├── gallery_grid.html # Gallery grid component
│   └── random_viewer.html # Random file viewer
├── uploads/              # Uploaded files storage (created automatically)
└── gallery.db           # SQLite database (created automatically)
```

## Database Schema

### MediaFile Model
- `id`: Primary key
- `filename`: Unique filename for storage
- `original_filename`: Original uploaded filename
- `file_type`: 'image' or 'video'
- `like_count`: Integer counter (can be negative)
- `created_at`: Upload timestamp
- `file_path`: Full path to stored file

## Development

### Adding New Features
The application is designed to be easily extensible:
- Add new routes in `app.py`
- Create corresponding templates in `templates/`
- Use HTMX attributes for dynamic interactions
- Follow Flask best practices for database operations

### API Endpoints
- `GET /api/random-file`: Get random file data
- `POST /api/like/<id>`: Increase like count
- `POST /api/dislike/<id>`: Decrease like count
- `GET /api/refresh-gallery`: Get new random gallery grid
- `POST /upload`: Handle file uploads

## Configuration

The application uses the following default settings:
- Database: SQLite file in project root
- Upload folder: `./uploads`
- Max file size: 100MB
- Debug mode: Enabled (development only)

## Security Notes

For production use, consider:
- Changing the SECRET_KEY
- Implementing user authentication
- Adding file type validation
- Setting up proper file permissions
- Using a production WSGI server

## License

This project is open source and available under the MIT License.

## File Management
- **Delete Files**: Remove files permanently from fullscreen view with confirmation dialog
- **Organized Storage**: Files are automatically organized into subfolders (first 2 characters of filename)
- **Large File Support**: Upload files up to 2GB in size
- **Duplicate Prevention**: Automatically detects and prevents duplicate uploads based on filename and size

## Video Editing
- Trim video files by specifying start and end points
- Preview video trimming results before saving
- Supported formats: MP4, AVI, MOV, WebM, MKV
