"""
Utility functions for honestplus library
"""

import os
import tempfile
import logging
from typing import Optional, Union, Tuple

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    raise ImportError(
        "Pillow is required for image processing. "
        "Install it with: pip install Pillow"
    )

logger = logging.getLogger(__name__)

# Default Honest+ dimensions for stories
STORY_WIDTH = 1037
STORY_HEIGHT = 1843
STORY_ASPECT_RATIO = STORY_WIDTH / STORY_HEIGHT

# Path to default font
_FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
DEFAULT_FONT_PATH = os.path.join(_FONT_DIR, "Fredoka-VariableFont_wdth,wght.ttf")


def get_default_font(size: int = 60) -> ImageFont.FreeTypeFont:
    """
    Get the default Fredoka font
    
    Args:
        size: Font size in points (default: 60)
        
    Returns:
        ImageFont.FreeTypeFont object
        
    Raises:
        FileNotFoundError: If font file is not found
    """
    if not os.path.exists(DEFAULT_FONT_PATH):
        raise FileNotFoundError(
            f"Default font not found at {DEFAULT_FONT_PATH}. "
            "Make sure the fonts directory is present in the package."
        )
    
    return ImageFont.truetype(DEFAULT_FONT_PATH, size)


def prepare_image_for_story(
    image_path: str,
    output_path: Optional[str] = None,
    background_color: Union[str, Tuple[int, int, int]] = "black"
) -> str:
    """
    Prepare image for Honest+ story (1037x1843) with letterboxing

    The image is resized maintaining the original aspect ratio and centered
    on a 1037x1843 canvas. Empty areas are filled with the background color.

    Args:
        image_path: Path to the original image
        output_path: Path to save (optional, creates temp file if None)
        background_color: Background color for letterboxing
                         Can be a color name ("black", "white", "red", etc.)
                         or RGB tuple (255, 0, 0)

    Returns:
        Path to the prepared image

    Raises:
        FileNotFoundError: If image_path does not exist
        ValueError: If the image cannot be opened
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    try:
        img = Image.open(image_path)
    except Exception as e:
        raise ValueError(f"Failed to open image: {e}")
    
    # Convert to RGB if needed (e.g., PNG with transparency)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    original_width, original_height = img.size
    original_ratio = original_width / original_height
    
    logger.debug(
        f"Preparing image for story: {original_width}x{original_height} "
        f"(ratio: {original_ratio:.2f}) -> {STORY_WIDTH}x{STORY_HEIGHT}"
    )
    
    # Calculate dimensions for FIT (not crop) - entire image fits
    if original_ratio > STORY_ASPECT_RATIO:
        # Wider image - fit by width
        new_width = STORY_WIDTH
        new_height = int(STORY_WIDTH / original_ratio)
    else:
        # Taller image - fit by height
        new_height = STORY_HEIGHT
        new_width = int(STORY_HEIGHT * original_ratio)
    
    # Resize maintaining aspect ratio
    img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Create canvas with colored background
    canvas = Image.new('RGB', (STORY_WIDTH, STORY_HEIGHT), background_color)
    
    # Center image on canvas
    x_offset = (STORY_WIDTH - new_width) // 2
    y_offset = (STORY_HEIGHT - new_height) // 2
    
    canvas.paste(img_resized, (x_offset, y_offset))
    
    # Save
    if output_path is None:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        output_path = temp_file.name
        temp_file.close()
        logger.debug(f"Created temporary file: {output_path}")

    # Save without EXIF metadata to avoid rotation issues
    canvas.save(output_path, 'JPEG', quality=100, optimize=True, exif=b'')
    
    logger.info(f"Image prepared for story: {output_path}")
    
    return output_path


def create_text_story(
    text: str,
    output_path: Optional[str] = None,
    background_color: Union[str, Tuple[int, int, int]] = "black",
    text_color: Union[str, Tuple[int, int, int]] = "white",
    font_size: int = 60,
    font_path: Optional[str] = None,
    max_width: int = 900,
) -> str:
    """
    Create a text-only story image with the default Fredoka font
    
    Creates a 1037x1843 image with centered text using the Fredoka font.
    Text is automatically wrapped to fit within max_width.
    
    Args:
        text: Text content to display
        output_path: Path to save (optional, creates temp file if None)
        background_color: Background color (name or RGB tuple)
        text_color: Text color (name or RGB tuple)
        font_size: Font size in points (default: 60)
        font_path: Custom font path (uses Fredoka if None)
        max_width: Maximum width for text wrapping in pixels (default: 900)
    
    Returns:
        Path to the created image
        
    Raises:
        FileNotFoundError: If font file is not found
    """
    # Create canvas
    canvas = Image.new('RGB', (STORY_WIDTH, STORY_HEIGHT), background_color)
    draw = ImageDraw.Draw(canvas)
    
    # Load font
    if font_path is None:
        font = get_default_font(font_size)
    else:
        if not os.path.exists(font_path):
            raise FileNotFoundError(f"Font file not found: {font_path}")
        font = ImageFont.truetype(font_path, font_size)
    
    # Wrap text to fit max_width
    lines = _wrap_text(text, font, max_width, draw)
    
    # Calculate total text height
    line_heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_heights.append(bbox[3] - bbox[1])
    
    line_spacing = font_size * 0.3  # 30% of font size for line spacing
    total_height = sum(line_heights) + line_spacing * (len(lines) - 1)
    
    # Start position (centered vertically)
    y = (STORY_HEIGHT - total_height) / 2
    
    # Draw each line centered horizontally
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        x = (STORY_WIDTH - text_width) / 2
        
        draw.text((x, y), line, font=font, fill=text_color)
        y += line_heights[i] + line_spacing
    
    # Save
    if output_path is None:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        output_path = temp_file.name
        temp_file.close()
        logger.debug(f"Created temporary file: {output_path}")
    
    canvas.save(output_path, 'JPEG', quality=100, optimize=True, exif=b'')
    logger.info(f"Text story created: {output_path}")
    
    return output_path


def add_text_to_image(
    image_path: str,
    text: str,
    output_path: Optional[str] = None,
    position: Tuple[int, int] = None,
    text_color: Union[str, Tuple[int, int, int]] = "white",
    font_size: int = 60,
    font_path: Optional[str] = None,
    align: str = "center",
    max_width: int = 900,
) -> str:
    """
    Add text overlay to an image using the default Fredoka font
    
    Args:
        image_path: Path to the base image
        text: Text to add
        output_path: Path to save (optional, creates temp file if None)
        position: Text position (x, y). If None, centers text vertically
        text_color: Text color (name or RGB tuple)
        font_size: Font size in points (default: 60)
        font_path: Custom font path (uses Fredoka if None)
        align: Text alignment: "left", "center", or "right" (default: "center")
        max_width: Maximum width for text wrapping in pixels (default: 900)
    
    Returns:
        Path to the image with text overlay
        
    Raises:
        FileNotFoundError: If image_path or font file not found
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    # Open image
    img = Image.open(image_path)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    draw = ImageDraw.Draw(img)
    
    # Load font
    if font_path is None:
        font = get_default_font(font_size)
    else:
        if not os.path.exists(font_path):
            raise FileNotFoundError(f"Font file not found: {font_path}")
        font = ImageFont.truetype(font_path, font_size)
    
    # Wrap text
    lines = _wrap_text(text, font, max_width, draw)
    
    # Calculate dimensions
    line_heights = []
    line_widths = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_widths.append(bbox[2] - bbox[0])
        line_heights.append(bbox[3] - bbox[1])
    
    line_spacing = font_size * 0.3
    total_height = sum(line_heights) + line_spacing * (len(lines) - 1)
    
    # Determine starting position
    if position is None:
        # Center vertically
        y = (img.height - total_height) / 2
    else:
        y = position[1]
    
    # Draw each line
    for i, line in enumerate(lines):
        if position is None or align == "center":
            x = (img.width - line_widths[i]) / 2
        elif align == "right":
            x = img.width - line_widths[i] - 50  # 50px margin
        else:  # left
            x = 50 if position is None else position[0]
        
        draw.text((x, y), line, font=font, fill=text_color)
        y += line_heights[i] + line_spacing
    
    # Save
    if output_path is None:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        output_path = temp_file.name
        temp_file.close()
        logger.debug(f"Created temporary file: {output_path}")
    
    img.save(output_path, 'JPEG', quality=100, optimize=True, exif=b'')
    logger.info(f"Text added to image: {output_path}")
    
    return output_path


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw) -> list:
    """
    Wrap text to fit within max_width
    
    Args:
        text: Text to wrap
        font: Font to use for measuring
        max_width: Maximum width in pixels
        draw: ImageDraw object for text measurement
        
    Returns:
        List of text lines
    """
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        width = bbox[2] - bbox[0]
        
        if width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                # Single word is too long, add it anyway
                lines.append(word)
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines if lines else [text]
