FROM openpolicyagent/opa:1.20.2

COPY policies/rego/runtime.rego /policies/runtime.rego

CMD ["run", "--server", "--addr=0.0.0.0:8181", "--log-format=json", "/policies"]
