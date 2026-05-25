# 01_contracts

Shared schemas and interfaces. All components communicate using these contracts.

## JSON Schemas

| File | Used by |
|------|---------|
| [request.schema.json](request.schema.json) | adapters → router/dispatcher |
| [response.schema.json](response.schema.json) | dispatcher → adapters |
| [stream_event.schema.json](stream_event.schema.json) | harness.stream() output |
| [tool_invocation.schema.json](tool_invocation.schema.json) | calling tools / MCP functions |
| [classification_audit_finding.schema.json](classification_audit_finding.schema.json) | responsibility-boundary audit JSONL records |

## Python Protocols

`interfaces/` holds runtime-checkable `typing.Protocol` mirrors so that adapters,
harnesses, and drivers can advertise the contract they implement without pulling
their full bucket as a dependency.

| Protocol | Concrete impls |
|----------|---------------|
| `AdapterProtocol` | 03_adapters/* |
| `HarnessProtocol` | 04_harnesses/* (abstract base at `harnesses.base.Harness`) |
| `DriverProtocol` | 08_drivers/* |
