# Deploy to a Hugging Face Space

The Space is a static Space. It shows one page: the map. Static Spaces are free.

## Build and upload

1. Build the site:

    ```bash
    uv run landuse-map site site-out
    ```

2. Create a static Space on Hugging Face.
3. Upload the files in `site-out/` to the Space.

The file `site-out/README.md` sets the Space title and type.
