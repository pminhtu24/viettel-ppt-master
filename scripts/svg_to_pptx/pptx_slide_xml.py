"""Animation capability exposed to the native PPTX builder."""

try:
    from pptx_animations import TRANSITIONS

    ANIMATIONS_AVAILABLE = True
except ImportError:
    ANIMATIONS_AVAILABLE = False
    TRANSITIONS = {}
