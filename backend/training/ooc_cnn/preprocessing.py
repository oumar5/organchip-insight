"""Image preprocessing shared by OoC CNN training and inference."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PIL import Image

IMAGE_SIZE = 224
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)
IMAGENET_MEAN_RGB = tuple(round(channel * 255) for channel in IMAGENET_MEAN)
PADDING_RGB = (0, 0, 0)


def force_rgb(image: Image.Image) -> Image.Image:
    """Return a three-channel image without retaining a handle to the source file."""
    if not isinstance(image, Image.Image):
        raise TypeError("image must be a PIL image")
    return image.convert("RGB")


def resize_and_pad(
    image: Image.Image,
    *,
    size: int = IMAGE_SIZE,
    padding_color: tuple[int, int, int] = PADDING_RGB,
) -> Image.Image:
    """Resize the complete field of view and center-pad it to a square canvas."""
    if size <= 0:
        raise ValueError("size must be positive")
    if len(padding_color) != 3 or any(not 0 <= channel <= 255 for channel in padding_color):
        raise ValueError("padding_color must contain three values between 0 and 255")

    rgb = force_rgb(image)
    width, height = rgb.size
    if width <= 0 or height <= 0:
        raise ValueError("image dimensions must be positive")

    scale = min(size / width, size / height)
    resized_width = min(size, max(1, round(width * scale)))
    resized_height = min(size, max(1, round(height * scale)))
    resized = rgb.resize(
        (resized_width, resized_height),
        resample=Image.Resampling.BILINEAR,
    )
    canvas = Image.new("RGB", (size, size), color=padding_color)
    offset = ((size - resized_width) // 2, (size - resized_height) // 2)
    canvas.paste(resized, offset)
    return canvas


@dataclass(frozen=True, slots=True)
class ResizeAndPad:
    """Pickle-friendly callable for use in torchvision compositions."""

    size: int = IMAGE_SIZE
    padding_color: tuple[int, int, int] = PADDING_RGB

    def __call__(self, image: Image.Image) -> Image.Image:
        return resize_and_pad(
            image,
            size=self.size,
            padding_color=self.padding_color,
        )


def build_image_transform(*, training: bool, image_size: int = IMAGE_SIZE) -> Any:
    """Build torchvision transforms, importing the optional dependency lazily."""
    try:
        from torchvision import transforms
    except (ImportError, RuntimeError) as error:
        raise RuntimeError(
            "torchvision is required to build CNN image transforms"
        ) from error

    operations: list[Any] = [transforms.Lambda(force_rgb)]
    if training:
        operations.extend(
            (
                transforms.RandomHorizontalFlip(),
                transforms.RandomVerticalFlip(),
            )
        )
    operations.extend(
        (
            ResizeAndPad(size=image_size),
            transforms.ToTensor(),
            transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        )
    )
    return transforms.Compose(operations)
