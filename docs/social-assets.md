# Social Preview Assets

Harrier EMR Demo Lab keeps deterministic social assets in the repository so GitHub previews stay consistent with the rest of the Harrier project.

## Assets

| Asset | Path | Use |
| --- | --- | --- |
| Demo lab GitHub social preview | `docs/assets/social-preview.png` | Upload in GitHub repository settings |
| Editable social preview | `docs/assets/social-preview.svg` | Source for social preview updates |

## GitHub Upload Steps

1. Open the GitHub repository.
2. Go to **Settings**.
3. Open **General**.
4. Scroll to **Social preview**.
5. Upload:

   ```text
   docs/assets/social-preview.png
   ```

6. Save changes.

GitHub social previews should be `1280x640` PNG images under 1 MB when possible.

## Regenerate PNG

Render the PNG from the editable SVG:

```bash
magick docs/assets/social-preview.svg docs/assets/social-preview.png
```
