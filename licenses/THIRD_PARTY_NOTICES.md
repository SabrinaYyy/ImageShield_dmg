# Third-Party Notices

ImageShield includes third-party Python packages and model files. Before public
distribution, legal review must confirm that each dependency and checkpoint may
be redistributed in the intended countries and use cases.

The build process downloads the VAE and scheduler from:

- Model: `timbrooks/instruct-pix2pix`
- Revision: `31519b5cb02a7fd89b906d88731cd4d6a7bbf88d`
- Source: <https://huggingface.co/timbrooks/instruct-pix2pix>

The downloaded files are intentionally excluded from Git. The macOS and Windows
packaging processes embed them into the final offline application.

The upstream repository states that pretrained checkpoints are based on Stable
Diffusion components and may be subject to additional checkpoint terms. Include
the authoritative upstream license and model-use terms here after legal review.

Python package licenses should be collected from the locked build environment
and shipped with every release.
