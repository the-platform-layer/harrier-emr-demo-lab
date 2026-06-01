# Claude Project Notes

Start with `AGENTS.md`. It is the canonical repository guide for scope, safety, commands, and scenario expectations.

This repo creates real AWS resources. Favor clear cleanup, explicit cost warnings, and reproducible scenario evidence over clever shortcuts.

Use these commands before handing work back:

```bash
make test
make smoke
```

If Terraform changed, also run Terraform format and validation.
