# Deploy to a Hugging Face Space

The Space is a static Space. It holds the site: one page and one data file with every area.

## Build and upload by hand

1. Build the site for every area:

    ```bash
    uv run landuse-map site site-out
    ```

2. Create a static Space on Hugging Face.
3. Upload the files in `site-out/` to the Space. The file `site-out/README.md` sets the Space title and type.

## Deploy from GitHub Actions

The workflow `ci` has a job named `deploy`. It runs only when you start it by hand, from the Actions tab. The job builds every area and uploads the site.

The upload needs a repository secret named `HF_TOKEN`. Without the secret, the job builds the site and skips the upload.

The upload also removes the old per-area data files from the Space.
