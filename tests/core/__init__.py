# Makes tests/core a proper Python package so test modules with the same
# basename (e.g. test_astrology.py in both tests/core/ and tests/core/context/)
# import under distinct dotted names (tests.core.test_astrology vs
# tests.core.context.test_astrology). Mirrors tests/__init__.py pattern.
