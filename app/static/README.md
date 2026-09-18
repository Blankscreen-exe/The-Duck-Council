# Static assets

Everything the page needs is served from here, so the app works fully offline
(with Ollama, for instance) and loads nothing from a third party at page view.

## Third-party files

| File | Source | Version | License |
|---|---|---|---|
| `vendor/htmx-2.0.10.min.js` | npm `htmx.org` | 2.0.10 | 0BSD (`licenses/htmx-LICENSE.txt`) |
| `vendor/htmx-ext-sse-2.2.4.js` | npm `htmx-ext-sse` | 2.2.4 | 0BSD (`licenses/htmx-ext-sse-LICENSE.txt`) |
| `fonts/dm-serif-display-400*.woff2` | npm `@fontsource/dm-serif-display`, latin subset | 5.3.0 | SIL OFL 1.1 (`licenses/dm-serif-display-OFL.txt`) |
| `fonts/karla-{400,500,700}.woff2` | npm `@fontsource/karla`, latin subset | 5.3.0 | SIL OFL 1.1 (`licenses/karla-OFL.txt`) |
| `fonts/caveat-{400,700}.woff2` | npm `@fontsource/caveat`, latin subset | 5.3.0 | SIL OFL 1.1 (`licenses/caveat-OFL.txt`) |
| `sounds/stamp.mp3` | Pixabay Sound Effects ("door slam", freesound_community) | - | Pixabay Content License: free use, no attribution required |

SHA-256, to verify nothing has been swapped since download:

```
71ea67185bfa8c98c39d31717c6fce5d852370fcdfd129db4543774d3145c0de  vendor/htmx-2.0.10.min.js
3b5992a541619babefc4c169505af474df5c3039da51e59b96ccf9241ecd61d2  vendor/htmx-ext-sse-2.2.4.js
fdf61e20fd2c0108e0ea28da4daca0035205b4b7fc031a3974b865b704de160a  fonts/dm-serif-display-400.woff2
ed8b291611e32fa2d2900488dd48fc95faf0957b2ef7ddf1527e8d21dd9cf2df  fonts/dm-serif-display-400-italic.woff2
250bb48fdea5ba354fa85161f3877121ef679c6f7a1ef3d8f173fb8979628906  fonts/karla-400.woff2
42c6c969fa8e0248f869f3e2795f95f80f2bb7f5382cf4bb9772f9b2e438c777  fonts/karla-500.woff2
b3613b987992f48294da8bce46723ef9683a16422318cd41712421084dd4c2c4  fonts/karla-700.woff2
d0b7b931b8980049327e8f8f9ac264617c8200b8422d62e886473d3d9527bad3  fonts/caveat-400.woff2
15f9638095ad5ec9816f93d66805ca1a87e71dc5a76b596bfce1c78d4704c405  fonts/caveat-700.woff2
6fb67577a4ea8723ef925347dcb7aa50e5c0149962749ba2c7bde3dd742410fa  sounds/stamp.mp3
```

## Our own

- `css/council.css`, `js/council.js`: the Green Bench theme (D24) and the
  stamp animation and sound (D26).
- `images/`: the thirteen duck portraits, carried over from v1.
