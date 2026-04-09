# Neutrino TLS

neutrino-api uses HTTPS + bearer-token auth by default.

For JoinMarket NG users, the short version is:

1. Set `neutrino_url` to `https://...`
2. Point JoinMarket NG to neutrino's `tls.cert`
3. Point JoinMarket NG to neutrino's `auth_token` file (or paste the token)

## Minimal Setup

```toml
[bitcoin]
backend_type = "neutrino"
neutrino_url = "https://127.0.0.1:8334"
neutrino_tls_cert = "~/.joinmarket-ng/neutrino/tls.cert"
neutrino_auth_token_file = "~/.joinmarket-ng/neutrino/auth_token"
```

Recommended local location for credentials:

- `~/.joinmarket-ng/neutrino/tls.cert`
- `~/.joinmarket-ng/neutrino/auth_token`

## Where The Files Come From

neutrino-api creates these on first start in its own data directory:

- `tls.cert`
- `auth_token`

Copy both files into `~/.joinmarket-ng/neutrino/` (or mount/symlink them)
and use the paths in `config.toml`.

## Migration from HTTP

If you previously used plain HTTP:

1. Change `neutrino_url` from `http://...` to `https://...`
2. Add `neutrino_tls_cert`
3. Add `neutrino_auth_token_file` (or `neutrino_auth_token`)
4. Restart JoinMarket NG services

## Resetting Credentials

If you run neutrino-api with `--reset-auth`, it regenerates both files.
After that, copy the new `tls.cert` and `auth_token` again and restart
JoinMarket NG.
