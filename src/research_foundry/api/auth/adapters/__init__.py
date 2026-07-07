# Auth adapter package — concrete AuthProvider implementations.
#
# Each sub-module self-registers its provider at import time by calling
# ``register_provider(instance)`` at module level.  Import a sub-module to
# make its provider available in the registry; do not import providers you
# don't need (avoids optional-dependency import errors).
