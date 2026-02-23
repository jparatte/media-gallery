import os
import uuid
import shutil
import hashlib
import json
import csv
import io
from datetime import datetime
from flask import Flask, request, render_template, jsonify, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import magic
from PIL import Image

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'dev-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gallery.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB max file size

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database
db = SQLAlchemy(app)

# Feature configuration loading
def load_config():
    """Load gallery configuration JSON. Path can be overridden with GALLERY_CONFIG env var."""
    default_path = os.environ.get('GALLERY_CONFIG', os.path.join(os.path.dirname(__file__), 'config.json'))
    try:
        with open(default_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Config file not found at {default_path}, using defaults.")
        return { 'features': {} }
    except json.JSONDecodeError as e:
        print(f"Malformed config file {default_path}: {e}. Using empty config.")
        return { 'features': {} }

CONFIG = load_config()

def feature_enabled(name: str, default: bool = True) -> bool:
    """Check if a feature is enabled, defaulting to True if not specified."""
    features = CONFIG.get('features', {})
    value = features.get(name)
    if value is None:
        return default
    return bool(value)

@app.context_processor
def inject_feature_helper():
    """Inject feature_enabled helper into templates."""
    return {'feature_enabled': feature_enabled}

# Models
class MediaFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(10), nullable=False)
    like_count = db.Column(db.Integer, default=0)
    elo_rating = db.Column(db.Integer, default=1500)  # ELO rating for comparisons
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False, default=0)
    file_hash = db.Column(db.String(64), nullable=True, index=True)  # SHA-256 hash for duplicate detection
    
    # Add the tags relationship
    tags = db.relationship('Tag', secondary='file_tags', lazy='subquery', 
                          backref=db.backref('files', lazy=True))
    
    def __repr__(self):
        return f'<MediaFile {self.original_filename}>'

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Tag {self.name}>'

# Association table for many-to-many relationship between MediaFile and Tag
file_tags = db.Table('file_tags',
    db.Column('file_id', db.Integer, db.ForeignKey('media_file.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

# Helper functions
def get_file_type(file_path):
    """Determine if file is image or video using python-magic"""
    try:
        mime = magic.from_file(file_path, mime=True)
        if mime.startswith('image/'):
            return 'image'
        elif mime.startswith('video/'):
            return 'video'
        else:
            # If magic fails, fallback to extension-based detection
            return get_file_type_by_extension(file_path)
    except Exception as e:
        print(f"Magic detection failed for {file_path}: {str(e)}")
        # Fallback to extension-based detection
        return get_file_type_by_extension(file_path)

def get_file_type_by_extension(file_path):
    """Fallback method to determine file type by extension"""
    ext = os.path.splitext(file_path)[1].lower()
    image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.svg'}
    video_exts = {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv', '.m4v', '.3gp', '.ogv'}
    
    if ext in image_exts:
        return 'image'
    elif ext in video_exts:
        return 'video'
    return None

def save_uploaded_file(file):
    """Save uploaded file and return file info"""
    try:
        if file.filename == '':
            return None
        
        # Calculate file size before saving
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        # Generate unique filename
        file_ext = os.path.splitext(secure_filename(file.filename))[1]
        unique_filename = f"{uuid.uuid4().hex}{file_ext}"
        
        # Create subfolder based on first 2 characters of filename
        subfolder = get_file_subfolder(unique_filename)
        subfolder_path = ensure_subfolder_exists(subfolder)
        
        # Build relative path for database storage
        relative_path = os.path.join(subfolder, unique_filename)
        full_file_path = os.path.join(subfolder_path, unique_filename)
        
        # Save file
        file.save(full_file_path)
        
        # Calculate file hash for duplicate detection
        file_hash = calculate_file_hash(full_file_path)
        if not file_hash:
            # If hash calculation fails, clean up and skip
            os.remove(full_file_path)
            return None
        
        # Check for duplicate based on file hash (more reliable than filename+size)
        existing_file = MediaFile.query.filter_by(file_hash=file_hash).first()
        if existing_file:
            # Remove the newly uploaded file since it's a duplicate
            os.remove(full_file_path)
            return None  # Skip duplicate file
        
        # Determine file type
        file_type = get_file_type(full_file_path)
        if file_type is None:
            # Delete invalid file
            os.remove(full_file_path)
            return None
        
        return {
            'filename': relative_path,  # Store relative path with subfolder
            'original_filename': file.filename,
            'file_type': file_type,
            'file_path': full_file_path,
            'file_size': file_size,
            'file_hash': file_hash
        }
    except Exception as e:
        # Log the error and return None
        print(f"Error saving file {file.filename}: {str(e)}")
        return None

def get_file_subfolder(filename):
    """Get subfolder based on first 2 characters of filename"""
    return filename[:2] if len(filename) >= 2 else '00'

def ensure_subfolder_exists(subfolder_name):
    """Create subfolder if it doesn't exist"""
    subfolder_path = os.path.join(app.config['UPLOAD_FOLDER'], subfolder_name)
    os.makedirs(subfolder_path, exist_ok=True)
    return subfolder_path

# Routes
@app.route('/')
def index():
    """Main gallery page with configurable filters"""
    # Get filter parameters from URL
    file_type = request.args.get('type', 'both')
    count = int(request.args.get('count', 25))
    sort_type = request.args.get('sort', 'newest')
    tag_filter = request.args.get('tag', '')  # Add tag filter
    page = int(request.args.get('page', 1))
    
    # Build base query
    query = MediaFile.query
    
    # Apply file type filter
    if file_type != 'both':
        query = query.filter(MediaFile.file_type == file_type)
    
    # Apply tag filter if specified
    if tag_filter:
        query = query.join(MediaFile.tags).filter(Tag.name == tag_filter.lower())
    
    # Apply sorting
    if sort_type == 'top':
        query = query.order_by(MediaFile.like_count.desc())
    elif sort_type == 'elo':
        query = query.order_by(MediaFile.elo_rating.desc())
    elif sort_type == 'newest':
        query = query.order_by(MediaFile.created_at.desc())
    elif sort_type == 'oldest':
        query = query.order_by(MediaFile.created_at.asc())
    else:  # random
        query = query.order_by(db.func.random())
    
    # Get total file count before pagination
    total_files = query.count()
    if count < 1:
        count = 25
    # Calculate total pages (at least 1)
    total_pages = max(1, (total_files + count - 1) // count)
    # Clamp page inside range
    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages

    # Apply pagination
    files = query.offset((page - 1) * count).limit(count).all()
    
    # Get all available tags for the filter dropdown
    available_tags = Tag.query.order_by(Tag.name).all()
    
    return render_template('gallery.html', 
                         files=files,
                         available_tags=available_tags,
                         current_type=file_type,
                         current_count=count,
                         current_sort=sort_type,
                         current_tag=tag_filter,
                         current_page=page,
                         total_pages=total_pages,
                         total_files=total_files)

@app.route('/random')
def random_viewer():
    """Single random file viewer for like/dislike"""
    return render_template('random_viewer.html')

@app.route('/api/random-file')
def get_random_file():
    """API endpoint to get a random file"""
    random_file = MediaFile.query.order_by(db.func.random()).first()
    if random_file:
        return jsonify({
            'id': random_file.id,
            'filename': random_file.filename,
            'original_filename': random_file.original_filename,
            'file_type': random_file.file_type,
            'like_count': random_file.like_count
        })
    return jsonify({'error': 'No files found'}), 404

@app.route('/api/random-file-html')
def get_random_file_html():
    """API endpoint to get a random file as HTML for HTMX"""
    random_file = MediaFile.query.order_by(db.func.random()).first()
    if random_file:
        return render_template('random_file_display.html', file=random_file)
    return render_template('no_files.html')

@app.route('/api/like/<int:file_id>', methods=['POST'])
def like_file(file_id):
    """Increase like count for a file"""
    file = MediaFile.query.get_or_404(file_id)
    file.like_count += 1
    db.session.commit()
    return jsonify({'like_count': file.like_count})

@app.route('/api/dislike/<int:file_id>', methods=['POST'])
def dislike_file(file_id):
    """Decrease like count for a file"""
    file = MediaFile.query.get_or_404(file_id)
    file.like_count -= 1
    db.session.commit()
    return jsonify({'like_count': file.like_count})

# Update the upload route
@app.route('/api/upload', methods=['POST'])
def upload_files():
    try:
        files = request.files.getlist('files[]')
        
        if not files:
            return jsonify({'success': False, 'message': 'No files provided'})
        
        uploaded_files = []
        skipped_files = []
        
        for file in files:
            file_info = save_uploaded_file(file)
            if file_info:
                # Create tags from filename
                tags = create_tags_from_filename(file_info['original_filename'])
                
                # Create MediaFile with auto-generated tags
                media_file = MediaFile(
                    filename=file_info['filename'],
                    original_filename=file_info['original_filename'], 
                    file_type=file_info['file_type'],
                    file_path=file_info['file_path'],
                    file_size=file_info['file_size'],
                    file_hash=file_info['file_hash'],
                    tags=tags
                )
                
                db.session.add(media_file)
                uploaded_files.append(file_info['original_filename'])
            else:
                skipped_files.append(file.filename)
        
        db.session.commit()
        
        message = f"Successfully uploaded {len(uploaded_files)} files!"
        if skipped_files:
            message += f" Skipped {len(skipped_files)} duplicate files"
            if len(skipped_files) <= 3:
                # Show filenames if only a few duplicates
                message += f": {', '.join(skipped_files)}"
            message += "."
        
        return jsonify({'success': True, 'message': message})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Upload failed: {str(e)}'})

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Serve uploaded files (supports subfolders)"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/refresh-gallery')
def refresh_gallery():
    """Refresh gallery with current filters"""
    file_type = request.args.get('type', 'both')
    count = int(request.args.get('count', 25))
    sort_type = request.args.get('sort', 'newest')
    tag_filter = request.args.get('tag', '')  # Add tag filter
    page = int(request.args.get('page', 1))
    
    # Build query with same logic as index route
    query = MediaFile.query
    
    if file_type != 'both':
        query = query.filter(MediaFile.file_type == file_type)
    
    if tag_filter:
        query = query.join(MediaFile.tags).filter(Tag.name == tag_filter.lower())
    
    if sort_type == 'top':
        query = query.order_by(MediaFile.like_count.desc())
    elif sort_type == 'elo':
        query = query.order_by(MediaFile.elo_rating.desc())
    elif sort_type == 'newest':
        query = query.order_by(MediaFile.created_at.desc())
    elif sort_type == 'oldest':
        query = query.order_by(MediaFile.created_at.asc())
    else:
        query = query.order_by(db.func.random())
    
    # Total files for pagination
    total_files = query.count()
    if count < 1:
        count = 25
    total_pages = max(1, (total_files + count - 1) // count)
    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages

    files = query.offset((page - 1) * count).limit(count).all()

    return render_template('gallery_grid.html', 
                           files=files,
                           current_page=page,
                           total_pages=total_pages,
                           total_files=total_files)

@app.route('/compare')
def compare_view():
    """Compare view for side-by-side file comparison"""
    return render_template('compare.html')

@app.route('/api/compare-files')
def get_compare_files():
    """API endpoint to get two random files for comparison"""
    matching_types = request.args.get('matching_types', 'false').lower() == 'true'
    
    if matching_types:
        # Get a random file type first, then get two files of that type
        available_types = db.session.query(MediaFile.file_type).distinct().all()
        if not available_types:
            return jsonify({'error': 'No files found'}), 404
        
        # Pick a random type
        import random
        random_type = random.choice(available_types)[0]
        
        # Get two random files of the same type
        files = MediaFile.query.filter(MediaFile.file_type == random_type).order_by(db.func.random()).limit(2).all()
    else:
        # Get any two random files
        files = MediaFile.query.order_by(db.func.random()).limit(2).all()
    
    if len(files) < 2:
        return jsonify({'error': 'Need at least 2 files for comparison'}), 404
    
    return jsonify({
        'file1': {
            'id': files[0].id,
            'filename': files[0].filename,
            'original_filename': files[0].original_filename,
            'file_type': files[0].file_type,
            'like_count': files[0].like_count,
            'created_at': files[0].created_at.strftime('%b %d, %Y at %I:%M %p')
        },
        'file2': {
            'id': files[1].id,
            'filename': files[1].filename,
            'original_filename': files[1].original_filename,
            'file_type': files[1].file_type,
            'like_count': files[1].like_count,
            'created_at': files[1].created_at.strftime('%b %d, %Y at %I:%M %p')
        }
    })

@app.route('/api/compare-files-html')
def get_compare_files_html():
    """API endpoint to get two random files as HTML for HTMX"""
    matching_types = request.args.get('matching_types', 'false').lower() == 'true'
    
    if matching_types:
        # Get a random file type first, then get two files of that type
        available_types = db.session.query(MediaFile.file_type).distinct().all()
        if not available_types:
            return render_template('no_files.html')
        
        # Pick a random type
        import random
        random_type = random.choice(available_types)[0]
        
        # Get two random files of the same type
        files = MediaFile.query.filter(MediaFile.file_type == random_type).order_by(db.func.random()).limit(2).all()
    else:
        # Get any two random files
        files = MediaFile.query.order_by(db.func.random()).limit(2).all()
    
    if len(files) < 2:
        return render_template('no_files.html')
    
    return render_template('compare_display.html', file1=files[0], file2=files[1])

@app.route('/api/vote/<int:winner_id>/<int:loser_id>', methods=['POST'])
def vote_compare(winner_id, loser_id):
    """Handle voting in compare view - update ELO ratings based on comparison"""
    winner = MediaFile.query.get_or_404(winner_id)
    loser = MediaFile.query.get_or_404(loser_id)
    
    # Calculate new ELO ratings
    winner_new_elo, loser_new_elo = calculate_elo_change(winner.elo_rating, loser.elo_rating)
    
    winner.elo_rating = winner_new_elo
    loser.elo_rating = loser_new_elo
    
    db.session.commit()
    
    # Check if this is king of the hill mode
    data = request.get_json() or {}
    king_of_hill = data.get('king_of_hill', False)
    matching_types = data.get('matching_types', False)
    
    response_data = {
        'success': True,
        'winner_elo': winner.elo_rating,
        'loser_elo': loser.elo_rating,
        'winner_likes': winner.like_count,
        'loser_likes': loser.like_count
    }
    
    # If king of hill mode, return HTML with winner + new challenger
    if king_of_hill:
        # Find a new challenger (excluding the winner)
        if matching_types:
            # Get a challenger of the same type as the winner
            challenger = MediaFile.query.filter(
                MediaFile.file_type == winner.file_type,
                MediaFile.id != winner.id
            ).order_by(db.func.random()).first()
        else:
            # Get any challenger except the winner
            challenger = MediaFile.query.filter(
                MediaFile.id != winner.id
            ).order_by(db.func.random()).first()
        
        if challenger:
            # Generate new comparison HTML
            html = render_template('compare_display.html', file1=winner, file2=challenger)
            response_data['html'] = html
        else:
            # No challenger found, fall back to regular refresh mode
            response_data['html'] = None
    
    return jsonify(response_data)

@app.route('/edit/<int:file_id>')
def edit_file(file_id):
    """Edit view for files - video editing for videos, metadata editing for all files"""
    file = MediaFile.query.get_or_404(file_id)
    
    # Get all available tags for autocomplete
    all_tags = Tag.query.order_by(Tag.name).all()
    
    # Check if we want video editing interface specifically
    video_edit = request.args.get('video_edit', 'false').lower() == 'true'
    
    if file.file_type == 'video' and video_edit:
        return render_template('video_edit.html', file=file, all_tags=all_tags)
    else:
        return render_template('file_edit.html', file=file, all_tags=all_tags)

@app.route('/api/trim-video/<int:file_id>', methods=['POST'])
def trim_video(file_id):
    """Trim a video and save the result"""
    try:
        file = MediaFile.query.get_or_404(file_id)
        if file.file_type != 'video':
            return jsonify({'error': 'File is not a video'}), 400
        
        data = request.get_json()
        start_time = float(data.get('start_time', 0))
        end_time = float(data.get('end_time', 0))
        keep_original = data.get('keep_original', True)
        
        if start_time >= end_time:
            return jsonify({'error': 'Start time must be less than end time'}), 400
        
        # Generate new filename for the trimmed video
        original_name, ext = os.path.splitext(file.original_filename)
        new_original_name = f"{original_name}_trimmed_{start_time:.1f}s-{end_time:.1f}s{ext}"
        new_filename = f"{uuid.uuid4().hex}{ext}"
        new_file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
        
        # Use FFmpeg to trim the video
        import subprocess
        cmd = [
            'ffmpeg', '-y',  # -y to overwrite output file
            '-i', file.file_path,
            '-ss', str(start_time),
            '-t', str(end_time - start_time),
            '-c', 'copy',  # Copy streams without re-encoding for speed
            new_file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return jsonify({'error': f'FFmpeg error: {result.stderr}'}), 500
        
        # Get file size of the new video
        new_file_size = os.path.getsize(new_file_path)
        
        # Calculate hash for the new video
        new_file_hash = calculate_file_hash(new_file_path)
        
        # Create new database entry
        new_media_file = MediaFile(
            filename=new_filename,
            original_filename=new_original_name,
            file_type='video',
            file_path=new_file_path,
            file_size=new_file_size,
            file_hash=new_file_hash,
            like_count=file.like_count,  # Copy like count from original
            tags=list(file.tags)  # Copy tags from original video
        )
        db.session.add(new_media_file)
        
        # Handle original file deletion if requested
        if not keep_original:
            # Remove from filesystem
            if os.path.exists(file.file_path):
                os.remove(file.file_path)
            # Remove from database
            db.session.delete(file)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'new_file_id': new_media_file.id,
            'message': f'Video trimmed successfully! {"Original file removed." if not keep_original else "Original file kept."}'
        })
        
    except subprocess.CalledProcessError as e:
        return jsonify({'error': f'Video processing failed: {str(e)}'}), 500
    except Exception as e:
        print(f"Error trimming video: {str(e)}")
        return jsonify({'error': f'Error processing video: {str(e)}'}), 500

@app.route('/adventure')
def adventure_view():
    """Adventure view for sequential media display"""
    if not feature_enabled('adventure'):
        return jsonify({'error': 'Feature disabled'}), 404
    # Get like count range for risk level selection
    min_likes = db.session.query(db.func.min(MediaFile.like_count)).scalar() or 0
    max_likes = db.session.query(db.func.max(MediaFile.like_count)).scalar() or 0
    
    return render_template('adventure.html', min_likes=min_likes, max_likes=max_likes)

@app.route('/api/adventure-start', methods=['POST'])
def start_adventure():
    """Start an adventure with given parameters"""
    if not feature_enabled('adventure'):
        return jsonify({'error': 'Feature disabled'}), 404
    data = request.get_json()
    risk_level = int(data.get('risk_level', 0))
    steps = int(data.get('steps', 8))
    file_type = data.get('file_type', 'both')
    
    # Build query based on parameters
    query = MediaFile.query.filter(MediaFile.like_count >= risk_level)
    
    if file_type != 'both':
        query = query.filter(MediaFile.file_type == file_type)
    
    # Get enough files for the adventure, ordered by random
    files = query.order_by(db.func.random()).limit(steps).all()
    
    if len(files) < steps:
        return jsonify({
            'error': f'Not enough files matching criteria. Found {len(files)}, need {steps}',
            'success': False
        }), 400
    
    # Convert files to JSON
    adventure_files = []
    for file in files:
        adventure_files.append({
            'id': file.id,
            'filename': file.filename,
            'original_filename': file.original_filename,
            'file_type': file.file_type,
            'like_count': file.like_count,
            'created_at': file.created_at.strftime('%b %d, %Y at %I:%M %p')
        })
    
    return jsonify({
        'success': True,
        'files': adventure_files,
        'total_steps': steps,
        'risk_level': risk_level
    })

# Error handlers
@app.errorhandler(413)
def too_large(e):
    """Handle file too large error"""
    return jsonify({
        'error': 'File too large. Maximum file size is 500MB.',
        'success': False
    }), 413

@app.route('/api/delete/<int:file_id>', methods=['DELETE'])
def delete_file(file_id):
    """Delete a file from database and disk"""
    try:
        file = MediaFile.query.get_or_404(file_id)
        
        # Construct full file path
        full_file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        
        # Delete file from disk if it exists
        if os.path.exists(full_file_path):
            os.remove(full_file_path)
        
        # Delete from database
        db.session.delete(file)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'File "{file.original_filename}" deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to delete file: {str(e)}'
        }), 500

@app.route('/api/file/<int:file_id>/tags', methods=['POST'])
def add_tag_to_file(file_id):
    """Add a tag to a file"""
    try:
        file = MediaFile.query.get_or_404(file_id)
        data = request.get_json()
        tag_name = data.get('tag_name', '').strip().lower()
        
        if not tag_name:
            return jsonify({'success': False, 'error': 'Tag name is required'}), 400
        
        # Check if tag already exists on this file
        existing_tag = Tag.query.filter_by(name=tag_name).first()
        if existing_tag and existing_tag in file.tags:
            return jsonify({'success': False, 'error': 'Tag already exists on this file'}), 400
        
        # Find or create the tag
        tag = existing_tag or Tag(name=tag_name)
        if not existing_tag:
            db.session.add(tag)
        
        # Add tag to file
        file.tags.append(tag)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'tag': {'id': tag.id, 'name': tag.name},
            'message': f'Tag "{tag_name}" added successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Failed to add tag: {str(e)}'}), 500

@app.route('/api/file/<int:file_id>/tags/<int:tag_id>', methods=['DELETE'])
def remove_tag_from_file(file_id, tag_id):
    """Remove a tag from a file"""
    try:
        file = MediaFile.query.get_or_404(file_id)
        tag = Tag.query.get_or_404(tag_id)
        
        if tag not in file.tags:
            return jsonify({'success': False, 'error': 'Tag not found on this file'}), 404
        
        # Remove tag from file
        file.tags.remove(tag)
        
        # Check if this tag is now orphaned (no other files use it)
        if not tag.files:
            # No other files reference this tag, so delete it
            db.session.delete(tag)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Tag "{tag.name}" removed successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Failed to remove tag: {str(e)}'}), 500

@app.route('/api/tags/search')
def search_tags():
    """Search tags for autocomplete"""
    query = request.args.get('q', '').strip().lower()
    if not query:
        return jsonify([])
    
    tags = Tag.query.filter(Tag.name.like(f'%{query}%')).order_by(Tag.name).limit(10).all()
    return jsonify([{'id': tag.id, 'name': tag.name} for tag in tags])

@app.route('/api/cleanup-orphaned-tags', methods=['POST'])
def cleanup_orphaned_tags():
    """Remove tags that are not associated with any files"""
    try:
        # Find tags that have no associated files
        orphaned_tags = Tag.query.filter(~Tag.files.any()).all()
        
        count = len(orphaned_tags)
        for tag in orphaned_tags:
            db.session.delete(tag)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Cleaned up {count} orphaned tags'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Failed to cleanup tags: {str(e)}'}), 500

# Initialize database
with app.app_context():
    db.create_all()

# Helper functions for tags
def process_tags(tag_string):
    """Process comma-separated tag string and return list of Tag objects"""
    if not tag_string:
        return []
    
    tags = []
    tag_names = [name.strip().lower() for name in tag_string.split(',') if name.strip()]
    
    for tag_name in tag_names:
        # Find existing tag or create new one
        tag = Tag.query.filter_by(name=tag_name).first()
        if not tag:
            tag = Tag(name=tag_name)
            db.session.add(tag)
        tags.append(tag)
    
    return tags

def get_all_tags():
    """Get all tags for autocomplete/suggestions"""
    return Tag.query.order_by(Tag.name).all()

# Update the helper function to create tags from filename
def create_tags_from_filename(filename):
    """Create tags from filename by extracting meaningful words"""
    import re
    
    # Remove file extension
    name_without_ext = os.path.splitext(filename)[0]
    
    # Split by common delimiters and clean up
    words = re.split(r'[_\-\s\.]+', name_without_ext.lower())
    
    # Filter out short words, numbers, and common photo terms
    excluded_words = {'img', 'dsc', 'pic', 'photo', 'video', 'mov', 'vid', 'image', 'file'}
    meaningful_words = [
        word.strip() for word in words 
        if len(word) > 2 and not word.isdigit() and word not in excluded_words
    ]
    
    # Limit to first 5 meaningful words to avoid too many tags
    meaningful_words = meaningful_words[:5]
    
    tags = []
    for word in meaningful_words:
        if word:  # Make sure word is not empty
            # Find existing tag or create new one
            tag = Tag.query.filter_by(name=word).first()
            if not tag:
                tag = Tag(name=word)
                db.session.add(tag)
            tags.append(tag)
    
    return tags

def calculate_file_hash(file_path):
    """Calculate SHA-256 hash of a file efficiently for large files"""
    hash_sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            # Read file in 64KB chunks to handle large files efficiently
            for chunk in iter(lambda: f.read(65536), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except Exception as e:
        print(f"Error calculating hash for {file_path}: {str(e)}")
        return None

def calculate_elo_change(winner_rating, loser_rating, k_factor=32):
    """Calculate ELO rating changes for winner and loser.
    
    Args:
        winner_rating: Current ELO rating of the winner
        loser_rating: Current ELO rating of the loser
        k_factor: Maximum change in rating (default 32, standard for most systems)
    
    Returns:
        Tuple of (winner_new_rating, loser_new_rating)
    """
    # Expected scores
    expected_winner = 1 / (1 + 10 ** ((loser_rating - winner_rating) / 400))
    expected_loser = 1 / (1 + 10 ** ((winner_rating - loser_rating) / 400))
    
    # Actual scores (winner gets 1, loser gets 0)
    winner_new = winner_rating + k_factor * (1 - expected_winner)
    loser_new = loser_rating + k_factor * (0 - expected_loser)
    
    return round(winner_new), round(loser_new)

# --- Utility / Admin Endpoints ---
@app.route('/api/export-likes', methods=['GET'])
def export_likes():
    """Export current like counts for all media as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    # Header
    writer.writerow(['id', 'original_filename', 'filename', 'file_type', 'like_count', 'elo_rating', 'created_at'])
    for m in MediaFile.query.order_by(MediaFile.id).all():
        writer.writerow([
            m.id,
            m.original_filename,
            m.filename,
            m.file_type,
            m.like_count,
            m.elo_rating,
            m.created_at.isoformat()
        ])
    output.seek(0)
    return app.response_class(
        output.read(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename=media_likes.csv'
        }
    )

@app.route('/api/reset-likes', methods=['POST'])
def reset_likes():
    """Reset like_count to zero for all media files."""
    try:
        affected = MediaFile.query.update({MediaFile.like_count: 0})
        db.session.commit()
        return jsonify({'success': True, 'affected': affected, 'message': f'Reset like counts for {affected} media files.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Failed to reset likes: {str(e)}'}), 500

@app.route('/api/reset-elo', methods=['POST'])
def reset_elo():
    """Reset ELO ratings to 1500 for all media files."""
    try:
        affected = MediaFile.query.update({MediaFile.elo_rating: 1500})
        db.session.commit()
        return jsonify({'success': True, 'affected': affected, 'message': f'Reset ELO ratings for {affected} media files.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Failed to reset ELO: {str(e)}'}), 500

# Run the app
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)
