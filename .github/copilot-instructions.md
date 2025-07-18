# Copilot Instructions for Bobbies Creator

## Project Overview
Django web application that converts uploaded images into coloring book-style sketches using OpenCV. The main workflow is: upload image → apply edge detection & Gaussian blur → save both original and sketch versions to media directory.

This project is designed to be extensible, allowing for future enhancements such as additional image processing options, user management, and API endpoints.

The template need be like a book, with a clean and responsive design using Tailwind CSS. The application should be easy to navigate, with a focus on user experience.

With pagination between the images, users can easily browse through their uploaded images and sketches.

## Architecture & Key Components

### Core App Structure
- **`core/`** - Single Django app handling all functionality
- **`media/`** - File storage for uploaded images and generated sketches
- **Image Processing Flow**: `views.upload_image()` → OpenCV processing → file system storage → template rendering

### Models (`core/models.py`)
```python
UploadedImage  # Main image uploads with user association
ImageChild     # Child/derived images (sketches) linked to parent
```
**Important**: Models exist but aren't used in current views - views use direct file system operations instead.

### Image Processing Logic (`core/views.py`)
Key OpenCV pipeline in `upload_image()`:
1. Convert to grayscale: `cv2.cvtColor(original_image, cv2.COLOR_BGR2GRAY)`
2. Invert colors: `255 - gray_image`  
3. Apply Gaussian blur with configurable detail_level
4. Create sketch via `cv2.divide()` for edge detection

**Critical Pattern**: `detail_level` must be odd number for Gaussian blur - auto-increment if even.

## Development Workflow

### Setup Commands
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Key Dependencies
- **Django 5.x** - Web framework
- **OpenCV (`cv2`)** - Image processing engine  
- **Pillow** - Django ImageField support

### File Organization Patterns
- Generated sketches prefixed with `sketch_` + original filename
- All media files stored flat in `/media/` directory
- Templates in `core/templates/` (app-level, not project-level)

## Current Implementation Notes

### Data Flow Mismatch
**Important**: The models define proper database relationships, but current view bypasses database entirely - uses direct file operations. Consider this when adding features:
- Views use `FileSystemStorage` directly
- No database records created for uploads
- User association exists in models but not implemented

### Form Handling
Simple `ImageUploadForm` with single `ImageField` - extensible for additional parameters like quality settings, filters, etc.

### URL Structure
- Root path (`/`) → upload interface
- Media served via `static()` configuration in main `urls.py`
- Admin available at `/admin/`

## Extension Points
- **Database Integration**: Connect existing models to views for user tracking
- **Batch Processing**: Current implementation processes one image at a time
- **Algorithm Options**: `detail_level` parameter shows how to add processing variants
- **API Endpoints**: Add REST API alongside existing form-based interface

## Common Tasks
- **Add new image filters**: Extend OpenCV pipeline in `views.upload_image()`
- **Database features**: Use existing `UploadedImage`/`ImageChild` models
- **UI improvements**: Modify `core/templates/upload.html` (inline CSS currently)
- **File management**: All media operations go through Django's `FileSystemStorage`

## Template Structure
- **`core/templates/base.html`** - Base template for consistent layout
- **`core/templates/upload.html`** - Main upload interface
- **`core/templates/show_image.html`** - Displays uploaded images and their sketches

Use Tailwind CSS classes for styling, ensuring responsive design. The templates should be clean and maintainable, with minimal inline styles.
