"""Top-level package for ``knowledge_storm``.

Only the version information is exported automatically to avoid
eagerly importing heavy dependencies when the package is imported.
Submodules should be imported explicitly by consumers as needed.
"""

__all__ = ["__version__", "rm"]

# importing these modules here previously pulled in numerous optional
# dependencies during test discovery. To keep startup lightweight we no
# longer import them automatically. Import the desired submodules
# directly instead.

__version__ = "1.2.0"
