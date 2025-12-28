# Views package initialization

# Import main views
from .main import *

# Import specialized views
try:
    from .allegati import *
except ImportError:
    pass  # allegati views might not be ready yet