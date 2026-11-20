# Public package. The CLI (cli.py) is the entry point; engine.scan / engine.trace do the work.
# Importing submodules lazily keeps `import roottrace` cheap for the HTTP server and tests.
