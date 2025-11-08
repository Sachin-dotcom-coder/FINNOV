# Place your extractor and logic modules in this package.
#
# Expected interfaces:
# - extractor.py must define:
#     def extract(input: dict) -> dict: ...
#
# - logic.py must define:
#     def analyze(extracted: dict, options: dict | None = None) -> dict: ...
