# Extension type: provider / adapter / connector

Pluggable implementations behind a common interface (payment providers, storage backends, AI model providers,
auth mechanisms, importers/exporters). Typical required registration points: a registry/factory entry, config
schema fields, environment variables, docs, an affected capability contract, and a changelog entry. Always
define the removal steps so disabling a provider doesn't leave orphan config/registry entries.
