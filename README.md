# Gallery - Image and Video Collection Viewer

A Flask-based web application for managing and viewing collections of images and videos with an intuitive interface and interactive features.

## Features

- **Drag & Drop Upload**: Upload multiple images and videos simultaneously (up to 2GB per file)
- **Masonry Gallery**: Beautiful responsive layout displaying 10 random files
- **Random Viewer**: Single file viewer with like/dislike functionality
- **Compare Mode**: Side-by-side comparison with ELO-based rating system
- **Dual Rating System**: ELO ratings from comparisons + direct like/dislike counts
- **Adventure Mode**: Sequential media slideshow with customizable parameters
- **Video Editing**: Basic trimming functionality for video files
- **File Management**: Delete files directly from fullscreen view
- **Tag System**: Automatic tag generation and manual tag management
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
- Paginate through results using Prev/Next or page selector when more than one page is available
- Keyboard navigation in fullscreen: Left/Right arrows cycle through currently loaded page items

### Random Viewer
- Navigate to the Random Viewer page
- Use thumbs up/down buttons to rate files
- After each rating, a new random file automatically loads

### Compare Mode
- Side-by-side comparison of two random files
- Vote for your preferred file using ELO rating algorithm
- ELO ratings adjust based on expected vs actual outcomes (standard K-factor of 32)
- Optional "matching types" mode (images vs images, videos vs videos)
- "King of the Hill" mode where winner stays and only loser is replaced
- Like/dislike counts remain independent from comparison votes

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
- `like_count`: Integer counter for direct likes/dislikes (can be negative)
- `elo_rating`: ELO rating from comparisons (default 1500)
- `created_at`: Upload timestamp
- `file_path`: Full path to stored file
- `file_size`: Size in bytes
- `file_hash`: SHA-256 hash for duplicate detection

## Development

### Adding New Features
The application is designed to be easily extensible:
- Add new routes in `app.py`
- Create corresponding templates in `templates/`
- Use HTMX attributes for dynamic interactions
- Follow Flask best practices for database operations

### API Endpoints
- `GET /api/random-file`: Get random file data
- `POST /api/like/<id>`: Increase like count (independent from ELO)
- `POST /api/dislike/<id>`: Decrease like count (independent from ELO)
- `POST /api/vote/<winner_id>/<loser_id>`: Update ELO ratings based on comparison
- `GET /api/refresh-gallery`: Get new random gallery grid
- `POST /upload`: Handle file uploads
- `GET /?page=N` / `GET /api/refresh-gallery?page=N`: Paginated gallery data (combine with type, count, sort, tag)
- `GET /api/export-likes`: Download a CSV file with current like counts and ELO ratings
- `POST /api/reset-likes`: Reset all like counts to zero
- `POST /api/reset-elo`: Reset all ELO ratings to 1500

## Configuration

The application uses the following default settings:
- Database: SQLite file in project root
- Upload folder: `./uploads`
- Max file size: 100MB
- Debug mode: Enabled (development only)

### Feature Toggles

You can enable or disable entire views/features via a JSON configuration file `config.json` placed in the project root (already created by default). Override the path using the `GALLERY_CONFIG` environment variable if needed.

Example `config.json`:

```json
{
  "features": {
    "adventure": false,
    "compare": true,
    "random": true,
    "upload": true,
    "video_edit": true,
    "tag_edit": true
  }
}
```

Available feature keys:

- `adventure` – Adventure slideshow view and its API
- `compare` – Compare view and vote endpoints
- `random` – Random viewer page
- `upload` – Upload UI and `/api/upload` endpoint (currently only hides nav/UI; you may self-guard the route if desired)
- `video_edit` – Video trimming interface
- `tag_edit` – Tag editing controls in file edit views

Disabled features:
1. Navigation links are hidden automatically.
2. Protected routes (e.g. `adventure`) return `404` JSON error when disabled.
3. Templates can check availability with `feature_enabled('feature_name')`.

To disable Adventure mode, set `"adventure": false` and restart the app. Visiting `/adventure` or calling `/api/adventure-start` will return a 404 response.

Environment override:

```bash
export GALLERY_CONFIG=/path/to/custom_config.json
python app.py
```

If the config file is missing or malformed, the app falls back to enabling all features by default.

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
## Pagination

The gallery supports page-based navigation. Parameters:

- `page`: 1-based page number (default: 1)
- `count`: items per page (10, 25, 50)
- `type`: `both`, `image`, or `video`
- `sort`: `newest`, `oldest`, `elo`, `top`, or `random`
- `tag`: optional tag name filter

Sort options:
- `elo`: Sort by ELO rating (highest first) - reflects comparison performance
- `top`: Sort by like count (most liked first) - reflects direct user feedback
- `newest` / `oldest`: Sort by upload date
- `random`: Random order

Example:

```
/?type=image&sort=elo&count=25&page=2
```

Fullscreen view supports keyboard navigation (ArrowLeft / ArrowRight) cycling within the currently loaded page.

## Rating System

The gallery uses a **dual rating system** that tracks quality in two independent ways:

### ELO Rating (Comparisons)
- **Purpose**: Measures relative quality through head-to-head comparisons
- **Default**: All files start at 1500 ELO
- **Algorithm**: Standard ELO system with K-factor of 32
  - When you choose a winner in Compare mode, both files' ratings adjust
  - Beating a higher-rated opponent gains more points
  - Losing to a lower-rated opponent loses more points
  - Expected score formula: `1 / (1 + 10^((opponent_rating - your_rating) / 400))`
- **Updates**: Only changes through `/api/vote` endpoint (Compare mode)
- **Use case**: "Which media is objectively better?"

### Like Count (Direct Feedback)
- **Purpose**: Tracks individual user sentiment
- **Default**: All files start at 0
- **Range**: Can be positive (net likes) or negative (net dislikes)
- **Updates**: Changes through thumbs up/down in Random Viewer or Gallery
  - `/api/like/<id>`: +1 to like_count
  - `/api/dislike/<id>`: -1 to like_count
- **Independent**: Not affected by comparison votes
- **Use case**: "Do I personally like this media?"

### Why Both?

- **ELO** gives you a ranking based on comparative quality across your entire collection
- **Like Count** lets you quickly favorite items or mark ones you dislike
- Sort by ELO to see your "best" media; sort by "Most Liked" to see your favorites
- Both metrics are displayed together on every media item (star icon for ELO, thumbs up for likes)

## Like Count Export & Reset

You can export the current like counts and ELO ratings for all media files and optionally reset them.

### Export CSV

Downloads a file `media_likes.csv` containing columns:

`id, original_filename, filename, file_type, like_count, elo_rating, created_at`

Example:

```bash
curl -o media_likes.csv http://localhost:5002/api/export-likes
```

### Reset All Like Counts

Sets every `MediaFile.like_count` to `0`.

```bash
curl -X POST http://localhost:5002/api/reset-likes
```

Response: `{"success": true, "affected": <number>, "message": "Reset like counts for <number> media files."}`

### Reset All ELO Ratings

Sets every `MediaFile.elo_rating` to `1500` (the default starting rating).

```bash
curl -X POST http://localhost:5002/api/reset-elo
```

Response: `{"success": true, "affected": <number>, "message": "Reset ELO ratings for <number> media files."}`


- Trim video files by specifying start and end points
- Preview video trimming results before saving
- Supported formats: MP4, AVI, MOV, WebM, MKV
